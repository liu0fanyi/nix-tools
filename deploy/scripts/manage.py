#!/usr/bin/env python3
"""Operational commands for the generated Docker or Podman deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import ssl
import stat
import subprocess
import sys
import tarfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import render as renderer


DEPLOY_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = DEPLOY_DIR / "instances/home.toml"
DEFAULT_OUTPUT = Path(
    os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
) / "dufs-plus/runtime/home"
DEFAULT_STATE_DIR = Path(
    os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")
) / "dufs-plus"
DEFAULT_BACKUP_KEEP = 5


def load_config(path: Path) -> dict[str, Any]:
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    renderer.validate(config)
    return config


def ensure_rendered(config_path: Path, output: Path) -> dict[str, Any]:
    renderer.render(config_path.resolve(), output.resolve())
    return load_config(config_path)


def compose_argv(output: Path, action: list[str]) -> list[str]:
    files_path = output / "compose-files.txt"
    files = [
        Path(line)
        for line in files_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(
        (output / "manifest.json").read_text(encoding="utf-8")
    )
    engine = manifest["engine"]
    argv = [
        engine,
        "compose",
        "--env-file",
        str(output / "compose.env"),
    ]
    for path in files:
        argv.extend(["-f", str(path)])
    argv.extend(action)
    return argv


def mode_is_private(path: Path) -> bool:
    return path.stat().st_mode & 0o077 == 0


def normalize_secret_permissions(secret_dir: Path) -> tuple[list[str], list[Path]]:
    """Remove group/world access from locally owned runtime secrets.

    Git only preserves the executable bit, so git-crypt may recreate tracked
    secrets using the host umask (for example, 0664 with umask 0002). Tighten
    those modes before preflight, but never follow symlinks or take ownership of
    files belonging to another user.
    """
    errors: list[str] = []
    changed: list[Path] = []
    if not secret_dir.exists() and not secret_dir.is_symlink():
        return errors, changed
    if secret_dir.is_symlink():
        return [
            f"secret directory must not be a symbolic link: {secret_dir}"
        ], changed

    try:
        directory_stat = secret_dir.lstat()
    except OSError as error:
        return [
            f"unable to inspect secret directory {secret_dir}: {error}"
        ], changed
    if not stat.S_ISDIR(directory_stat.st_mode):
        return errors, changed
    if directory_stat.st_uid != os.getuid():
        return [
            f"secret directory is not owned by the current user: {secret_dir}"
        ], changed

    directory_mode = stat.S_IMODE(directory_stat.st_mode)
    private_directory_mode = directory_mode & ~0o077
    if private_directory_mode != directory_mode:
        try:
            secret_dir.chmod(private_directory_mode)
            changed.append(secret_dir)
        except OSError as error:
            errors.append(
                f"unable to tighten secret directory mode {secret_dir}: {error}"
            )
            return errors, changed

    try:
        entries = list(secret_dir.iterdir())
    except OSError as error:
        errors.append(f"unable to list secret directory {secret_dir}: {error}")
        return errors, changed

    for path in entries:
        if path.name in {"README.md", ".gitignore"}:
            continue
        try:
            path_stat = path.lstat()
        except OSError as error:
            errors.append(f"unable to inspect secret path {path}: {error}")
            continue
        if stat.S_ISLNK(path_stat.st_mode):
            errors.append(f"secret path must not be a symbolic link: {path}")
            continue
        if not stat.S_ISREG(path_stat.st_mode):
            continue
        if path_stat.st_uid != os.getuid():
            errors.append(f"secret file is not owned by the current user: {path}")
            continue

        file_mode = stat.S_IMODE(path_stat.st_mode)
        private_file_mode = file_mode & ~0o077
        if private_file_mode != file_mode:
            try:
                path.chmod(private_file_mode)
                changed.append(path)
            except OSError as error:
                errors.append(f"unable to tighten secret file mode {path}: {error}")
    return errors, changed


def wait_for_mounts(paths: list[Path], wait_seconds: int = 30) -> list[Path]:
    deadline = time.monotonic() + wait_seconds
    while True:
        missing = [path for path in paths if not path.is_mount()]
        if not missing or time.monotonic() >= deadline:
            return missing
        time.sleep(1)


def preflight(config_path: Path, output: Path) -> int:
    config = ensure_rendered(config_path, output)
    paths = renderer.table(config, "paths")
    features = renderer.table(config, "features")
    engine = renderer.table(config, "runtime")["engine"]
    profile = renderer.table(config, "deployment")["profile"]
    errors: list[str] = []
    warnings: list[str] = []

    if profile == "home-ipv6-cdn" and not features["ddns"]:
        errors.append("home-ipv6-cdn production preflight requires DDNS-Go")

    required_mounts = [Path(path) for path in paths.get("required_mounts", [])]
    for path in wait_for_mounts(required_mounts):
        errors.append(f"required filesystem is not mounted: {path}")

    required_dirs = [
        "workspace",
        "tag_data",
        "dist",
        "caddy_data",
        "caddy_config",
    ]
    if features["authelia"]:
        required_dirs.extend(["authelia_data", "secrets"])
    if features["readonly"]:
        required_dirs.extend(["readonly", "readonly_tag_data"])
    if profile == "home-ipv6-cdn":
        required_dirs.append("ddns_config")
    if paths.get("media"):
        required_dirs.append("media")
    if features["terminal"]:
        required_dirs.append("terminal_workspace")

    for key in required_dirs:
        path = Path(paths[key])
        if not path.is_dir():
            errors.append(f"[paths].{key} is not a directory: {path}")
    if features["readonly"]:
        readonly_metadata = Path(paths["readonly_tag_data"]) / "metadata"
        if not readonly_metadata.is_dir():
            errors.append(
                "read-only tag metadata directory is missing: "
                f"{readonly_metadata}"
            )

    expected_files = [
        Path(paths["tag_data"]) / "tag_all.db",
        Path(paths["dist"]) / "index.html",
    ]
    if features["readonly"]:
        expected_files.append(Path(paths["readonly_tag_data"]) / "tag_all.db")
    if features["authelia"]:
        expected_files.append(Path(paths["authelia_data"]) / "db.sqlite3")
    if profile == "home-ipv6-cdn":
        expected_files.append(
            Path(paths["ddns_config"]) / ".ddns_go_config.yaml"
        )
    for path in expected_files:
        if not path.is_file():
            errors.append(f"missing runtime file: {path}")

    secret_dir = Path(paths["secrets"])
    permission_errors, normalized_paths = normalize_secret_permissions(secret_dir)
    errors.extend(permission_errors)
    for path in normalized_paths:
        warnings.append(f"tightened runtime secret permissions: {path}")
    if (
        secret_dir.is_dir()
        and not secret_dir.is_symlink()
        and not mode_is_private(secret_dir)
    ):
        errors.append(f"secret directory must not be group/world accessible: {secret_dir}")
    if secret_dir.is_dir() and not secret_dir.is_symlink():
        for path in secret_dir.iterdir():
            if path.is_symlink() and path.name not in {"README.md", ".gitignore"}:
                continue
            if path.is_file() and path.name not in {"README.md", ".gitignore"}:
                if not mode_is_private(path):
                    errors.append(f"secret file mode must be 0600 or stricter: {path}")

    commands = ["curl", engine]
    if engine == "podman":
        commands.append("podman-compose")
    for command in commands:
        if shutil.which(command) is None:
            errors.append(f"required command not found: {command}")
    if engine == "docker" and shutil.which("docker") is not None:
        result = subprocess.run(
            ["docker", "compose", "version"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            errors.append("Docker Compose plugin is not available")

    if features["terminal"]:
        expected_socket_dir = Path(f"/run/user/{os.getuid()}/ttyd")
        configured_socket_dir = Path(paths["terminal_socket_dir"])
        if configured_socket_dir != expected_socket_dir:
            errors.append(
                "[paths].terminal_socket_dir must match the systemd user runtime "
                f"directory: {expected_socket_dir}"
            )
        home_dir = Path(paths["host_home"])
        for command in ("ttyd", "zellij", "bash"):
            binary = home_dir / ".nix-profile/bin" / command
            if not binary.exists():
                errors.append(f"host terminal command not found: {binary}")

    images = renderer.table(config, "images")
    for name, image in images.items():
        if image.endswith(":latest"):
            warnings.append(f"[images].{name} is not version pinned: {image}")

    db_path = Path(paths["tag_data"]) / "tag_all.db"
    if db_path.is_file():
        try:
            connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            result = connection.execute("PRAGMA quick_check").fetchone()
            connection.close()
            if not result or result[0] != "ok":
                errors.append(f"Tag SQLite quick_check failed: {result}")
        except sqlite3.Error as error:
            errors.append(f"unable to check Tag SQLite: {error}")

    if features["readonly"]:
        readonly_tag_db = Path(paths["readonly_tag_data"]) / "tag_all.db"
        if readonly_tag_db.is_file():
            try:
                connection = sqlite3.connect(
                    f"file:{readonly_tag_db}?mode=ro", uri=True
                )
                result = connection.execute("PRAGMA quick_check").fetchone()
                connection.close()
                if not result or result[0] != "ok":
                    errors.append(
                        f"Read-only Tag SQLite quick_check failed: {result}"
                    )
            except sqlite3.Error as error:
                errors.append(f"unable to check read-only Tag SQLite: {error}")

    authelia_db = Path(paths["authelia_data"]) / "db.sqlite3"
    if features["authelia"] and authelia_db.is_file():
        try:
            connection = sqlite3.connect(f"file:{authelia_db}?mode=ro", uri=True)
            result = connection.execute("PRAGMA quick_check").fetchone()
            connection.close()
            if not result or result[0] != "ok":
                errors.append(f"Authelia SQLite quick_check failed: {result}")
        except sqlite3.Error as error:
            errors.append(f"unable to check Authelia SQLite: {error}")

    print(f"Profile: {profile}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"Preflight failed with {len(errors)} error(s).")
        return 1
    print("Preflight passed.")
    return 0


def sqlite_backup(source: Path, destination: Path) -> None:
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    destination.chmod(0o600)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prune_backups(destination_root: Path, keep_last: int) -> list[Path]:
    if keep_last <= 0 or not destination_root.is_dir():
        return []
    backups = sorted(
        path
        for path in destination_root.iterdir()
        if path.is_dir() and path.name[:8].isdigit()
    )
    removed = backups[:-keep_last]
    for path in removed:
        shutil.rmtree(path)
    return removed


def backup(
    config_path: Path,
    output: Path,
    destination_root: Path | None,
    keep_last: int,
) -> int:
    config = ensure_rendered(config_path, output)
    paths = renderer.table(config, "paths")
    if destination_root is None:
        deployment_name = renderer.table(config, "deployment")["name"]
        destination_root = DEFAULT_STATE_DIR / "backups" / deployment_name
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1_000_000_000:09d}"
    destination = destination_root / stamp
    destination.mkdir(parents=True, mode=0o700)
    destination.chmod(0o700)

    features = renderer.table(config, "features")
    tag_db = Path(paths["tag_data"]) / "tag_all.db"
    sqlite_backup(tag_db, destination / "tag_all.db")
    if features["readonly"]:
        readonly_tag_db = Path(paths["readonly_tag_data"]) / "tag_all.db"
        if readonly_tag_db.is_file():
            sqlite_backup(
                readonly_tag_db, destination / "readonly_tag_all.db"
            )
    if features["authelia"]:
        authelia_db = Path(paths["authelia_data"]) / "db.sqlite3"
        sqlite_backup(authelia_db, destination / "authelia.db.sqlite3")

    sidecar_archive = destination / "sidecars.tar.gz"
    with tarfile.open(sidecar_archive, "w:gz") as archive:
        workspace = Path(paths["workspace"])
        for path in workspace.rglob("*.tag"):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(workspace), recursive=False)
    sidecar_archive.chmod(0o600)

    shutil.copy2(config_path, destination / "instance.toml")
    (destination / "instance.toml").chmod(0o600)
    secret_source = Path(paths["secrets"])
    if secret_source.is_dir():
        shutil.copytree(
            secret_source,
            destination / "secrets",
            ignore=shutil.ignore_patterns("README.md", ".gitignore"),
        )
        for path in (destination / "secrets").rglob("*"):
            if path.is_file():
                path.chmod(0o600)
        (destination / "secrets").chmod(0o700)

    ddns_file = Path(paths["ddns_config"]) / ".ddns_go_config.yaml"
    if ddns_file.is_file():
        shutil.copy2(ddns_file, destination / "ddns-go.yaml")
        (destination / "ddns-go.yaml").chmod(0o600)

    files = [
        path
        for path in destination.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    ]
    manifest = {
        "created_at": stamp,
        "profile": renderer.table(config, "deployment")["profile"],
        "files": {
            str(path.relative_to(destination)): {
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        },
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest_path.chmod(0o600)
    print(f"Created consistent runtime backup: {destination}")
    removed = prune_backups(destination_root, keep_last)
    if removed:
        print(
            f"Pruned {len(removed)} old backup(s); "
            f"keeping the latest {keep_last} in {destination_root}"
        )
    return 0


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_status(
    url: str,
    host_header: str | None = None,
    resolve_address: str | None = None,
) -> tuple[int, str]:
    if resolve_address:
        parsed = urllib.parse.urlsplit(url)
        if not parsed.hostname:
            raise ValueError(f"URL has no hostname: {url}")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        argv = [
            "curl",
            "--silent",
            "--show-error",
            "--insecure",
            "--output",
            "/dev/null",
            "--write-out",
            "%{http_code}\n%{redirect_url}",
            "--max-time",
            "15",
            "--resolve",
            f"{parsed.hostname}:{port}:{resolve_address}",
        ]
        if host_header:
            argv.extend(["--header", f"Host: {host_header}"])
        argv.append(url)
        result = subprocess.run(argv, check=True, text=True, capture_output=True)
        status_text, _, location = result.stdout.partition("\n")
        return int(status_text), location.strip()

    context = ssl._create_unverified_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context), NoRedirect()
    )
    headers = {"Host": host_header} if host_header else {}
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, response.headers.get("Location", "")
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Location", "")


def smoke(
    config: dict[str, Any],
    base_url: str,
    host_header: str | None = None,
    resolve_address: str | None = None,
    wait_seconds: int = 0,
) -> int:
    base = base_url.rstrip("/")
    features = renderer.table(config, "features")
    checks = [("/", {200, 302, 401})]
    if features["authelia"]:
        checks.append(("/authelia/", {200, 302}))
    else:
        checks.extend(
            [
                ("/?json", {200}),
                ("/tag-api/tags", {200}),
            ]
        )
    deadline = time.monotonic() + wait_seconds
    last_error: Exception | None = None
    last_results: list[tuple[str, int, str, set[int]]] = []
    while True:
        current_results: list[tuple[str, int, str, set[int]]] = []
        try:
            for path, expected in checks:
                status, location = request_status(
                    base + path, host_header, resolve_address
                )
                current_results.append((path, status, location, expected))
            last_results = current_results
            if all(status in expected for _, status, _, expected in current_results):
                for path, status, location, _ in current_results:
                    suffix = f" -> {location}" if location else ""
                    print(f"{status} {path}{suffix}")
                print("Unauthenticated smoke test passed.")
                return 0
        except (
            OSError,
            ValueError,
            subprocess.CalledProcessError,
            urllib.error.URLError,
        ) as error:
            last_error = error

        if time.monotonic() >= deadline:
            break
        time.sleep(1)

    for path, status, location, _ in last_results:
        suffix = f" -> {location}" if location else ""
        print(f"{status} {path}{suffix}")
    if last_error is not None:
        print(f"Smoke test failed after waiting {wait_seconds}s: {last_error}")
    else:
        print(f"Smoke test failed after waiting {wait_seconds}s.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("render")
    subparsers.add_parser("preflight")
    subparsers.add_parser("config")
    subparsers.add_parser("ps")
    logs_parser = subparsers.add_parser("logs")
    logs_parser.add_argument("--follow", action="store_true")
    up_parser = subparsers.add_parser("up")
    up_parser.add_argument(
        "--confirm",
        "--confirm-cutover",
        dest="confirm",
        action="store_true",
        help="confirm starting services on production ports",
    )
    recreate_parser = subparsers.add_parser("recreate")
    recreate_parser.add_argument(
        "service",
        choices=(
            "caddy",
            "dufs",
            "tag-server",
            "tag-server-readonly",
            "readonly-gateway",
            "authelia",
            "dufs-readonly",
            "ddns-go",
        ),
    )
    subparsers.add_parser("down")
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument(
        "--destination",
        type=Path,
        help="backup root (default: $XDG_STATE_HOME/dufs-plus/backups/<instance>)",
    )
    backup_parser.add_argument(
        "--keep-last",
        type=int,
        default=DEFAULT_BACKUP_KEEP,
        help="retain this many completed backups; 0 keeps all",
    )
    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--base-url", required=True)
    smoke_parser.add_argument("--host-header")
    smoke_parser.add_argument("--resolve-address")
    smoke_parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()

    try:
        if args.command == "render":
            ensure_rendered(args.config, args.output)
            return 0
        if args.command == "preflight":
            return preflight(args.config, args.output)
        if args.command == "backup":
            return backup(
                args.config,
                args.output,
                args.destination,
                args.keep_last,
            )
        if args.command == "smoke":
            config = load_config(args.config)
            return smoke(
                config,
                args.base_url,
                args.host_header,
                args.resolve_address,
                args.wait_seconds,
            )

        config = ensure_rendered(args.config, args.output)
        if args.command == "config":
            action = ["config"]
        elif args.command == "ps":
            action = ["ps"]
        elif args.command == "logs":
            action = ["logs"] + (["--follow"] if args.follow else [])
        elif args.command == "down":
            action = ["down"]
        elif args.command == "up":
            if not args.confirm:
                print(
                    "refusing to start production ports without --confirm",
                    file=sys.stderr,
                )
                return 2
            if preflight(args.config, args.output) != 0:
                return 1
            action = ["up", "-d"]
            # podman-compose 1.6 may remove dependency containers before
            # recreating their dependants and then wait forever. Docker
            # Compose has reliable orphan cleanup.
            if renderer.table(config, "runtime")["engine"] == "docker":
                action.append("--remove-orphans")
        elif args.command == "recreate":
            action = [
                "up",
                "-d",
                "--no-deps",
                "--force-recreate",
                args.service,
            ]
        else:
            raise RuntimeError(f"unsupported command: {args.command}")
        return subprocess.run(compose_argv(args.output, action), check=False).returncode
    except (renderer.ConfigError, OSError, tomllib.TOMLDecodeError) as error:
        print(f"{args.command} error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
