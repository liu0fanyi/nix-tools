#!/usr/bin/env python3
"""Device-bound read-only install checks. Never infer a destructive target."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ANYWHERE = "github:nix-community/nixos-anywhere/6b77f26ec4538ced04bf1d02f374b0ec02e9c27e"
PROBE = r'''
import json, os, pathlib, subprocess
def run(args):
    p = subprocess.run(args, text=True, capture_output=True)
    return p.stdout.strip() if p.returncode == 0 else ""
def read(p):
    try: return pathlib.Path(p).read_text().strip()
    except OSError: return ""
wired = []
for p in pathlib.Path("/sys/class/net").iterdir():
    if (p / "device").exists() and not (p / "wireless").exists():
        wired.append({"name": p.name, "carrier": read(p / "carrier"),
                      "ipv4": run(["ip", "-4", "-o", "addr", "show", "dev", p.name, "scope", "global"])})
disk = __DISK__
print(json.dumps({
    "hostname": run(["hostname"]), "arch": run(["uname", "-m"]),
    "product": read("/sys/class/dmi/id/product_name"),
    "disk_real": os.path.realpath(disk) if disk else "",
    "disk_bytes": run(["lsblk", "-bdno", "SIZE", disk]) if disk else "",
    "disks": run(["lsblk", "-bdn", "-o", "NAME,TYPE,SIZE,MODEL"]),
    "wired": wired, "ssh_connection": os.environ.get("SSH_CONNECTION", ""),
    "uefi": pathlib.Path("/sys/firmware/efi").exists(),
    "root": os.geteuid() == 0 or subprocess.run(["sudo", "-n", "true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
    "efi_writable": os.access("/sys/firmware/efi/efivars", os.W_OK) or subprocess.run(["sudo", "-n", "test", "-w", "/sys/firmware/efi/efivars"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
    "kexec_disabled": read("/proc/sys/kernel/kexec_load_disabled"),
    "lockdown": read("/sys/kernel/security/lockdown"),
    "meminfo": read("/proc/meminfo").splitlines()[0],
}, ensure_ascii=False))
'''

def assess(profile, report):
    errors = []
    def need(ok, message):
        if not ok: errors.append(message)
    need(report["hostname"] == profile["hostname"], "target hostname does not match selected device")
    need(report["arch"] == "x86_64", "target architecture is not x86_64")
    need(profile.get("disk"), "device has no approved stable disk identity")
    if profile.get("disk"):
        need(report["product"] == profile["product"], "hardware product mismatch")
        need(report["disk_bytes"] == str(profile["disk_bytes"]), "stable disk ID missing or capacity mismatch")
    need(report["uefi"] and report["efi_writable"], "UEFI writable check missing (requires root privileges)")
    need(report["root"], "root SSH or temporary passwordless sudo required")
    need(report["kexec_disabled"] == "0", "kexec disabled or status unavailable")
    need("[none]" in report["lockdown"] or not report["lockdown"], "kernel lockdown enabled")
    connected = [x for x in report["wired"] if x["carrier"] == "1" and x["ipv4"]]
    need(connected, "wired IPv4 connection required; Wi-Fi is not sufficient")
    connection = report["ssh_connection"].split()
    addresses = [part.split("/")[0] for x in connected for part in x["ipv4"].split() if "/" in part]
    need(len(connection) == 4 and connection[2] in addresses, "SSH must use the wired interface address")
    # Preparations must not become a hidden installation authorization.
    need(profile.get("installation_enabled", False), profile["reason"])
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=["nuc", "homebox", "liu-bigpc"])
    parser.add_argument("--target", help="explicit SSH target, still verified against selected device")
    parser.add_argument("--check", action="store_true", help="read-only preflight (default)")
    parser.add_argument("--plan", action="store_true", help="print candidate command, never execute")
    args = parser.parse_args()
    profile = json.loads((ROOT / "nixos/hosts/install-targets.json").read_text())[args.host]
    target = args.target or profile["ssh"]
    if target.startswith("-") or any(c.isspace() for c in target):
        parser.error("invalid SSH target")
    payload = PROBE.replace("__DISK__", repr(profile.get("disk", "")))
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=yes", target, "python3 -"], input=payload, text=True, capture_output=True)
    if p.returncode:
        print(p.stderr.strip(), file=sys.stderr)
        return 2
    report = json.loads(p.stdout)
    errors = assess(profile, report)
    print(json.dumps({"host": args.host, "report": report, "blockers": errors}, ensure_ascii=False, indent=2))
    if args.plan and "flake" in profile:
        print("CANDIDATE ONLY — NOT AUTHORIZED; uses the reviewed per-host hardware report without overwriting it:")
        print(shlex.join(["nix", "run", ANYWHERE, "--", "--no-substitute-on-destination", "--flake", f"path:{ROOT}#{profile['flake']}", "--target-host", target]))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
