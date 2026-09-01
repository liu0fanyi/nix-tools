#!/usr/bin/env python3
"""Render the shared Docker/Podman deployment from one instance TOML file."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
import textwrap
import tomllib
import urllib.parse
from pathlib import Path
from typing import Any


HOST_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$")
PROFILES = {"home-ipv6-cdn", "vps-direct", "aliyun-edgeone-http"}
ENGINES = {"podman", "docker"}


class ConfigError(Exception):
    pass


def is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


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

    runtime = table(config, "runtime")
    engine = required_string(runtime, "engine", "runtime")
    if engine not in ENGINES:
        raise ConfigError(f"unsupported container engine: {engine}")

    domains = table(config, "domains")
    for key in ("public", "origin", "readonly_public", "readonly_origin"):
        value = required_string(domains, key, "domains")
        if not HOST_RE.fullmatch(value):
            raise ConfigError(f"[domains].{key} is not a valid hostname")
    aliases = domains.get("aliases", [])
    if not isinstance(aliases, list) or not all(
        isinstance(alias, str) and HOST_RE.fullmatch(alias) for alias in aliases
    ):
        raise ConfigError("[domains].aliases must be an array of hostnames")

    features = table(config, "features")
    for key in ("authelia", "dufs_write", "readonly", "terminal", "ddns"):
        if not isinstance(features.get(key), bool):
            raise ConfigError(f"[features].{key} must be true or false")
    if profile in {"vps-direct", "aliyun-edgeone-http"} and features["ddns"]:
        raise ConfigError(f"{profile} requires [features].ddns = false")
    if profile == "aliyun-edgeone-http" and any(
        features[key] for key in ("authelia", "readonly", "terminal", "ddns")
    ):
        raise ConfigError(
            "aliyun-edgeone-http is a minimal Caddy/DUFS/Tag Server profile"
        )
    paths = table(config, "paths")
    for key in (
        "host_home",
        "workspace",
        "tag_data",
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
    secret_source = paths.get("secret_source")
    if secret_source is not None and (
        not isinstance(secret_source, str)
        or not secret_source
        or not Path(secret_source).is_absolute()
    ):
        raise ConfigError("[paths].secret_source must be an absolute path")
    if features["readonly"]:
        readonly_tag_data = Path(
            required_string(paths, "readonly_tag_data", "paths")
        )
        if not readonly_tag_data.is_absolute():
            raise ConfigError("[paths].readonly_tag_data must be absolute")
    media = paths.get("media", "")
    if not isinstance(media, str) or (media and not Path(media).is_absolute()):
        raise ConfigError("[paths].media must be empty or absolute")
    required_mounts = paths.get("required_mounts", [])
    if not isinstance(required_mounts, list) or not all(
        isinstance(path, str) and Path(path).is_absolute()
        for path in required_mounts
    ):
        raise ConfigError("[paths].required_mounts must be an array of absolute paths")

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
    cors_origins = security.get("cors_origins", [])
    if not isinstance(cors_origins, list) or not all(
        isinstance(value, str) for value in cors_origins
    ):
        raise ConfigError("[security].cors_origins must be an array of origins")
    for origin in cors_origins:
        parsed = urllib.parse.urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ConfigError(f"invalid CORS origin: {origin}")


def read_lan_auth(secret_dir: Path) -> tuple[str, str]:
    path = secret_dir / "caddy_lan_basic_auth"
    raw = path.read_text(encoding="utf-8").strip()
    parts = raw.split(maxsplit=1)
    if len(parts) != 2 or not re.fullmatch(r"[A-Za-z0-9_.-]+", parts[0]):
        raise ConfigError(f"invalid Caddy basic auth secret: {path}")
    if not parts[1].startswith(("$2a$", "$2b$", "$2y$")):
        raise ConfigError(f"Caddy password in {path} must be a bcrypt hash")
    return parts[0], parts[1]


def app_routes(
    terminal: bool,
    capabilities_json: str,
    dufs_service: str = "dufs",
    tag_service: str = "tag-server",
    tag_write: bool = True,
    game_tools: bool = True,
) -> str:
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
    tag_write_guard = ""
    if not tag_write:
        tag_write_guard = """
