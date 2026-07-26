#!/usr/bin/env python3
"""Build once and release dufs-plus and tag-server to home and Aliyun."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path


NIX_TOOLS = Path(__file__).resolve().parents[2]
WORKSPACE = NIX_TOOLS.parent
HOME_CONFIG = NIX_TOOLS / "deploy/instances/home.toml"
HOME_OUTPUT = NIX_TOOLS / "deploy/.generated/home"
MANAGE = NIX_TOOLS / "deploy/scripts/manage.py"


def run(argv: list[str], cwd: Path | None = None) -> None:
    print("+", shlex.join(argv), flush=True)
    subprocess.run(argv, cwd=cwd, check=True)


def remote_run(remote: str, remote_root: str, argv: list[str]) -> None:
    command = f"cd {shlex.quote(remote_root)} && {shlex.join(argv)}"
    run(["ssh", remote, command])


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


def deploy_tag_server(
    tag_source: Path, remote: str, remote_root: str, image: str
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
    run(
        [
            "python3",
            str(MANAGE),
            "--config",
            str(HOME_CONFIG),
            "--output",
            str(HOME_OUTPUT),
            "recreate",
            "tag-server",
        ],
        cwd=NIX_TOOLS,
    )
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
            "recreate",
            "tag-server",
        ],
    )


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
        choices=("all", "frontend", "tag-server", "runtime-images"),
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
            )
        if args.component == "runtime-images":
            deploy_runtime_images(args.remote)
        if not args.skip_smoke:
            smoke(args.remote, args.remote_root)
    except subprocess.CalledProcessError as error:
        print(f"release failed with exit code {error.returncode}", file=sys.stderr)
        return error.returncode or 1
    print("Release completed on home and Aliyun.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
