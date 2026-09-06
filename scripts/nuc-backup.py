#!/usr/bin/env python3
"""Run ON NUC as root. Default is a non-mutating backup check."""
import argparse
import datetime
import json
import os
import re
from pathlib import Path
import socket
import stat
import subprocess
import sys

MOUNT = Path("/media/liou/project")
BASE = MOUNT / ".nuc-migration-backups"
UUID = "8bce6197-7281-40a0-84ec-e31c3d313877"
SOURCES = ["/home/liou", "/etc", "/root", "/srv", "/opt", "/var/spool/cron", "/var/lib/NetworkManager", "/var/lib/bluetooth", "/var/lib/systemd/linger", "/var/lib/containers"]
BUSINESS_REQUIRED = [
    "/home/liou/dufs", "/home/liou/dufs-lan",
    "/home/liou/.config/dufs-plus", "/home/liou/.config/ddns-go",
    "/home/liou/.local/share/authelia", "/home/liou/.local/share/caddy",
    "/home/liou/.local/share/caddy-container-config",
    "/home/liou/.local/share/dufs-plus/runtime",
    "/media/liou/project/me/nix-tools/deploy", "/home/liou/.ssh",
]
BUSINESS_OPTIONAL = [
    "/etc/ssh", "/etc/subuid", "/etc/subgid",
    "/home/liou/.config/systemd/user",
    *["/home/liou/.local/state/syncthing/" + name for name in
      ["config.xml", "cert.pem", "key.pem", "https-cert.pem", "https-key.pem"]],
]
# Keep container storage as insurance; restore images using PC release tools.
LEGACY_EXCLUDES = ["/home/liou/.cache/***", "/root/.cache/***"]
# User explicitly retired NUC Codex state; retain it only in the old seed snapshot.
EXCLUDES = [*LEGACY_EXCLUDES, "/home/liou/.codex/***"]

def run(args, **kw):
    return subprocess.run(args, text=True, check=True, **kw)

def capture(args):
    return run(args, capture_output=True).stdout.strip()

def safe_directory(path):
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise RuntimeError(f"symlink in backup path: {parent}")
    if path.exists():
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
            raise RuntimeError(f"backup directory must be root-owned mode 0700: {path}")

def select_sources(scope):
    if scope == "full":
        return [p for p in SOURCES if Path(p).exists()]
    for p in BUSINESS_REQUIRED:
        if not Path(p).is_dir() or Path(p).is_symlink():
            raise RuntimeError(f"required business source missing or symlinked: {p}")
    for root in ["/home/liou/dufs", "/home/liou/dufs-lan"]:
        if not (Path(root) / ".dufs_plus_state/tag_all.db").is_file():
            raise RuntimeError(f"required tag-all database missing: {root}")
    return BUSINESS_REQUIRED + [p for p in BUSINESS_OPTIONAL if Path(p).exists()]

def checks(scope="business"):
    if os.geteuid() != 0:
        raise RuntimeError("root required: use sudo python3 scripts/nuc-backup.py --check on NUC")
    if socket.gethostname() != "nuc" or Path("/sys/class/dmi/id/product_name").read_text().strip() != "NUC8i5BEH":
        raise RuntimeError("not the inventoried NUC")
    list(MOUNT.iterdir())  # Activate automount before checking actual filesystem.
    # systemd automount may report both autofs and ext4 for the same target.
    actual = capture(["findmnt", "-rn", "-T", str(MOUNT), "-t", "ext4", "-o", "UUID,FSTYPE"]).split()
    if actual != [UUID, "ext4"]:
        raise RuntimeError("backup disk UUID/filesystem mismatch; no fallback to system disk")
    safe_directory(BASE)
    if MOUNT.stat().st_dev == Path("/home/liou").stat().st_dev:
        raise RuntimeError("backup destination is on the system filesystem")
    for p in ["/home/liou/dufs", "/home/liou/dufs-lan"]:
        if not Path(p).is_dir() or Path(p).is_symlink():
            raise RuntimeError(f"expected business directory missing or changed: {p}")
    return select_sources(scope)

def user_cmd(*args):
    return ["runuser", "-u", "liou", "--", "env", "XDG_RUNTIME_DIR=/run/user/1000", "PATH=/home/liou/.nix-profile/bin:/usr/bin:/bin", *args]

def root_podman():
    # sudo strips the user Nix profile from PATH. Resolve the verified profile
    # entry to immutable root-owned store content instead of widening root PATH.
    binary = Path("/home/liou/.nix-profile/bin/podman").resolve(strict=True)
    if not binary.is_relative_to("/nix/store"):
        raise RuntimeError("Podman profile must resolve into /nix/store")
    for path in [binary, *binary.parents]:
        info = path.stat()
        # Multi-user Nix store is normally root:nixbld 1775; sticky bit protects
        # the root-owned store entry from replacement by group members.
        protected_store = path == Path("/nix/store") and info.st_mode & stat.S_ISVTX
        if info.st_uid != 0 or (info.st_mode & 0o022 and not protected_store):
            raise RuntimeError(f"unsafe root Podman path: {path}")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError("Podman store binary is not executable")
    return str(binary)

