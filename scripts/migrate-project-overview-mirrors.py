#!/usr/bin/env python3
"""One-time, manifest-bound cleanup of superseded project mirrors; no service changes."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tarfile
from zoneinfo import ZoneInfo

TODOS = Path("/home/liou/dufs-lan/todos")
BACKUPS = Path("/home/liou/.local/share/project-progress-backups")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def snapshot(root, names):
    result = {}
    for name in names:
        if Path(name).name != name or name in {".", "..", "projects"}:
            raise ValueError("Exact legacy top-level entries required")
        p = root / name
        if not p.exists() and not p.is_symlink():
            continue
        entries = [p, *sorted(p.rglob("*"))] if p.is_dir() and not p.is_symlink() else [p]
        for entry in entries:
            rel = entry.relative_to(root).as_posix()
            mode = entry.lstat().st_mode
            if stat.S_ISLNK(mode):
                result[rel] = {"kind": "symlink", "target": os.readlink(entry)}
            elif stat.S_ISDIR(mode):
                result[rel] = {"kind": "directory"}
            elif stat.S_ISREG(mode):
                result[rel] = {"kind": "file", "sha256": digest(entry), "size": entry.stat().st_size}
            else:
                raise ValueError("Unsupported non-document entry: " + rel)
    return result


def verify_archive(archive, records):
    found = {}
    with tarfile.open(archive, "r:gz") as tar:
        for item in tar:
            name = item.name.rstrip("/")
            if item.isfile() or item.islnk():
                stream = tar.extractfile(item)
                sha, size = hashlib.sha256(), 0
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    sha.update(block); size += len(block)
                found[name] = {"kind": "file", "sha256": sha.hexdigest(), "size": size}
            elif item.isdir():
                found[name] = {"kind": "directory"}
            elif item.issym():
                found[name] = {"kind": "symlink", "target": item.linkname}
            else:
                raise ValueError("Unexpected archive type: " + name)
    if found != records:
        raise ValueError("Backup archive content mismatch")


def backup(root, names, base, expected_projects):
    # Only explicitly enumerated entries; personal files and projects never enter cleanup.
    if not names or len(names) != len(set(names)):
        raise ValueError("Unique nonempty legacy allowlist required")
    before = snapshot(root, names)
    existing = sorted(name for name in names if (root/name).exists() or (root/name).is_symlink())
    protected = sorted(p.name for p in root.iterdir() if p.name not in names and p.name != "projects")
    protected_before = snapshot(root, protected)
    project_paths = root / "projects"
    for name, sha in expected_projects.items():
        p = project_paths / name
        if Path(name).name != name or p.is_symlink() or not p.is_file() or digest(p) != sha:
            raise ValueError("New project overview is missing or differs: " + name)
    folder = base / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S")
    folder.mkdir(mode=0o700, parents=True, exist_ok=False)
    folder.chmod(0o700)
    archive = folder / "legacy-projects.tar.gz"
    with tarfile.open(archive, "w:gz", dereference=False) as tar:
        for name in existing:
            tar.add(root/name, arcname=name)
    archive.chmod(0o600)
    verify_archive(archive, before)
    if snapshot(root, names) != before or snapshot(root, protected) != protected_before:
        raise ValueError("Source changed during backup; do not clean")
    manifest = {"root": str(root), "names": existing, "legacy": before,
                "protected_names": protected, "protected": protected_before,
                "projects": expected_projects, "archive_sha256": digest(archive)}
    (folder/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    (folder/"manifest.json").chmod(0o600)
    return folder


def cleanup(root, folder):
    manifest = json.loads((folder/"manifest.json").read_text())
    archive = folder/"legacy-projects.tar.gz"
    if manifest["root"] != str(root) or digest(archive) != manifest["archive_sha256"]:
        raise ValueError("Unexpected backup root or changed archive")
    verify_archive(archive, manifest["legacy"])
    if snapshot(root, manifest["names"]) != manifest["legacy"]:
        raise ValueError("Legacy files changed since backup; refuse cleanup")
    if snapshot(root, manifest["protected_names"]) != manifest["protected"]:
        raise ValueError("Protected files changed since backup; review before cleanup")
    for name, sha in manifest["projects"].items():
        if digest(root/"projects"/name) != sha:
            raise ValueError("Published overview changed before cleanup")
    for name in manifest["names"]:
        p = root/name
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
    if snapshot(root, manifest["names"]):
        raise ValueError("Legacy entries remain")
    if snapshot(root, manifest["protected_names"]) != manifest["protected"]:
        raise ValueError("Protected file verification failed")
    return {"removed_legacy_entries": len(manifest["names"]),
            "backed_up_files": sum(v["kind"]=="file" for v in manifest["legacy"].values()),
            "protected_entries_unchanged": len(manifest["protected_names"]),
            "new_markdown_files_verified": len(manifest["projects"]),
            "backup": str(folder), "backup_sha256": manifest["archive_sha256"],
            "personal_files_unchanged": True, "services_changed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", type=Path)
    group.add_argument("--backup", type=Path, help="JSON with exact legacy names and new overview hashes")
    group.add_argument("--cleanup", type=Path, help="Previously verified backup folder")
    args = parser.parse_args()
    if args.plan or args.backup:
        plan = json.loads((args.plan or args.backup).read_text())
        if args.plan:
            print(json.dumps({"legacy_entries": plan["names"], "new_markdown_files": len(plan["projects"]), "deletion": False}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"backup": str(backup(TODOS, plan["names"], BACKUPS, plan["projects"]))}))
    else:
        folder = args.cleanup.resolve()
        if folder.parent != BACKUPS or folder.is_symlink():
            raise ValueError("A fixed private backup folder is required")
        print(json.dumps(cleanup(TODOS, folder), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
