#!/usr/bin/env python3
"""Perform the explicit in-place cutover with automatic service rollback."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
import time
import tomllib
from pathlib import Path


DEPLOY_DIR = Path(__file__).resolve().parents[1]
MANAGE = DEPLOY_DIR / "scripts" / "manage.py"


def run(argv: list[str], check: bool = True) -> int:
    return subprocess.run(argv, check=check).returncode


def unit_active(unit: str) -> bool:
    return (
        subprocess.run(
            ["systemctl", "--user", "is-active", "--quiet", unit], check=False
        ).returncode
        == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=DEPLOY_DIR / "instances/home.toml"
    )
    parser.add_argument("--output", type=Path, default=DEPLOY_DIR / ".generated/home")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--smoke-url")
    args = parser.parse_args()

    if not args.confirm:
        print("refusing production cutover without --confirm", file=sys.stderr)
        return 2

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    profile = config["deployment"]["profile"]
    features = config["features"]
    tag_data = Path(config["paths"]["tag_data"])
    smoke_port = (
        config["ports"]["main_origin"]
        if profile == "home-ipv6-cdn"
        else config["ports"]["https"]
    )
    smoke_host = config["domains"]["public"]
    smoke_url = args.smoke_url or f"https://{smoke_host}:{smoke_port}"

    old_units = [
        "caddy.service",
        "ttyd.service",
        "podman-ddns-go.service",
        "podman-authelia.service",
        "podman-tag-server.service",
        "podman-dufs-lan.service",
        "podman-dufs.service",
    ]
    if profile != "home-ipv6-cdn":
        old_units.remove("podman-ddns-go.service")
    active_before = [unit for unit in old_units if unit_active(unit)]

    manage_base = [
        sys.executable,
        str(MANAGE),
        "--config",
        str(args.config),
        "--output",
        str(args.output),
    ]
    run(manage_base + ["preflight"])
    run(manage_base + ["backup"])

    stopped: list[str] = []
    compose_started = False
    terminal_unit_created = False
    terminal_unit_started = False
    try:
        unit_dir = Path.home() / ".config/systemd/user"
        unit_dir.mkdir(parents=True, exist_ok=True)
        if features["terminal"]:
            terminal_unit_target = unit_dir / "ttyd-compose.service"
            if not terminal_unit_target.exists():
                shutil.copy2(
                    args.output / "ttyd-compose.service",
                    terminal_unit_target,
                )
                terminal_unit_target.chmod(0o600)
                terminal_unit_created = True
            run(["systemctl", "--user", "daemon-reload"])
            run(
                [
                    "systemctl",
                    "--user",
                    "enable",
                    "--now",
                    "ttyd-compose.service",
                ]
            )
            terminal_unit_started = True
            socket_path = Path(config["paths"]["terminal_socket_dir"]) / "ttyd.sock"
            for _ in range(50):
                if socket_path.is_socket():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError(f"host terminal socket was not created: {socket_path}")

        for unit in active_before:
            run(["systemctl", "--user", "stop", unit])
            stopped.append(unit)

        tag_db = tag_data / "tag_all.db"
        connection = sqlite3.connect(tag_db)
        try:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            connection.close()

        run(manage_base + ["backup"])
        compose_started = True
        run(manage_base + ["up", "--confirm-cutover"])
        smoke_args = manage_base + [
            "smoke",
            "--base-url",
            smoke_url,
            "--wait-seconds",
            "45",
        ]
        if args.smoke_url is None:
            smoke_args.extend(["--resolve-address", "127.0.0.1"])
        run(smoke_args)

        shutil.copy2(
            args.output / "dufs-plus-compose.service",
            unit_dir / "dufs-plus-compose.service",
        )
        (unit_dir / "dufs-plus-compose.service").chmod(0o600)
        run(["systemctl", "--user", "daemon-reload"])
        run(
            [
                "systemctl",
                "--user",
                "enable",
                "--now",
                "dufs-plus-compose.service",
            ]
        )
        for unit in old_units:
            run(["systemctl", "--user", "disable", unit], check=False)

        print("Production cutover completed and the Compose user service is enabled.")
        return 0
    except Exception as error:
        print(f"cutover failed, rolling back: {error}", file=sys.stderr)
        if compose_started:
            run(manage_base + ["down"], check=False)
        if terminal_unit_started:
            run(
                ["systemctl", "--user", "disable", "--now", "ttyd-compose.service"],
                check=False,
            )
        if terminal_unit_created:
            (Path.home() / ".config/systemd/user/ttyd-compose.service").unlink(
                missing_ok=True
            )
            run(["systemctl", "--user", "daemon-reload"], check=False)
        for unit in reversed(stopped):
            run(["systemctl", "--user", "start", unit], check=False)
        print("Rollback attempted; inspect all service states.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