def require_quiet(scope="business"):
    # Never stop production implicitly. Operator arranges maintenance first.
    for unit in ["dufs-plus-compose", "ttyd-compose", "syncthing", "clipboard-sync"]:
        p = subprocess.run(user_cmd("systemctl", "--user", "is-active", unit), text=True, capture_output=True)
        if p.stdout.strip() not in {"inactive", "failed", "unknown"}:
            raise RuntimeError(f"stop {unit} before final backup (cannot verify stopped state)")
    if capture(user_cmd("podman", "ps", "-q")):
        raise RuntimeError("user containers still running; final backup requires all stopped")
    p = subprocess.run([root_podman(), "ps", "-q"], text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("cannot verify root container state: " + p.stderr.strip())
    if p.stdout.strip():
        raise RuntimeError("root containers still running")
    if scope == "full":
        processes = capture(["ps", "-u", "liou", "-o", "comm="]).splitlines()
        if any(x.strip() in {".fcitx5-wrapped", "fcitx5", "cosmic-session"} for x in processes):
            raise RuntimeError("desktop writers still running; close them before final backup")

def previous_root(name, sources):
    if not re.fullmatch(r"\d{8}T\d{6}\.\d{6}Z", name):
        raise RuntimeError("previous must be a snapshot timestamp, not a path")
    snapshot = BASE / name
    safe_directory(snapshot)
    safe_directory(snapshot / "rootfs")
    manifest_path = snapshot / "manifest.json"
    if manifest_path.is_symlink():
        raise RuntimeError("previous manifest must not be a symlink")
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get("host") != "nuc" or manifest.get("backup_uuid") != UUID
            or not manifest.get("copy_complete") or manifest.get("sources") != sources
            or manifest.get("excludes") not in [LEGACY_EXCLUDES, EXCLUDES]):
        raise RuntimeError("previous snapshot identity/scope/copy status mismatch")
    root = snapshot / "rootfs"
    if not root.is_dir() or root.stat().st_dev != BASE.stat().st_dev:
        raise RuntimeError("previous snapshot must be on the same backup filesystem")
    return root

def classify_verification(text):
    # Ignore only rsync's explicit notices for the intentionally omitted special files.
    # All itemized changes AND unknown diagnostics remain failures.
    skipped, differences = [], []
    for line in text.splitlines():
        if line.startswith('skipping non-regular file "') and line.endswith('"'):
            skipped.append(line)
        elif line.strip():
            differences.append(line)
    return skipped, differences

def copy_args(sources, destination, verify=False, previous=None):
    args = ["rsync", "-aHAXx", "--numeric-ids", "--no-devices", "--no-specials", "--relative"]
    if verify:
        args += ["--checksum", "--dry-run", "--itemize-changes"]
    else:
        args += ["--info=progress2", "--stats"]
        if previous is not None:
            # Fresh destination only: never use --inplace, --append or --delete.
            # Verify unchanged contents before sharing their inodes with the old snapshot.
            args += ["--checksum", "--link-dest=" + str(previous)]
    for pattern in EXCLUDES:
        args += ["--exclude", pattern]
    return args + sources + [str(destination) + "/"]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--seed", action="store_true", help="live copy; NEVER install-ready")
    mode.add_argument("--final", action="store_true", help="manually quiesced services required")
    parser.add_argument("--previous", help="prior completed snapshot timestamp; --final only")
    parser.add_argument("--scope", choices=["business", "full"], default="business",
                        help="business is the default; full explicitly includes the old whole-home scope")
    args = parser.parse_args()
    if args.scope == "business" and args.previous:
        parser.error("business scope uses a fresh small copy; omit --previous")
    sources = checks(args.scope)
    if args.previous and not args.final:
        parser.error("--previous requires --final")
    previous = previous_root(args.previous, sources) if args.previous else None
    sizes = capture(["du", "-sx", "--block-size=1", *sources])
    needed = sum(int(line.split()[0]) for line in sizes.splitlines())
    fs = os.statvfs(MOUNT)
    available = fs.f_bavail * fs.f_frsize
    print(json.dumps({"scope": args.scope, "sources": sources, "excludes": EXCLUDES, "destination": str(BASE), "upper_estimate_bytes": needed, "available_bytes": available}, indent=2))
    if available < needed * 1.2:
        raise RuntimeError("insufficient backup headroom")
    if not (args.seed or args.final):
        return 0
    if args.final:
        require_quiet(args.scope)
    os.umask(0o077)
    BASE.mkdir(mode=0o700, exist_ok=True)
    safe_directory(BASE)
    name = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = BASE / name
    destination.mkdir(mode=0o700)  # Never reuse/delete an earlier snapshot.
    rootfs = destination / "rootfs"
    rootfs.mkdir(mode=0o700)
    manifest = {"schema": 1, "host": "nuc", "created": name, "backup_uuid": UUID,
                "sources": sources, "excludes": EXCLUDES, "copy_complete": False,
                "quiesced": bool(args.final), "checksum_verified": False,
                "restore_rehearsal": False, "install_ready": False}
    manifest["previous"] = args.previous
    manifest["scope"] = args.scope
    manifest["phase"] = "copy"
    def save():
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    save()
    print(f"Backup: {destination}\nPhase: copy (progress below; checksum scan may pause counters)", flush=True)
    with (destination / "copy.log").open("w") as log:
        run(copy_args(sources, rootfs, previous=previous), stderr=log)
    manifest["copy_complete"] = True
    manifest["phase"] = "verify"
    save()
    print("Phase: full checksum verification; read-only and potentially slow", flush=True)
    with (destination / "verify.log").open("w") as log:
        run(copy_args(sources, rootfs, verify=True), stdout=log, stderr=subprocess.STDOUT)
    skipped, differences = classify_verification((destination / "verify.log").read_text())
    unchanged = not differences
    manifest["skipped_special_notices"] = len(skipped)
    manifest["verification_differences"] = len(differences)
    manifest["checksum_verified"] = unchanged
    manifest["phase"] = "verified" if unchanged else "differences"
    save()
    if args.final:
        require_quiet(args.scope)
        if not unchanged:
            save()
            raise RuntimeError("files changed during final backup; not a final consistent snapshot")
    save()
    print(f"Backup: {destination}")
    print("NOT install-ready: isolated restore rehearsal and migration approval still required.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        sys.exit(1)