@tag_api_mutation {
    path /tag-api/*
    not method GET HEAD OPTIONS
}
handle @tag_api_mutation {
    respond "Read-only tag service" 405
}
"""
    game_tools_guard = ""
    if not game_tools:
        game_tools_guard = """
@game_tools {
    path /dist/bevy-game /dist/bevy-game/*
}
handle @game_tools {
    respond "Not found" 404
}
"""
    return f"""
@dufs_plus_capabilities {{
    path /.dufs-plus/capabilities.json
}}
handle @dufs_plus_capabilities {{
    header Content-Type application/json
    header Cache-Control "no-store"
    respond `{capabilities_json}` 200
}}

root * /srv/dist

@html_entry {{
    method GET HEAD
    path / /index.html /dist/transcriptions /dist/transcriptions/ /dist/transcriptions/index.html /dist/bevy-sketch /dist/bevy-sketch/ /dist/bevy-sketch/index.html /dist/bevy-game/animation-editor /dist/bevy-game/animation-editor/ /dist/bevy-game/animation-editor/index.html /dist/bevy-game/galgame /dist/bevy-game/galgame/ /dist/bevy-game/galgame/index.html /dist/bevy-game/gallery-2d /dist/bevy-game/gallery-2d/ /dist/bevy-game/gallery-2d/index.html /dist/bevy-game/gallery-3d /dist/bevy-game/gallery-3d/ /dist/bevy-game/gallery-3d/index.html
}}
header @html_entry Cache-Control "no-cache, must-revalidate"

{tag_write_guard}
{game_tools_guard}
handle_path /tag-api/* {{
    reverse_proxy {tag_service}:8081 {{
        header_up -X-Dufs-Device-Api
        header_up -X-Dufs-Device-Provisioning
    }}
}}

@dufs_api {{
    expression {{query}}=='json'||{{query}}.startsWith('json&')
}}
handle @dufs_api {{
    reverse_proxy {dufs_service}:5000
}}

{terminal_routes}
@ui_root {{
    method GET HEAD
    path /
    not expression {{query}}=='json'||{{query}}.startsWith('json&')
}}
handle @ui_root {{
    rewrite * /index.html
    file_server
}}

handle_path /dist/* {{
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
    reverse_proxy {dufs_service}:5000
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
    not path /authelia/* /device-api /device-api/*
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

    capabilities_json = json.dumps(
        {
            "dufs_write": features["dufs_write"],
            "tag_write": features["dufs_write"],
            "bevy_sketch": features["dufs_write"],
            "game_tools": features["dufs_write"],
            "terminal": features["terminal"],
        },
        separators=(",", ":"),
    )
    routes = app_routes(
        features["terminal"],
        capabilities_json,
        tag_write=features["dufs_write"],
        game_tools=features["dufs_write"],
    )
    readonly_capabilities_json = json.dumps(
        {
            "dufs_write": False,
            "tag_write": False,
            "bevy_sketch": False,
            "game_tools": False,
            "terminal": False,
        },
        separators=(",", ":"),
    )
    readonly_routes = app_routes(
        False,
        readonly_capabilities_json,
        dufs_service="dufs-readonly",
        tag_service="tag-server-readonly",
        tag_write=False,
        game_tools=False,
    )
    auth = auth_routes(domains["public"]) if features["authelia"] else ""

    if profile == "vps-direct":
        auth_block = f"{textwrap.indent(auth, '    ')}\n\n" if auth else ""
        sites = [
            f"""
{domains["public"]} {{
    @public_device_api path /device-api /device-api/*
    respond @public_device_api "Not found" 404

{auth_block}
{textwrap.indent(routes, "    ")}
}}
"""
        ]
        if features["readonly"]:
            sites.append(
                f"""
{domains["readonly_public"]} {{
    @not_options not method OPTIONS
    basic_auth @not_options {{
        {lan_auth[0]} {lan_auth[1]}
    }}

{textwrap.indent(readonly_routes, "    ")}
}}
"""
            )
        return global_options + "\n".join(sites)

    if profile == "aliyun-edgeone-http":
        hosts = [domains["public"], *domains.get("aliases", [])]
        addresses = ", ".join(f"http://{host}" for host in hosts)
        return (
            global_options
            + f"""
{addresses} {{
    # EdgeOne terminates client TLS and currently connects to this origin over HTTP.
    # Only redirect when the CDN explicitly reports an HTTP client request; this
    # avoids a redirect loop for HTTPS clients using an HTTP origin connection.
    @edgeone_client_http header X-Forwarded-Proto http
    redir @edgeone_client_http https://{{host}}{{uri}}

    @public_device_api path /device-api /device-api/*
    respond @public_device_api "Not found" 404

{textwrap.indent(routes, "    ")}
}}
"""
        )

    username, password_hash = lan_auth
    lan_cidrs = " ".join(security["lan_cidrs"])
    readonly_site = ""
    if features["readonly"]:
        readonly_auth_routes = f"""@not_options not method OPTIONS
basic_auth @not_options {{
    {username} {password_hash}
}}

{readonly_routes}"""
        readonly_site = f"""
http://:{ports["readonly_origin"]} {{
{textwrap.indent(readonly_auth_routes, "    ")}
}}

https://{domains["readonly_origin"]}:5443, https://{domains["readonly_public"]}:5443 {{
    tls internal
{textwrap.indent(readonly_auth_routes, "    ")}
}}
"""

    auth_block = f"{textwrap.indent(auth, '    ')}\n\n" if auth else ""
    return (
        global_options
        + readonly_site
        + f"""
http://:{ports["lan"]} {{
    @device_transcription_upload {{
        remote_ip {lan_cidrs}
        method POST
        path /device-api/v1/transcriptions
    }}
    @device_transcription_read {{
        remote_ip {lan_cidrs}
        method GET HEAD
        path /device-api/v1/transcriptions/*
    }}
    handle @device_transcription_upload {{
        uri replace /device-api/v1/transcriptions /v1/device/transcriptions
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Api 1
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    handle @device_transcription_read {{
        uri replace /device-api/v1/transcriptions /v1/device/transcriptions
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Api 1
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    @device_enrollment {{
        remote_ip {lan_cidrs}
        method POST
        path /device-api/v1/enrollments /device-api/v1/enrollments/*/claim
    }}
    handle @device_enrollment {{
        uri replace /device-api/v1/enrollments /v1/device/enrollments
        reverse_proxy tag-server:8081 {{
            header_up -X-Dufs-Device-Api
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    @device_api {{
        remote_ip {lan_cidrs}
        method GET HEAD OPTIONS
        path /device-api/v1/session /device-api/v1/files /device-api/v1/tags /device-api/v1/items /device-api/v1/progress /device-api/v1/thumbnail /device-api/v1/cover /device-api/v1/pdf/info /device-api/v1/pdf/page /device-api/v1/epub/info /device-api/v1/epub/page /device-api/v1/comics/manifest /device-api/v1/comics/page /device-api/v1/openapi.json /device-api/v1/docs
    }}
    @device_session_revoke {{
        remote_ip {lan_cidrs}
        method DELETE
        path /device-api/v1/session
    }}
    @device_progress_write {{
        remote_ip {lan_cidrs}
        method PUT
        path /device-api/v1/progress
    }}
    handle @device_api {{
        uri strip_prefix /device-api
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Api 1
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    handle @device_session_revoke {{
        uri strip_prefix /device-api
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Api 1
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    handle @device_progress_write {{
        uri strip_prefix /device-api
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Api 1
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    @unknown_device_api {{
        remote_ip {lan_cidrs}
        path /device-api /device-api/*
    }}
    handle @unknown_device_api {{
        respond "Unknown device API" 404
    }}

    @lan remote_ip {lan_cidrs}
    handle @lan {{
        @not_options not method OPTIONS
        basic_auth @not_options {{
            {username} {password_hash}
        }}

        handle /tag-api/device-sessions {{
            uri strip_prefix /tag-api
            reverse_proxy tag-server:8081 {{
                header_up X-Dufs-Device-Provisioning 1
                header_up -X-Dufs-Device-Api
            }}
        }}
        handle /tag-api/v1/device-enrollments* {{
            uri strip_prefix /tag-api
            reverse_proxy tag-server:8081 {{
                header_up X-Dufs-Device-Provisioning 1
                header_up -X-Dufs-Device-Api
            }}
        }}
        handle /tag-api/v1/device-tokens* {{
            uri strip_prefix /tag-api
            reverse_proxy tag-server:8081 {{
                header_up X-Dufs-Device-Provisioning 1
                header_up -X-Dufs-Device-Api
            }}
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

    @device_transcription_upload {{
        method POST
        path /device-api/v1/transcriptions
    }}
    @device_transcription_read {{
        method GET HEAD
        path /device-api/v1/transcriptions/*
    }}
    handle @device_transcription_upload {{
        uri replace /device-api/v1/transcriptions /v1/device/transcriptions
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Api 1
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    handle @device_transcription_read {{
        uri replace /device-api/v1/transcriptions /v1/device/transcriptions
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Api 1
            header_up -X-Dufs-Device-Provisioning
        }}
    }}
    @device_enrollment {{
        method POST
        path /device-api/v1/enrollments /device-api/v1/enrollments/*/claim
    }}
    handle @device_enrollment {{
        uri replace /device-api/v1/enrollments /v1/device/enrollments
        reverse_proxy tag-server:8081 {{
            header_up -X-Dufs-Device-Api
            header_up -X-Dufs-Device-Provisioning
        }}
    }}

    @public_device_api path /device-api /device-api/*
    respond @public_device_api "Not found" 404

{auth_block}
    handle /tag-api/v1/device-enrollments* {{
        uri strip_prefix /tag-api
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Provisioning 1
            header_up -X-Dufs-Device-Api
        }}
    }}
    handle /tag-api/v1/device-tokens* {{
        uri strip_prefix /tag-api
        reverse_proxy tag-server:8081 {{
            header_up X-Dufs-Device-Provisioning 1
            header_up -X-Dufs-Device-Api
        }}
    }}
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
    tag_data = paths["tag_data"]
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
    source_mode = "" if features["dufs_write"] else ":ro"
    dufs_volumes = [f"{workspace}:/data{source_mode}"]
    tag_volumes = [
        f"{workspace}:/workspace{source_mode}",
        f"{tag_data}:/data",
    ]
    if paths.get("media"):
        dufs_volumes.append(f"{paths['media']}:/data/media{source_mode}")
        tag_volumes.append(f"{paths['media']}:/workspace/media{source_mode}")
    if paths.get("whisper_models"):
        tag_volumes.append(f"{paths['whisper_models']}:/models:ro")

    tag_secret = secret_dir / "tag-server.env"
    if is_file(tag_secret):
        tag_volumes.append(f"{tag_secret}:/run/secrets/tag-server.env:ro")
    cors_args = "".join(
        f" --cors-origin {shlex.quote(origin)}"
        for origin in table(config, "security").get("cors_origins", [])
    )

    dufs_command = []
    if features["dufs_write"]:
        dufs_command = [
            "    command:",
            "      - /data",
            "      - --allow-all",
            "      - --allow-symlink",
            "      - --allow-archive",
        ]

    lines = [
        "services:",
        "  caddy:",
        "    volumes:",
        yaml_list(caddy_volumes, 6),
        "  dufs:",
        *dufs_command,
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
        f"        exec /app/tag-server --database /data/tag_all.db --workspace /workspace --metadata-dir /data/metadata --addr 0.0.0.0:8081{cors_args}",
        "    volumes:",
        yaml_list(tag_volumes, 6),
    ]

    if features["authelia"]:
        lines.extend(
            [
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
        )

    if features["readonly"]:
        readonly_tag_data = paths["readonly_tag_data"]
        readonly_tag_volumes = [
            f"{paths['readonly']}:/workspace:ro",
            f"{readonly_tag_data}:/data",
        ]
        if is_file(tag_secret):
            readonly_tag_volumes.append(
                f"{tag_secret}:/run/secrets/tag-server.env:ro"
            )
        lines.extend(
            [
                "  dufs-readonly:",
                "    volumes:",
                yaml_list(
                    [
                        f"{paths['readonly']}:/data:ro",
                    ],
                    6,
                ),
                "  tag-server-readonly:",
                '    entrypoint: ["/bin/sh", "-ec"]',
                "    command:",
                "      - |",
                "        if [ -f /run/secrets/tag-server.env ]; then",
                "          set -a",
                "          . /run/secrets/tag-server.env",
                "          set +a",
                "        fi",
                f"        exec /app/tag-server --database /data/tag_all.db --workspace /workspace --metadata-dir /data/metadata --addr 0.0.0.0:8081{cors_args}",
                "    volumes:",
                yaml_list(readonly_tag_volumes, 6),
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


def compose_asset_names(config: dict[str, Any]) -> list[str]:
    profile = table(config, "deployment")["profile"]
    features = table(config, "features")
    files = ["compose.yaml", f"compose.{profile}.yaml", "compose.instance.yaml"]
    if features["authelia"]:
        files.insert(2, "compose.authelia.yaml")
    if features["readonly"]:
        files.insert(2, "compose.readonly.yaml")
    if features["ddns"]:
        files.insert(2, "compose.ddns.yaml")
    return files


def sync_runtime_secrets(source: Path, destination: Path) -> None:
    """Materialize git-crypt plaintext into a stable private runtime directory."""
    if source.resolve() == destination.resolve():
        return
    if source.is_symlink() or not source.is_dir():
        raise ConfigError(
            f"secret source must be a directory, not a symlink: {source}"
        )
    if destination.exists() and (
        destination.is_symlink() or not destination.is_dir()
    ):
        raise ConfigError(
            f"runtime secret destination must be a directory, not a symlink: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.chmod(0o700)
    for source_path in source.iterdir():
        if source_path.name in {"README.md", ".gitignore"}:
            continue
        if source_path.is_symlink():
            raise ConfigError(
                f"secret source must not contain symlinks: {source_path}"
            )
        if not source_path.is_file():
            continue
        if source_path.read_bytes().startswith(b"\x00GITCRYPT"):
            raise ConfigError(
                f"secret source is still git-crypt encrypted; unlock the repository: {source_path}"
            )
        destination_path = destination / source_path.name
        if destination_path.is_symlink():
            raise ConfigError(
                f"runtime secret destination must not contain symlinks: {destination_path}"
            )
        temporary_path: Path | None = None
        try:
            with source_path.open("rb") as source_file, tempfile.NamedTemporaryFile(
                dir=destination,
                prefix=f".{source_path.name}.",
                delete=False,
            ) as temporary_file:
                shutil.copyfileobj(source_file, temporary_file)
                temporary_path = Path(temporary_file.name)
            temporary_path.chmod(0o600)
            temporary_path.replace(destination_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def install_runtime_compose_assets(
    deploy_dir: Path, output: Path, config: dict[str, Any]
) -> list[Path]:
    names = compose_asset_names(config)
    for name in names:
        if name == "compose.instance.yaml":
            continue
        destination = output / name
        shutil.copyfile(deploy_dir / name, destination)
        destination.chmod(0o600)
    if table(config, "features")["readonly"]:
        destination = output / "haproxy.readonly.cfg"
        shutil.copyfile(deploy_dir / destination.name, destination)
        # The official HAProxy image runs as uid 99 rather than root. A
        # rootless bind mount of a host-owned 0600 file is therefore
        # unreadable inside the container and makes readonly-gateway restart
        # forever. This file contains routing only (no credentials), so keep
        # private runtime assets at 0600 but make this one config readable.
        destination.chmod(0o644)
    return [output / name for name in names]


def render(config_path: Path, output: Path) -> None:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    validate(config)

    deploy_dir = Path(__file__).resolve().parents[1]
    paths = table(config, "paths")
    secret_dir = Path(paths["secrets"])
    secret_source = Path(paths.get("secret_source", paths["secrets"]))
    sync_runtime_secrets(secret_source, secret_dir)
    profile = table(config, "deployment")["profile"]
    features = table(config, "features")
    required_secrets: list[str] = []
    if features["authelia"]:
        required_secrets.extend(
            [
                "authelia_jwt_secret",
                "authelia_session_secret",
                "authelia_storage_key",
                "authelia_users_database.yml",
            ]
        )
    if profile == "home-ipv6-cdn" or features["readonly"]:
        required_secrets.append("caddy_lan_basic_auth")
    missing = [
        str(secret_dir / name)
        for name in required_secrets
        if not is_file(secret_dir / name)
    ]
    if missing:
        raise ConfigError(
            "missing runtime secrets; unlock and provision the configured secret source:\n  "
            + "\n  ".join(missing)
        )

    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    authelia_dir = output / "authelia"
    if features["authelia"]:
        authelia_dir.mkdir(exist_ok=True)
        authelia_dir.chmod(0o700)

    lan_auth = (
        read_lan_auth(secret_dir)
        if profile == "home-ipv6-cdn" or features["readonly"]
        else ("unused", "$2a$04$unusedunusedunusedunusedunusedunusedunusedunusedunused")
    )
    caddyfile = output / "Caddyfile"
    caddyfile.write_text(render_caddy(config, lan_auth), encoding="utf-8")
    caddyfile.chmod(0o600)

    if features["authelia"]:
        authelia_config = authelia_dir / "configuration.yml"
        authelia_config.write_text(render_authelia(config), encoding="utf-8")
        authelia_config.chmod(0o600)

    instance_compose = output / "compose.instance.yaml"
    instance_compose.write_text(
        render_instance_compose(config, output, secret_dir), encoding="utf-8"
    )
    instance_compose.chmod(0o600)

    deployment = table(config, "deployment")
    engine = table(config, "runtime")["engine"]
    images = table(config, "images")
    ports = table(config, "ports")
    security = table(config, "security")
    env = [
        env_line("COMPOSE_PROJECT_NAME", deployment["name"]),
        env_line("TZ", deployment["timezone"]),
        env_line("CADDY_IMAGE", images["caddy"]),
        env_line("READONLY_GATEWAY_IMAGE", images["readonly_gateway"]),
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

    files = install_runtime_compose_assets(deploy_dir, output, config)
    (output / "compose-files.txt").write_text(
        "\n".join(str(path) for path in files) + "\n", encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": config["schema_version"],
                "profile": deployment["profile"],
                "engine": engine,
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
    host_home = paths["host_home"]
    host_username = Path(host_home).name
    host_path = (
        f"{host_home}/.nix-profile/bin:"
        "/nix/var/nix/profiles/default/bin:"
        f"/etc/profiles/per-user/{host_username}/bin:"
        "/run/current-system/sw/bin:/usr/bin:/bin"
    )

    compose_control = output / "compose-control"
    compose_command = [
        engine,
        "compose",
        "--env-file",
        str(output / "compose.env"),
    ]
    for path in files:
        compose_command.extend(["-f", str(path)])
    compose_control.write_text(
        "#!/bin/sh\nset -eu\nexec "
        + shlex.join(compose_command)
        + ' "$@"\n',
        encoding="utf-8",
    )
    compose_control.chmod(0o700)

    unit = f"""[Unit]
Description=dufs-plus {engine.capitalize()} Compose stack
Wants=network-online.target
After=network-online.target
{terminal_dependency}

[Service]
Type=oneshot
RemainAfterExit=yes
Restart=on-failure
RestartSec=15s
WorkingDirectory={output}
Environment=HOME={host_home}
Environment=PATH={host_path}
ExecStart={compose_control} up -d
ExecStop={compose_control} down
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
        home_dir = paths["host_home"]
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
        "--config", type=Path, default=deploy_dir / "instances/home.toml"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
        )
        / "dufs-plus/runtime/home",
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
