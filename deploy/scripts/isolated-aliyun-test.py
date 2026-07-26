#!/usr/bin/env python3
"""Exercise the Aliyun HTTP profile locally with Podman on port 15080."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import render as renderer
from isolated_test_helpers import replace_key


DEPLOY_DIR = Path(__file__).resolve().parents[1]


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
        for line in (output / "compose-files.txt").read_text().splitlines()
        if line.strip()
    ]
    argv = ["podman", "compose", "--env-file", str(output / "compose.env")]
    for path in files:
        argv.extend(["-f", path])
    return argv + action


def status(path: str, forwarded_http: bool = False) -> int:
    argv = [
        "curl",
        "--silent",
        "--show-error",
        "--output",
        "/dev/null",
        "--write-out",
        "%{http_code}",
        "--max-time",
        "15",
        "--resolve",
        "wttliou.top:15080:127.0.0.1",
    ]
    if forwarded_http:
        argv.extend(["--header", "X-Forwarded-Proto: http"])
    argv.append(f"http://wttliou.top:15080{path}")
    return int(subprocess.run(argv, check=True, text=True, capture_output=True).stdout)


def main() -> int:
    source = DEPLOY_DIR / "instances/aliyun.toml"
    original = source.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="dufs-plus-aliyun-") as temp_name:
        temp = Path(temp_name)
        workspace = temp / "workspace"
        tag_data = temp / "tag-data"
        caddy_data = temp / "caddy-data"
        caddy_config = temp / "caddy-config"
        generated = temp / "generated"
        for path in (workspace, tag_data, caddy_data, caddy_config):
            path.mkdir()
        sqlite_backup(Path("/home/liou/dufs-lan/tag_all.db"), tag_data / "tag_all.db")
        (workspace / "aliyun-profile-test.txt").write_text("ok\n", encoding="utf-8")

        text = replace_key(original, "deployment", "name", '"nix-tools-aliyun-test"')
        text = replace_key(text, "runtime", "engine", '"podman"')
        text = replace_key(text, "paths", "host_home", '"/home/liou"')
        text = replace_key(text, "paths", "workspace", f'"{workspace}"')
        text = replace_key(text, "paths", "tag_data", f'"{tag_data}"')
        text = replace_key(text, "paths", "dist", '"/home/liou/dufs-lan/dist"')
        text = replace_key(text, "paths", "caddy_data", f'"{caddy_data}"')
        text = replace_key(text, "paths", "caddy_config", f'"{caddy_config}"')
        text = replace_key(text, "ports", "http", "15080")
        text = replace_key(text, "security", "container_subnet", '"10.89.52.0/24"')
        config = temp / "instance.toml"
        config.write_text(text, encoding="utf-8")
        renderer.render(config, generated)

        up = compose_argv(generated, ["up", "-d"])
        down = compose_argv(generated, ["down"])
        started = False
        try:
            subprocess.run(up, check=True)
            started = True
            deadline = time.monotonic() + 45
            results: tuple[int, int, int, int] | None = None
            while time.monotonic() < deadline:
                try:
                    results = (
                        status("/"),
                        status("/?json"),
                        status("/tag-api/tags"),
                        status("/", forwarded_http=True),
                    )
                    if results == (200, 200, 200, 302):
                        break
                except (subprocess.CalledProcessError, ValueError):
                    pass
                time.sleep(1)
            else:
                subprocess.run(compose_argv(generated, ["ps"]), check=False)
                subprocess.run(
                    compose_argv(generated, ["logs", "--no-color"]), check=False
                )
                raise RuntimeError(f"Aliyun profile timed out; statuses={results}")
            print(
                "Aliyun profile passed: "
                f"UI={results[0]}, DUFS={results[1]}, tags={results[2]}, "
                f"EdgeOne redirect={results[3]}"
            )
        finally:
            if started:
                subprocess.run(down, check=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"isolated Aliyun test failed: {error}", file=sys.stderr)
        raise SystemExit(1)
