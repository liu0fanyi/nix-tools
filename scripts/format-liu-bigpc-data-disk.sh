#!/usr/bin/env bash
set -euo pipefail

# Destructive, one-host migration helper. Never replace this stable by-id path
# with /dev/sdX: enumeration changes when disks are added or removed.
readonly expected_serial="XQ--CC1U4731017"
readonly expected_model="WDC WD5003ABYZ-011FA0"
readonly disk_by_id="/dev/disk/by-id/ata-WDC_WD5003ABYZ-011FA0_XQ--CC1U4731017"
readonly partition_by_id="${disk_by_id}-part1"
readonly confirmation="FORMAT ${expected_serial}"

if (( EUID != 0 )); then
  echo "Run this script with sudo." >&2
  exit 1
fi

for command in blockdev findmnt lsblk mkfs.ext4 mountpoint readlink; do
  command -v "$command" >/dev/null || {
    echo "Required command is missing: $command" >&2
    exit 1
  }
done

[[ -b "$disk_by_id" ]] || {
  echo "Expected data disk is missing: $disk_by_id" >&2
  exit 1
}
[[ -b "$partition_by_id" ]] || {
  echo "Expected data partition is missing: $partition_by_id" >&2
  exit 1
}

disk="$(readlink -f "$disk_by_id")"
partition="$(readlink -f "$partition_by_id")"
model="$(lsblk -dn -o MODEL "$disk" | xargs)"
serial="$(lsblk -dn -o SERIAL "$disk" | xargs)"
partition_number="$(lsblk -dn -o PARTN "$partition" | xargs)"
partition_size="$(blockdev --getsize64 "$partition")"

[[ "$model" == "$expected_model" ]] || {
  echo "Model mismatch: expected '$expected_model', got '$model'." >&2
  exit 1
}
[[ "$serial" == "$expected_serial" ]] || {
  echo "Serial mismatch: expected '$expected_serial', got '$serial'." >&2
  exit 1
}
[[ "$partition_number" == "1" ]] || {
  echo "Partition mismatch: expected part 1, got '$partition_number'." >&2
  exit 1
}
(( partition_size >= 490000000000 && partition_size <= 510000000000 )) || {
  echo "Partition size is outside the expected 490-510 GB range: $partition_size" >&2
  exit 1
}

mapfile -t mountpoints < <(findmnt -rn -S "$partition" -o TARGET || true)
for target in "${mountpoints[@]}"; do
  [[ "$target" == "/mnt/disk500" ]] || {
    echo "Refusing to format: unexpected mount point $target" >&2
    exit 1
  }
done

echo "WARNING: this permanently erases the filesystem on:"
echo "  disk:      $disk"
echo "  partition: $partition"
echo "  model:     $model"
echo "  serial:    $serial"
echo "  size:      $partition_size bytes"
echo
printf "Type '%s' to continue: " "$confirmation"
IFS= read -r answer
[[ "$answer" == "$confirmation" ]] || {
  echo "Confirmation did not match; nothing was changed."
  exit 1
}

for target in "${mountpoints[@]}"; do
  umount "$target"
done

mkfs.ext4 -F -L data "$partition_by_id"

# Initialise ownership for the uid/gid used by both old liu and new liou.
install -d -m 0755 /mnt/disk500
mount "$partition_by_id" /mnt/disk500
chown 1000:100 /mnt/disk500
chmod 0755 /mnt/disk500
sync
umount /mnt/disk500

echo "Formatted successfully. Persistent NixOS mount point: /data"
lsblk -f "$disk"
