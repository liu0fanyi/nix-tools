#!/usr/bin/env python3
"""Render the Podman deployment from one instance.toml file."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import textwrap
import tomllib
from pathlib import Path
from typing import Any


HOST_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$")
PROFILES = {"home-ipv6-cdn", "vps-direct"}


class ConfigError(Exception):
    pass


def table(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"missing [{name}] table")
    return value


def required_string(values: dict[str, Any], key: str, section: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"[{section}].{key} must be a non-empty string")
    return value


def required_int(values: dict[str, Any], key: str, section: str) -> int:
    value = values.get(key)
    if not isinstance(value, int) or not 1 <= value <= 65535:
        raise ConfigError(f"[{section}].{key} must be a port from 1 to 65535")
    return value


def validate(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise ConfigError("schema_version must be 1")

    deployment = table(config, "deployment")
    profile = required_string(deployment, "profile", "deployment")
    if profile not in PROFILES:
        raise ConfigError(f"unsupported profile: {profile}")

    domains = table(config, "domains")
    for key in ("public", "origin", "readonly_public", "readonly_origin"):
        value = required_string(domains, key, "domains")
        if not HOST_RE.fullmatch(value):
            raise ConfigError(f"[domains].{key} is not a valid hostname")

    features = table(config, "features")
    for key in ("readonly", "terminal", "ddns"):
        if not isinstance(features.get(key), bool):
            raise ConfigError(f"[features].{key} must be true or false")
    if profile == "vps-direct" and features["ddns"]:
        raise ConfigError("vps-direct requires [features].ddns = false")
    paths = table(config, "paths")
    for key in (
        "workspace",
        "readonly",
        "dist",
        "authelia_data",
        "ddns_config",
        "caddy_data",
        "caddy_config",
        "terminal_workspace",
        "terminal_socket_dir",
        "secrets",
    ):
        path = Path(required_string(paths, key, "paths"))
        if not path.is_absolute():
            raise ConfigError(f"[paths].{key} must be absolute")
    media = paths.get("media", "")
    if not isinstance(media, str) or (media and not Path(media).is_absolute()):
        raise ConfigError("[paths].media must be empty or absolute")

    ports = table(config, "ports")
    for key in ("lan", "readonly_origin", "main_origin", "http", "https"):
        required_int(ports, key, "ports")

    security = table(config, "security")
    subnet = required_string(security, "container_subnet", "security")
    try:
        ipaddress.ip_network(subnet)
    except ValueError as error:
        raise ConfigError(f"invalid container_subnet: {error}") from error
    for key in ("lan_cidrs", "edgeone_trusted_proxies"):
        values = security.get(key)
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            raise ConfigError(f"[security].{key} must be an array of CIDRs")
        for value in values:
            try:
                ipaddress.ip_network(value)
            except ValueError as error:
                raise ConfigError(f"invalid CIDR in {key}: {value}") from error


def read_lan_auth(secret_dir: Path) -> tuple[str, str]:
    path = secret_dir / "caddy_lan_basic_auth"
    raw = path.read_text(encoding="utf-8").strip()
    parts = raw.split(maxsplit=1)
    if len(parts) != 2 or not re.fullmatch(r"[A-Za-z0-9_.-]+", parts[0]):
        raise ConfigError(f"invalid Caddy basic auth secret: {path}")
    if not parts[1].startswith(("$2a$", "$2b$", "$2y$")):
        raise ConfigError(f"Caddy password in {path} must be a bcrypt hash")
    return parts[0], parts[1]


def app_routes(terminal: bool) -> str:
    terminal_routes = ""
    if terminal:
        terminal_routes = """
