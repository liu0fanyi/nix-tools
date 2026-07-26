#!/usr/bin/env python3
"""Import the current Home Manager secrets without printing their values."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path


def write_secret(path: Path, content: str) -> None:
    path.write_text(content.rstrip("\n") + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    deploy_dir = Path(__file__).resolve().parents[1]
    repo_dir = deploy_dir.parent
    home = Path.home()

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", type=Path, default=repo_dir / "secrets.json")
    parser.add_argument("--output", type=Path, default=deploy_dir / "secrets")
    parser.add_argument(
        "--authelia-users",
        type=Path,
        default=home / ".config/authelia/users_database.yml",
    )
    parser.add_argument("--tag-env", type=Path, default=home / "tag_secrets.env")
    parser.add_argument(
        "--caddyfile", type=Path, default=home / ".config/caddy/Caddyfile"
    )
    args = parser.parse_args()

    source = json.loads(args.source_json.read_text(encoding="utf-8"))
    required = {
        "authelia_jwt_secret",
        "authelia_session_secret",
        "authelia_storage_key",
        "dufs_auth",
    }
    missing = sorted(required - source.keys())
    if missing:
        raise SystemExit(f"missing keys in {args.source_json}: {', '.join(missing)}")

    args.output.mkdir(parents=True, exist_ok=True)
    args.output.chmod(0o700)

    for key in (
        "authelia_jwt_secret",
        "authelia_session_secret",
        "authelia_storage_key",
    ):
        write_secret(args.output / key, str(source[key]))

    auth_rule = str(source["dufs_auth"])
    dufs_config = "\n".join(
        [
            "serve-path: /data",
            "bind: 0.0.0.0",
            "port: 5000",
            "auth:",
            f"  - {json.dumps(auth_rule, ensure_ascii=False)}",
            "allow-symlink: true",
            "",
        ]
    )
    write_secret(args.output / "dufs-readonly.yaml", dufs_config)

    if not args.authelia_users.is_file():
        raise SystemExit(f"missing Authelia users file: {args.authelia_users}")
    shutil.copyfile(args.authelia_users, args.output / "authelia_users_database.yml")
    (args.output / "authelia_users_database.yml").chmod(0o600)

    if args.tag_env.is_file():
        shutil.copyfile(args.tag_env, args.output / "tag-server.env")
        (args.output / "tag-server.env").chmod(0o600)

    caddy_text = args.caddyfile.read_text(encoding="utf-8")
    match = re.search(
        r"(?m)^\s*([A-Za-z0-9_.-]+)\s+(\$2[aby]\$\d+\$[./A-Za-z0-9]+)\s*$",
        caddy_text,
    )
    if not match:
        raise SystemExit(f"unable to find Caddy basic_auth entry in {args.caddyfile}")
    write_secret(args.output / "caddy_lan_basic_auth", f"{match[1]} {match[2]}")

    print(f"Imported runtime secrets into {args.output} (values not displayed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
