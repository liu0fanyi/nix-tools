#!/usr/bin/env python3
"""Restore a verified business snapshot into a new private directory, never live paths."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

spec = importlib.util.spec_from_file_location("backup", Path(__file__).with_name("nuc-backup.py"))
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)

DATABASES = [
    "home/liou/dufs/.dufs_plus_state/tag_all.db",
    "home/liou/dufs-lan/.dufs_plus_state/tag_all.db",
    "home/liou/.local/share/authelia/db.sqlite3",
]
REQUIRED_FILES = [
    "home/liou/.config/dufs-plus/secrets/tag-server.env",
    "home/liou/.config/dufs-plus/secrets/authelia_users_database.yml",
    "home/liou/.config/dufs-plus/secrets/authelia_jwt_secret",
    "home/liou/.config/dufs-plus/secrets/authelia_session_secret",
    "home/liou/.config/dufs-plus/secrets/authelia_storage_key",
    "media/liou/project/me/nix-tools/deploy/instances/home.toml",
    "home/liou/.local/state/syncthing/config.xml",
    "home/liou/.local/state/syncthing/cert.pem",
    "home/liou/.local/state/syncthing/key.pem",
]

def inside(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise RuntimeError("required restored path escapes rehearsal directory: " + relative)
    return path

def validate_manifest(manifest):
    if manifest.get("host") != "nuc" or manifest.get("backup_uuid") != backup.UUID or manifest.get("scope") != "business":
        raise RuntimeError("not the expected NUC business snapshot")
    for key in ["copy_complete", "checksum_verified", "quiesced"]:
        if manifest.get(key) is not True:
            raise RuntimeError("snapshot has not passed " + key)

def check_database(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("missing/empty database")
    # Writable connection ONLY to the independent restored copy, so any WAL recovery
    # cannot modify the backup or the production database. No hard links are used.
    with sqlite3.connect(path.as_uri() + "?mode=rw", uri=True) as connection:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
        if rows != [("ok",)]:
            raise RuntimeError("SQLite integrity check failed")
        tables = connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        if not tables:
            raise RuntimeError("database contains no tables")
    return {"integrity": "ok", "tables": tables}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"\d{8}T\d{6}\.\d{6}Z", args.snapshot):
        parser.error("snapshot must be a timestamp, not a path")
    backup.checks("business")  # Root, host, UUID and private backup directory guards.
    snapshot = backup.BASE / args.snapshot
    backup.safe_directory(snapshot)
    manifest_path = inside(snapshot, "manifest.json")
    manifest = json.loads(manifest_path.read_text())
    validate_manifest(manifest)
    source = snapshot / "rootfs"
    backup.safe_directory(source)
    if not source.is_dir():
        raise RuntimeError("snapshot rootfs missing")
    os.umask(0o077)
    parent = backup.BASE / "restore-checks"
    backup.safe_directory(parent)
    parent.mkdir(mode=0o700, exist_ok=True)
    destination = parent / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination.mkdir(mode=0o700)
    restored = destination / "rootfs"
    restored.mkdir(mode=0o700)
    report = {"snapshot": args.snapshot, "copy_verified": False, "databases": {},
              "rehearsal_passed": False, "install_ready": False}
    def save():
        (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    print("Rehearsal: " + str(destination), flush=True)
    try:
        rsync = ["rsync", "-aHAXx", "--numeric-ids"]
        subprocess.run([*rsync, "--info=progress2", str(source) + "/", str(restored) + "/"], check=True)
        with (destination / "verify.log").open("w") as log:
            subprocess.run([*rsync, "--checksum", "--dry-run", "--itemize-changes",
                            str(source) + "/", str(restored) + "/"], check=True, stdout=log, stderr=subprocess.STDOUT)
        if (destination / "verify.log").stat().st_size:
            raise RuntimeError("restored files/permissions differ; inspect private verify.log")
        report["copy_verified"] = True
        for relative in REQUIRED_FILES:
            path = inside(restored, relative)
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError("required configuration/credential missing: " + relative)
        for relative in DATABASES:
            report["databases"][relative] = check_database(inside(restored, relative))
        report["rehearsal_passed"] = True
        save()
    except Exception:
        save()
        raise
    print(json.dumps(report, indent=2))
    print("File/metadata/SQLite rehearsal passed; no application startup tested, no installation authorized.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        print("STOP: " + str(exc), file=sys.stderr)
        sys.exit(1)