@terminal_ws {
    path /terminal/ws /terminal/ws/*
}
handle @terminal_ws {
    uri strip_prefix /terminal
    reverse_proxy unix//run/host-ttyd/ttyd.sock {
        header_up Connection "Upgrade"
        header_up Upgrade "websocket"
    }
}
@terminal {
    path /terminal /terminal/ /terminal/*
}
handle @terminal {
    uri strip_prefix /terminal
    reverse_proxy unix//run/host-ttyd/ttyd.sock
}
"""
    return f"""
root * /srv/dist

@dufs_api {{
    expression {{query}}.contains('json')
}}
handle @dufs_api {{
    reverse_proxy dufs-lan:5000
}}

handle_path /tag-api/* {{
    reverse_proxy tag-server:8081
}}

{terminal_routes}
@ui_root {{
    method GET HEAD
    path /
    not expression {{query}}.contains('json')
}}
handle @ui_root {{
    rewrite * /index.html
    file_server
}}

@static {{
    method GET HEAD
    file
}}
handle @static {{
    file_server
}}

handle {{
    reverse_proxy dufs-lan:5000
}}
""".strip()


def auth_routes(public_host: str) -> str:
    return f"""
handle /authelia/* {{
    reverse_proxy authelia:9091 {{
        header_up X-Real-IP {{client_ip}}
        header_up X-Forwarded-Proto {{scheme}}
        header_up X-Forwarded-Host {{host}}
        header_up X-Forwarded-For {{client_ip}}
    }}
}}

@not_options {{
    not method OPTIONS
    not path /authelia/*
}}
forward_auth @not_options authelia:9091 {{
    uri /authelia/api/authz/forward-auth?authelia_url=https://{public_host}/authelia/
    header_up X-Forwarded-Method {{method}}
    header_up X-Forwarded-Proto {{scheme}}
    header_up X-Forwarded-Host {{host}}
    header_up X-Forwarded-Uri {{uri}}
    header_up X-Forwarded-For {{client_ip}}
    copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
}}

handle_errors {{
    @unauthorized expression {{err.status_code}} == 401
    handle @unauthorized {{
        redir https://{public_host}/authelia/?rd=https://{public_host}{{uri}}
    }}
}}
""".strip()


def render_caddy(config: dict[str, Any], lan_auth: tuple[str, str]) -> str:
    deployment = table(config, "deployment")
    profile = deployment["profile"]
    domains = table(config, "domains")
    features = table(config, "features")
    ports = table(config, "ports")
    security = table(config, "security")

    proxies = " ".join(security["edgeone_trusted_proxies"])
    global_options = """
{
    servers {
        trusted_proxies static private_ranges%s
    }
    skip_install_trust
%s
}
""" % (
        f" {proxies}" if profile == "home-ipv6-cdn" and proxies else "",
        "    auto_https disable_redirects" if profile == "home-ipv6-cdn" else "",
    )

    routes = app_routes(features["terminal"])
    auth = auth_routes(domains["public"])

    if profile == "vps-direct":
        sites = [
            f"""
{domains["public"]} {{
{textwrap.indent(auth, "    ")}

{textwrap.indent(routes, "    ")}
}}
"""
        ]
        if features["readonly"]:
            sites.append(
                f"""
{domains["readonly_public"]} {{
    reverse_proxy dufs-readonly:5000
}}
"""
            )
        return global_options + "\n".join(sites)

    username, password_hash = lan_auth
    lan_cidrs = " ".join(security["lan_cidrs"])
    readonly_site = ""
    if features["readonly"]:
        readonly_site = f"""
https://{domains["readonly_origin"]}:{ports["readonly_origin"]}, https://{domains["readonly_public"]}:{ports["readonly_origin"]} {{
    tls internal
    @origin_host host {domains["readonly_origin"]}
    redir @origin_host https://{domains["readonly_public"]}{{uri}} permanent
    reverse_proxy dufs-readonly:5000
}}
"""

    return (
        global_options
        + readonly_site
        + f"""
http://:{ports["lan"]} {{
    @lan remote_ip {lan_cidrs}
    handle @lan {{
        @not_options not method OPTIONS
        basic_auth @not_options {{
            {username} {password_hash}
        }}

{textwrap.indent(routes, "        ")}
    }}
    handle {{
        abort
    }}
}}

https://{domains["public"]}:{ports["main_origin"]}, https://{domains["origin"]}:{ports["main_origin"]}, https://localhost:{ports["main_origin"]}, https://127.0.0.1:{ports["main_origin"]} {{
    tls internal
    @origin_host host {domains["origin"]}
    redir @origin_host https://{domains["public"]}{{uri}} permanent

{textwrap.indent(auth, "    ")}

{textwrap.indent(routes, "    ")}
}}
"""
    )


def render_authelia(config: dict[str, Any]) -> str:
    deployment = table(config, "deployment")
    domains = table(config, "domains")
    authelia = table(config, "authelia")
    allowed_domains = [domains["public"]]
    if deployment["profile"] == "home-ipv6-cdn":
        allowed_domains.append(domains["origin"])
    domain_lines = "\n".join(f'        - "{host}"' for host in allowed_domains)

    return f"""---
server:
  address: tcp://0.0.0.0:9091/authelia
  endpoints:
    authz:
      forward-auth:
        implementation: ForwardAuth

log:
  level: info

authentication_backend:
  password_reset:
    disable: false
  file:
    path: /config/users_database.yml
    password:
      algorithm: argon2id
      iterations: 3
      memory: 65536
      parallelism: 4
      salt_length: 16
      key_length: 32

totp:
  issuer: "{authelia["issuer"]}"
  period: 30
  skew: 1

webauthn:
  timeout: 60s
  display_name: "{authelia["display_name"]}"
  attestation_conveyance_preference: indirect
  selection_criteria:
    user_verification: preferred

session:
  name: authelia_session
  expiration: 12h
  inactivity: 3h
  remember_me: 1M
  cookies:
    - domain: "{authelia["session_domain"]}"
      authelia_url: "https://{domains["public"]}/authelia/"
      default_redirection_url: "https://{domains["public"]}/"

storage:
  local:
    path: /data/db.sqlite3

notifier:
  disable_startup_check: false
  filesystem:
    filename: /data/notification.txt

access_control:
  default_policy: "{authelia["default_policy"]}"
  rules:
    - domain:
{domain_lines}
      resources:
        - "^/authelia/api/authz/forward-auth.*$"
      policy: bypass
"""


def yaml_list(items: list[str], indent: int) -> str:
    prefix = " " * indent
    return "\n".join(f"{prefix}- {json.dumps(item)}" for item in items)


def render_instance_compose(
    config: dict[str, Any], generated_dir: Path, secret_dir: Path
) -> str:
    profile = table(config, "deployment")["profile"]
    features = table(config, "features")
    paths = table(config, "paths")

    workspace = paths["workspace"]
    caddy_volumes = [
        f"{generated_dir / 'Caddyfile'}:/etc/caddy/Caddyfile:ro",
        f"{paths['dist']}:/srv/dist:ro",
        f"{paths['caddy_data']}:/data/caddy",
        f"{paths['caddy_config']}:/config/caddy",
    ]
    if features["terminal"]:
        caddy_volumes.append(
            f"{paths['terminal_socket_dir']}:/run/host-ttyd:ro"
        )
    dufs_volumes = [f"{workspace}:/data"]
    tag_volumes = [f"{workspace}:/workspace"]
    if paths.get("media"):
        dufs_volumes.append(f"{paths['media']}:/data/media")
        tag_volumes.append(f"{paths['media']}:/workspace/media")

    tag_secret = secret_dir / "tag-server.env"
    if tag_secret.is_file():
        tag_volumes.append(f"{tag_secret}:/run/secrets/tag-server.env:ro")

    lines = [
        "services:",
        "  caddy:",
        "    volumes:",
        yaml_list(caddy_volumes, 6),
        "  dufs-lan:",
        "    volumes:",
        yaml_list(dufs_volumes, 6),
        "  tag-server:",
        '    entrypoint: ["/bin/sh", "-ec"]',
        "    command:",
        "      - |",
        "        if [ -f /run/secrets/tag-server.env ]; then",
        "          set -a",
        "          . /run/secrets/tag-server.env",
        "          set +a",
        "        fi",
        "        exec /app/tag-server --database /workspace/tag_all.db --workspace /workspace --addr 0.0.0.0:8081",
        "    volumes:",
        yaml_list(tag_volumes, 6),
        "  authelia:",
        "    volumes:",
        yaml_list(
            [
                f"{generated_dir / 'authelia' / 'configuration.yml'}:/config/configuration.yml:ro",
                f"{secret_dir / 'authelia_users_database.yml'}:/config/users_database.yml:ro",
                f"{paths['authelia_data']}:/data",
                f"{secret_dir / 'authelia_jwt_secret'}:/run/secrets/authelia_jwt_secret:ro",
                f"{secret_dir / 'authelia_session_secret'}:/run/secrets/authelia_session_secret:ro",
                f"{secret_dir / 'authelia_storage_key'}:/run/secrets/authelia_storage_key:ro",
            ],
            6,
        ),
    ]

    if features["readonly"]:
        lines.extend(
            [
                "  dufs-readonly:",
                "    volumes:",
                yaml_list(
                    [
                        f"{paths['readonly']}:/data:ro",
                        f"{secret_dir / 'dufs-readonly.yaml'}:/run/secrets/dufs-readonly.yaml:ro",
                    ],
                    6,
                ),
            ]
        )

    if features["ddns"]:
        lines.extend(
            [
                "  ddns-go:",
                "    volumes:",
                yaml_list([f"{paths['ddns_config']}:/root"], 6),
            ]
        )
    return "\n".join(lines) + "\n"


def env_line(key: str, value: Any) -> str:
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ConfigError(f"newline not allowed in environment value {key}")
    return f"{key}={text}"


def compose_files(
    deploy_dir: Path, generated_dir: Path, config: dict[str, Any]
) -> list[Path]:
    profile = table(config, "deployment")["profile"]
    features = table(config, "features")
    files = [
        deploy_dir / "compose.yaml",
        deploy_dir / f"compose.{profile}.yaml",
        generated_dir / "compose.instance.yaml",
    ]
    if features["readonly"]:
        files.insert(2, deploy_dir / "compose.readonly.yaml")
    if features["ddns"]:
        files.insert(2, deploy_dir / "compose.ddns.yaml")
    return files


def render(config_path: Path, output: Path) -> None:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    validate(config)

    deploy_dir = Path(__file__).resolve().parents[1]
    paths = table(config, "paths")
    secret_dir = Path(paths["secrets"])
    profile = table(config, "deployment")["profile"]
    required_secrets = [
        "authelia_jwt_secret",
        "authelia_session_secret",
        "authelia_storage_key",
        "authelia_users_database.yml",
    ]
    if profile == "home-ipv6-cdn":
        required_secrets.append("caddy_lan_basic_auth")
    if table(config, "features")["readonly"]:
        required_secrets.append("dufs-readonly.yaml")
    missing = [str(secret_dir / name) for name in required_secrets if not (secret_dir / name).is_file()]
    if missing:
        raise ConfigError(
            "missing runtime secrets; run scripts/import-current-secrets.py first:\n  "
            + "\n  ".join(missing)
        )

    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    authelia_dir = output / "authelia"
    authelia_dir.mkdir(exist_ok=True)
    authelia_dir.chmod(0o700)

    lan_auth = (
        read_lan_auth(secret_dir)
        if profile == "home-ipv6-cdn"
        else ("unused", "$2a$04$unusedunusedunusedunusedunusedunusedunusedunusedunused")
    )
    caddyfile = output / "Caddyfile"
    caddyfile.write_text(render_caddy(config, lan_auth), encoding="utf-8")
    caddyfile.chmod(0o600)

    authelia_config = authelia_dir / "configuration.yml"
    authelia_config.write_text(render_authelia(config), encoding="utf-8")
    authelia_config.chmod(0o600)

    instance_compose = output / "compose.instance.yaml"
    instance_compose.write_text(
        render_instance_compose(config, output, secret_dir), encoding="utf-8"
    )
    instance_compose.chmod(0o600)

    deployment = table(config, "deployment")
    images = table(config, "images")
    ports = table(config, "ports")
    security = table(config, "security")
    env = [
        env_line("COMPOSE_PROJECT_NAME", deployment["name"]),
        env_line("TZ", deployment["timezone"]),
        env_line("CADDY_IMAGE", images["caddy"]),
        env_line("DUFS_IMAGE", images["dufs"]),
        env_line("TAG_SERVER_IMAGE", images["tag_server"]),
        env_line("AUTHELIA_IMAGE", images["authelia"]),
        env_line("DDNS_GO_IMAGE", images["ddns_go"]),
        env_line("CONTAINER_SUBNET", security["container_subnet"]),
        env_line("LAN_PUBLISH_PORT", ports["lan"]),
        env_line("READONLY_ORIGIN_PUBLISH_PORT", ports["readonly_origin"]),
        env_line("MAIN_ORIGIN_PUBLISH_PORT", ports["main_origin"]),
        env_line("HTTP_PUBLISH_PORT", ports["http"]),
        env_line("HTTPS_PUBLISH_PORT", ports["https"]),
    ]
    env_path = output / "compose.env"
    env_path.write_text("\n".join(env) + "\n", encoding="utf-8")
    env_path.chmod(0o600)

    files = compose_files(deploy_dir, output, config)
    (output / "compose-files.txt").write_text(
        "\n".join(str(path) for path in files) + "\n", encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": config["schema_version"],
                "profile": deployment["profile"],
                "features": table(config, "features"),
                "compose_files": [str(path) for path in files],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    terminal_dependency = ""
    if table(config, "features")["terminal"]:
        terminal_dependency = "Wants=ttyd-compose.service\nAfter=ttyd-compose.service\n"
    host_home = str(Path(paths["workspace"]).parent)
    host_username = Path(host_home).name
    host_path = (
        f"{host_home}/.nix-profile/bin:"
        "/nix/var/nix/profiles/default/bin:"
        f"/etc/profiles/per-user/{host_username}/bin:"
        "/run/current-system/sw/bin:/usr/bin:/bin"
    )

    unit = f"""[Unit]
Description=dufs-plus Podman Compose stack
Wants=network-online.target
After=network-online.target
{terminal_dependency}

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={deploy_dir}
Environment=HOME={host_home}
Environment=PATH={host_path}
ExecStart=/usr/bin/env python3 {deploy_dir / "scripts" / "manage.py"} --config {config_path} --output {output} up --confirm-cutover
ExecStop=/usr/bin/env python3 {deploy_dir / "scripts" / "manage.py"} --config {config_path} --output {output} down
TimeoutStartSec=180
TimeoutStopSec=120

[Install]
WantedBy=default.target
"""
    unit_path = output / "dufs-plus-compose.service"
    unit_path.write_text(unit, encoding="utf-8")
    unit_path.chmod(0o600)

    if table(config, "features")["terminal"]:
        terminal_path = paths["terminal_workspace"]
        home_dir = str(Path(terminal_path).parents[1])
        username = Path(home_dir).name
        profile_bin = f"{home_dir}/.nix-profile/bin"
        terminal_unit = f"""[Unit]
Description=Host development terminal for the dufs-plus Compose stack
Before=dufs-plus-compose.service

[Service]
WorkingDirectory={terminal_path}
RuntimeDirectory=ttyd
RuntimeDirectoryMode=0700
Environment=HOME={home_dir}
Environment=SHELL={profile_bin}/bash
Environment=PATH={profile_bin}:/nix/var/nix/profiles/default/bin:/etc/profiles/per-user/{username}/bin:/run/current-system/sw/bin:/usr/bin:/bin
ExecStart={profile_bin}/ttyd -i %t/ttyd/ttyd.sock -W -w {terminal_path} {profile_bin}/zellij attach -c web-dev options --mouse-mode false
Restart=on-failure
RestartSec=2s

[Install]
WantedBy=default.target
"""
        terminal_unit_path = output / "ttyd-compose.service"
        terminal_unit_path.write_text(terminal_unit, encoding="utf-8")
        terminal_unit_path.chmod(0o600)
    print(f"Rendered {deployment['profile']} configuration into {output}")


def main() -> int:
    deploy_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=deploy_dir / "instance.toml"
    )
    parser.add_argument(
        "--output", type=Path, default=deploy_dir / ".generated"
    )
    args = parser.parse_args()
    try:
        render(args.config.resolve(), args.output.resolve())
    except (ConfigError, OSError, tomllib.TOMLDecodeError) as error:
        print(f"render error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
