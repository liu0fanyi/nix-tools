#!/usr/bin/env bash
set -euo pipefail

# Keep the two dufs-plus media roots stable even when their exFAT volume labels
# change. This script only updates /etc/fstab; it deliberately never unmounts
# or remounts a live disk, because doing so could interrupt file operations.

readonly marker_begin="# BEGIN dufs-plus stable media mounts"
readonly marker_end="# END dufs-plus stable media mounts"
readonly art_uuid="5F82-B190"
readonly passport_uuid="AC2F-A91E"
usage() {
  cat <<'EOF'
Usage:
  install-dufs-media-mounts.sh --dry-run [USER]
  sudo install-dufs-media-mounts.sh [USER]

USER defaults to SUDO_USER, or liou when SUDO_USER is unavailable.
The install command updates /etc/fstab atomically but does not remount disks.
Finish or stop active file jobs, then reboot to activate the stable mounts.
EOF
}

mode="install"
if [[ "${1:-}" == "--dry-run" ]]; then
  mode="dry-run"
  shift
elif [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

mount_user="${1:-${SUDO_USER:-liou}}"
if ! getent passwd "$mount_user" >/dev/null; then
  echo "Unknown mount owner: $mount_user" >&2
  exit 2
fi
mount_uid="$(id -u "$mount_user")"
mount_gid="$(id -g "$mount_user")"

verify_volume() {
  local name="$1"
  local uuid="$2"
  local device
  device="$(blkid -U "$uuid" 2>/dev/null || true)"
  if [[ -z "$device" ]]; then
    echo "$name volume UUID=$uuid is not currently available" >&2
    exit 3
  fi
  echo "$name: $device (UUID=$uuid)" >&2
}

verify_volume "Art" "$art_uuid"
verify_volume "My Passport" "$passport_uuid"

mount_options="rw,nofail,x-systemd.automount,x-systemd.device-timeout=15s,uid=${mount_uid},gid=${mount_gid},fmask=0022,dmask=0022,iocharset=utf8"
fstab_block="$marker_begin
UUID=$art_uuid /media/liou/Art exfat $mount_options 0 0
UUID=$passport_uuid /media/liou/My\\040Passport exfat $mount_options 0 0
$marker_end"

if [[ "$mode" == "dry-run" ]]; then
  printf '%s\n' "$fstab_block"
  exit 0
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "Install mode must run as root. Use: sudo $0 $mount_user" >&2
  exit 4
fi

backup="/etc/fstab.dufs-plus.$(date +%Y%m%d-%H%M%S).bak"
cp --preserve=mode,ownership,timestamps /etc/fstab "$backup"
temporary="$(mktemp /etc/fstab.dufs-plus.XXXXXX)"
cleanup() {
  rm -f "$temporary"
}
trap cleanup EXIT

awk -v begin="$marker_begin" -v end="$marker_end" '
  $0 == begin { skipping = 1; next }
  $0 == end { skipping = 0; next }
  !skipping { print }
' /etc/fstab >"$temporary"
printf '\n%s\n' "$fstab_block" >>"$temporary"
chmod --reference=/etc/fstab "$temporary"
chown --reference=/etc/fstab "$temporary"
mv "$temporary" /etc/fstab
trap - EXIT

systemctl daemon-reload
echo "Installed stable dufs-plus media mounts. Backup: $backup"
echo "No live mount was changed. Finish active jobs and reboot to activate them."
