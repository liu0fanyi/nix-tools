#!/usr/bin/env python3
"""Start an isolated copy of the stack on temporary ports, test it, then stop it."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEPLOY_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DEPLOY_DIR / "scripts"))

import render as renderer
from isolated_test_helpers import replace_key


def sqlite_backup(source: Path, destination: Path) -> None:
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def compose_argv(output: Path, action: list[str]) -> list[str]:
    files = [
        line
        for line in (output / "compose-files.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    argv = [
        "podman",
        "compose",
        "--env-file",
        str(output / "compose.env"),
    ]
    for path in files:
        argv.extend(["-f", path])
    return argv + action


def curl_status(url: str, resolve: str | None = None) -> int:
    argv = [
        "curl",
        "--silent",
        "--show-error",
        "--insecure",
        "--output",
        "/dev/null",
        "--write-out",
        "%{http_code}",
        "--max-time",
        "15",
    ]
    if resolve:
        argv.extend(["--resolve", resolve])
    argv.append(url)
    result = subprocess.run(argv, check=True, text=True, capture_output=True)
    return int(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=DEPLOY_DIR / "instances/home.toml"
    )
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    original = args.config.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="dufs-plus-stack-") as temp_name:
        temp = Path(temp_name)
        workspace = temp / "workspace"
        readonly = temp / "readonly"
        authelia_data = temp / "authelia-data"
        caddy_data = temp / "caddy-data"
        caddy_config = temp / "caddy-config"
        generated = temp / "generated"
        for path in (
            workspace,
            readonly,
            authelia_data,
            caddy_data,
            caddy_config,
        ):
            path.mkdir(parents=True)

        sqlite_backup(Path("/home/liou/dufs-lan/tag_all.db"), workspace / "tag_all.db")
        sqlite_backup(
            Path("/home/liou/.local/share/authelia/db.sqlite3"),
            authelia_data / "db.sqlite3",
        )
        (workspace / "isolated-test.txt").write_text("isolated test\n", encoding="utf-8")
        (readonly / "isolated-readonly.txt").write_text(
            "isolated readonly test\n", encoding="utf-8"
        )

        text = replace_key(original, "deployment", "name", '"dufs-plus-test"')
        text = replace_key(text, "features", "ddns", "false")
        text = replace_key(text, "features", "terminal", "false")
        text = replace_key(text, "paths", "workspace", f'"{workspace}"')
        text = replace_key(text, "paths", "tag_data", f'"{workspace}"')
        text = replace_key(text, "paths", "readonly", f'"{readonly}"')
        text = replace_key(text, "paths", "media", '""')
        text = replace_key(text, "paths", "authelia_data", f'"{authelia_data}"')
        text = replace_key(text, "paths", "caddy_data", f'"{caddy_data}"')
        text = replace_key(text, "paths", "caddy_config", f'"{caddy_config}"')
        text = replace_key(
            text, "security", "container_subnet", '"10.89.51.0/24"'
        )
        test_config = temp / "instance.toml"
        test_config.write_text(text, encoding="utf-8")

        renderer.render(test_config, generated)
        env_path = generated / "compose.env"
        env_text = env_path.read_text(encoding="utf-8")
        env_text = env_text.replace("LAN_PUBLISH_PORT=5006", "LAN_PUBLISH_PORT=15006")
        env_text = env_text.replace(
            "READONLY_ORIGIN_PUBLISH_PORT=5008",
            "READONLY_ORIGIN_PUBLISH_PORT=15008",
        )
        env_text = env_text.replace(
            "MAIN_ORIGIN_PUBLISH_PORT=5009", "MAIN_ORIGIN_PUBLISH_PORT=15009"
        )
        env_path.write_text(env_text, encoding="utf-8")
        up = compose_argv(generated, ["up", "-d"])
        down = compose_argv(generated, ["down"])
        started = False
        try:
            subprocess.run(up, check=True)
            started = True
            deadline = time.monotonic() + 45
            statuses: tuple[int, int, int] | None = None
            while time.monotonic() < deadline:
                try:
                    lan = curl_status("http://127.0.0.1:15006/")
                    main = curl_status(
                        "https://nas.wttliou.top:15009/",
                        "nas.wttliou.top:15009:127.0.0.1",
                    )
                    portal = curl_status(
                        "https://nas.wttliou.top:15009/authelia/",
                        "nas.wttliou.top:15009:127.0.0.1",
                    )
                    statuses = (lan, main, portal)
                    if lan == 401 and main in {302, 401} and portal in {200, 302}:
                        break
                except (subprocess.CalledProcessError, ValueError):
                    pass
                time.sleep(1)
            else:
                subprocess.run(
                    compose_argv(generated, ["ps"]), check=False
                )
                subprocess.run(
                    compose_argv(generated, ["logs", "--no-color"]), check=False
                )
                raise RuntimeError(f"isolated smoke test timed out; statuses={statuses}")

            print(
                "Isolated stack passed: "
                f"LAN={statuses[0]}, main={statuses[1]}, Authelia={statuses[2]}"
            )
        finally:
            if started and not args.keep:
                subprocess.run(down, check=False)
            elif started:
                print(f"Kept isolated stack and files at {temp}")
                input("Press Enter to stop and remove the isolated stack...")
                subprocess.run(down, check=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"isolated test failed: {error}", file=sys.stderr)
        raise SystemExit(1)
