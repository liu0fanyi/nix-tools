#!/usr/bin/env bash
set -euo pipefail

# Destructively repurpose only the retired WDC 120 GB NixOS SSD. Device names
# are deliberately ignored; identity is pinned to model, serial, size, and the
# old filesystem UUIDs.

readonly expected_model="WDC WDS120G1G0A-00SS50"
readonly expected_serial="171708A01FEB"
readonly expected_size=120034123776
readonly old_root_uuid="428f77c1-1fe1-47f4-8457-9944aec9e0e9"
readonly old_swap_uuid="ef3a79ac-83ff-4bbb-ba48-1b371418d9e3"
readonly old_esp_uuid="332B-F609"
readonly new_uuid="b2f8be6a-6739-46c7-8b85-070ac915c206"
readonly data_uuid="92af0d70-de16-4502-93fb-651392709a7b"
readonly mount_point="/data-ssd"
readonly confirmation="ERASE ${expected_serial} AS DATA-SSD"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

trim() {
  xargs <<<"$*"
}

single_value() {
  local column="$1"
  local device="$2"
  trim "$(lsblk -dn -o "$column" "$device")"
}

partition_by_number() {
  local disk="$1"
  local number="$2"
  lsblk -nrpo PATH,PARTN "$disk" | awk -v number="$number" '$2 == number { print $1 }'
}

if (( EUID != 0 )); then
  die "Run this script as root: sudo $0"
fi

required_commands=(
  awk blockdev findmnt lsblk mkfs.ext4 mount mountpoint partprobe readlink
  sfdisk sgdisk swapon sync udevadm umount xargs
)
missing_commands=()
for command in "${required_commands[@]}"; do
  command -v "$command" >/dev/null || missing_commands+=("$command")
done

if (( ${#missing_commands[@]} > 0 )); then
  if [[ "${NIXOS_SSD_TOOL_ENV-}" == 1 ]]; then
    die "Commands still missing inside the Nix tool environment: ${missing_commands[*]}"
  fi
  nix_command="$(command -v nix || true)"
  [[ -n "$nix_command" ]] || die "Commands are missing and nix is unavailable: ${missing_commands[*]}"
  script_path="$(readlink -f "$0")"
  echo "Preparing missing disk tools with Nix: ${missing_commands[*]}"
  exec env NIXOS_SSD_TOOL_ENV=1 "$nix_command" \
    --extra-experimental-features "nix-command flakes" \
    shell nixpkgs#gptfdisk nixpkgs#parted nixpkgs#e2fsprogs nixpkgs#util-linux \
    -c "$script_path" "$@"
fi

mapfile -t matches < <(lsblk -dpno PATH,TYPE | awk '$2 == "disk" { print $1 }' | while read -r candidate; do
  if [[ "$(single_value MODEL "$candidate")" == "$expected_model" && \
        "$(single_value SERIAL "$candidate")" == "$expected_serial" ]]; then
    printf '%s\n' "$candidate"
  fi
done)
(( ${#matches[@]} == 1 )) || die "Expected exactly one disk with serial $expected_serial; found ${#matches[@]}."

target="$(readlink -f "${matches[0]}")"
[[ "$(blockdev --getsize64 "$target")" == "$expected_size" ]] || die "Target disk size mismatch."

running_root="$(readlink -f "$(findmnt -nro SOURCE /)")"
running_parent="/dev/$(single_value PKNAME "$running_root")"
[[ "$target" != "$running_parent" ]] || die "Target unexpectedly contains the running root filesystem."

while read -r node; do
  findmnt -rn -S "$node" >/dev/null && die "Target node is mounted: $node"
  swapon --noheadings --raw --show=NAME 2>/dev/null | grep -Fxq "$node" && die "Target node is active swap: $node"
done < <(lsblk -nrpo PATH "$target")

partition_one="$(partition_by_number "$target" 1)"
partition_two="$(partition_by_number "$target" 2)"
partition_three="$(partition_by_number "$target" 3)"

if [[ -b "$partition_one" && "$(single_value UUID "$partition_one")" == "$new_uuid" ]]; then
  [[ -z "$partition_two" && -z "$partition_three" ]] || die "Unexpected extra partitions beside the planned data partition."
  echo "The exact data filesystem already exists; nothing will be reformatted."
elif [[ -b "$partition_one" && -b "$partition_two" && -b "$partition_three" ]]; then
  [[ "$(single_value UUID "$partition_one")" == "$old_root_uuid" ]] || die "Old root UUID mismatch."
  [[ "$(single_value UUID "$partition_two")" == "$old_swap_uuid" ]] || die "Old swap UUID mismatch."
  [[ "$(single_value UUID "$partition_three")" == "$old_esp_uuid" ]] || die "Old ESP UUID mismatch."

  backup_dir="/data/migration-backups/retired-wdc-ssd-$(date -u +%Y%m%dT%H%M%SZ)"
  [[ "$(findmnt -nro UUID /data)" == "$data_uuid" ]] || die "/data backup disk is not mounted with its expected UUID."
  mkdir -p "$backup_dir"
  sgdisk --backup="$backup_dir/partition-table.gpt" "$target"
  sfdisk --dump "$target" >"$backup_dir/partition-table.sfdisk"
  sync

  echo "Validated retired SSD:"
  echo "  disk:       $target"
  echo "  model:      $expected_model"
  echo "  serial:     $expected_serial"
  echo "  size:       $expected_size bytes"
  echo "  backup:     $backup_dir"
  echo "  new UUID:   $new_uuid"
  echo "  mount at:   $mount_point"
  printf "Type '%s' to continue: " "$confirmation"
  IFS= read -r answer
  [[ "$answer" == "$confirmation" ]] || die "Confirmation did not match; disk was not changed."

  sgdisk --zap-all "$target"
  sgdisk --clear --new=1:0:0 --typecode=1:8300 --change-name=1:DATA-SSD "$target"
  sgdisk --verify "$target"
  partprobe "$target"
  udevadm settle
  partition_one="$(partition_by_number "$target" 1)"
  [[ -b "$partition_one" ]] || die "New data partition did not appear."
  mkfs.ext4 -F -U "$new_uuid" -L data-ssd "$partition_one"
else
  die "Disk layout is neither the exact retired NixOS layout nor the resumable data layout."
fi

mkdir -p "$mount_point"
mount "$partition_one" "$mount_point"
chown liou:users "$mount_point"
chmod 0755 "$mount_point"
sync
umount "$mount_point"

echo "Old NixOS SSD is now an ext4 data disk with UUID $new_uuid."
echo "Apply the NixOS declaration to mount it:"
echo "  cd /home/liou/nix-tools"
echo "  nu rerun.nu liou --host liu-bigpc"
