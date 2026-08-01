#!/usr/bin/env python3
"""Build once and release dufs-plus and tag-server to home and Aliyun."""

from __future__ import annotations

import argparse
import hashlib
import shlex
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path


NIX_TOOLS = Path(__file__).resolve().parents[2]
WORKSPACE = NIX_TOOLS.parent
HOME_CONFIG = NIX_TOOLS / "deploy/instances/home.toml"
HOME_OUTPUT = NIX_TOOLS / "deploy/.generated/home"
MANAGE = NIX_TOOLS / "deploy/scripts/manage.py"


def run(argv: list[str], cwd: Path | None = None) -> None:
    print("+", shlex.join(argv), flush=True)
    subprocess.run(argv, cwd=cwd, check=True)


def capture(argv: list[str], cwd: Path | None = None) -> str:
    print("+", shlex.join(argv), flush=True)
    return subprocess.run(
        argv,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def remote_run(remote: str, remote_root: str, argv: list[str]) -> None:
    command = f"cd {shlex.quote(remote_root)} && {shlex.join(argv)}"
    run(["ssh", remote, command])


def manage_local(argv: list[str]) -> None:
    run(
        [
            "python3",
            str(MANAGE),
            "--config",
            str(HOME_CONFIG),
            "--output",
            str(HOME_OUTPUT),
            *argv,
        ],
        cwd=NIX_TOOLS,
    )


def manage_remote(remote: str, remote_root: str, argv: list[str]) -> None:
    remote_run(
        remote,
        remote_root,
        [
            "python3",
            "deploy/scripts/manage.py",
            "--config",
            "deploy/instances/aliyun.toml",
            "--output",
            "deploy/.generated/aliyun",
            *argv,
        ],
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_frontend(
    frontend: Path, remote: str, remote_root: str
) -> None:
    local_index = (frontend / "dist/index.html").read_bytes()
    local_hash = sha256_bytes(local_index)
    remote_output = capture(
        [
            "ssh",
            remote,
            f"sha256sum {shlex.quote(remote_root + '/dist/index.html')}",
        ]
    )
    remote_hash = remote_output.split(maxsplit=1)[0]

    config = tomllib.loads(
        (NIX_TOOLS / "deploy/instances/aliyun.toml").read_text(encoding="utf-8")
    )
    domains = config["domains"]
    public_host = domains.get("aliases", [domains["public"]])[0]
    public_url = f"https://{public_host}/index.html?release={local_hash[:16]}"
    request = urllib.request.Request(
        public_url,
        headers={"Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        public_hash = sha256_bytes(response.read())

    print(
        "Frontend SHA-256: "
        f"local={local_hash} remote={remote_hash} public={public_hash}"
    )
    if len({local_hash, remote_hash, public_hash}) != 1:
        raise RuntimeError("frontend artifacts differ between local, VPS, and public CDN")


def deploy_frontend(
    frontend: Path, remote: str, remote_root: str, skip_bevy: bool
) -> None:
    run(["just", "deploy", "true" if skip_bevy else "false"], cwd=frontend)
    source = str(frontend / "dist") + "/"
    destination = f"{remote}:{remote_root}/dist/"
    # Hashed assets are transferred first and index.html last so the remote
    # browser never receives an index that references files not uploaded yet.
    run(
        [
            "rsync",
            "-az",
            "--delete",
            "--delay-updates",
            "--exclude",
            "index.html",
            source,
            destination,
        ]
    )
    run(["rsync", "-az", str(frontend / "dist/index.html"), destination])
    verify_frontend(frontend, remote, remote_root)


def transfer_image(image: str, remote: str) -> None:
    print(f"+ podman save {image} | zstd | ssh {remote} 'zstd -d | docker load'", flush=True)
    save = subprocess.Popen(["podman", "save", image], stdout=subprocess.PIPE)
    assert save.stdout is not None
    compress = subprocess.Popen(
        ["zstd", "-T0", "-3", "-c"],
        stdin=save.stdout,
        stdout=subprocess.PIPE,
    )
    save.stdout.close()
    assert compress.stdout is not None
    load = subprocess.Popen(
        ["ssh", remote, "zstd -d | docker load"],
        stdin=compress.stdout,
    )
    compress.stdout.close()
    load_status = load.wait()
    compress_status = compress.wait()
    save_status = save.wait()
    if save_status or compress_status or load_status:
        raise subprocess.CalledProcessError(
            load_status or compress_status or save_status,
            ["podman", "save", image],
        )
    # Keep every archive single-image. Podman multi-image archives have shown
    # incompatible tag assignment when loaded by Docker.
    remote_run(
        remote,
        "/",
        ["docker", "image", "inspect", image],
    )


def deploy_runtime_images(remote: str) -> None:
    config = tomllib.loads(HOME_CONFIG.read_text(encoding="utf-8"))
    images = config["images"]
    for image in (images["caddy"], images["dufs"], images["tag_server"]):
        transfer_image(image, remote)


def deploy_configuration(
    remote: str,
    remote_root: str,
    *,
    backup: bool,
) -> None:
    run(
        [
            "rsync",
            "-az",
            "--exclude",
            "secrets",
            "--exclude",
            ".generated",
            "--exclude",
            "__pycache__",
            f"{NIX_TOOLS / 'deploy'}/",
            f"{remote}:{remote_root}/deploy/",
        ]
    )
    if backup:
        manage_local(["backup"])
        manage_remote(remote, remote_root, ["backup"])
    manage_local(["up", "--confirm"])
    manage_remote(remote, remote_root, ["up", "--confirm"])
    # Compose does not necessarily recreate Caddy when only the contents of its
    # bind-mounted generated Caddyfile change.
    manage_local(["recreate", "caddy"])
    manage_remote(remote, remote_root, ["recreate", "caddy"])


def deploy_tag_server(
    tag_source: Path,
    remote: str,
    remote_root: str,
    image: str,
    *,
    recreate: bool = True,
) -> None:
    run(["podman", "build", "-t", image, "-f", "Containerfile", "."], cwd=tag_source)

    run(
        [
            "python3",
            str(MANAGE),
            "--config",
            str(HOME_CONFIG),
            "--output",
            str(HOME_OUTPUT),
            "backup",
        ],
        cwd=NIX_TOOLS,
    )
    remote_manage = "deploy/scripts/manage.py"
    remote_config = "deploy/instances/aliyun.toml"
    remote_output = "deploy/.generated/aliyun"
    remote_run(
        remote,
        remote_root,
        [
            "python3",
            remote_manage,
            "--config",
            remote_config,
            "--output",
            remote_output,
            "backup",
        ],
    )

    transfer_image(image, remote)
    if recreate:
        manage_local(["recreate", "tag-server"])
        manage_local(["recreate", "tag-server-readonly"])
        manage_remote(remote, remote_root, ["recreate", "tag-server"])


def smoke(remote: str, remote_root: str) -> None:
    run(
        [
            "python3",
            str(MANAGE),
            "--config",
            str(HOME_CONFIG),
            "smoke",
            "--base-url",
            "https://nas.wttliou.top:5009",
            "--resolve-address",
            "127.0.0.1",
            "--wait-seconds",
            "30",
        ],
        cwd=NIX_TOOLS,
    )
    remote_run(
        remote,
        remote_root,
        [
            "python3",
            "deploy/scripts/manage.py",
            "--config",
            "deploy/instances/aliyun.toml",
            "smoke",
            "--base-url",
            "http://wttliou.top",
            "--resolve-address",
            "127.0.0.1",
            "--wait-seconds",
            "30",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "component",
        choices=("all", "config", "frontend", "tag-server", "runtime-images"),
        nargs="?",
        default="all",
    )
    parser.add_argument("--remote", default="root@47.93.153.102")
    parser.add_argument("--remote-root", default="/root/nix-tools")
    parser.add_argument("--frontend-source", type=Path, default=WORKSPACE / "dufs-plus")
    parser.add_argument("--tag-source", type=Path, default=WORKSPACE / "tag-all")
    parser.add_argument("--skip-bevy", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()

    image = "localhost/tag-server:dufs-plus"
    try:
        if args.component in {"all", "frontend"}:
            deploy_frontend(
                args.frontend_source.resolve(),
                args.remote,
                args.remote_root,
                args.skip_bevy,
            )
        if args.component in {"all", "tag-server"}:
            deploy_tag_server(
                args.tag_source.resolve(),
                args.remote,
                args.remote_root,
                image,
                recreate=args.component != "all",
            )
        if args.component in {"all", "config"}:
            # The tag-server release already made a consistent backup for
            # `all`; a config-only rollout needs its own backup.
            deploy_configuration(
                args.remote,
                args.remote_root,
                backup=args.component == "config",
            )
        if args.component == "runtime-images":
            deploy_runtime_images(args.remote)
        if not args.skip_smoke:
            smoke(args.remote, args.remote_root)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            return_code = error.returncode or 1
        else:
            return_code = 1
        print(f"release failed with exit code {return_code}", file=sys.stderr)
        print(f"reason: {error}", file=sys.stderr)
        return return_code
    print("Release completed on home and Aliyun.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
