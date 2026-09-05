#!/usr/bin/env bash
set -euo pipefail

# Prefer running from a NixOS live environment. Passing --online allows a
# two-pass migration from the installed liu-bigpc root when no live medium is
# available. Close applications that write important user data first.
# Only the former Windows D: partition is deleted. The Microsoft Reserved and
# Windows EFI partitions keep their original partition GUIDs and contents.

readonly expected_target_model="KIOXIA-EXCERIA SATA SSD"
readonly expected_target_serial="Z12B81WRKFW4"
readonly expected_target_size=480103981056
readonly expected_msr_partuuid="6d7c2c5e-69e0-40be-b44e-d27aa93a8524"
readonly expected_data_partuuid="84f0b944-ef86-4fbe-822d-c967fa792c80"
readonly expected_data_uuid="F6465A114659D2CB"
readonly expected_windows_esp_partuuid="f973da9b-7447-473b-9a70-3064debb9a26"
readonly expected_windows_esp_uuid="2480-A068"

readonly source_root_uuid="428f77c1-1fe1-47f4-8457-9944aec9e0e9"
readonly source_root_model="WDC WDS120G1G0A-00SS50"
readonly source_root_serial="171708A01FEB"
readonly data_disk_uuid="92af0d70-de16-4502-93fb-651392709a7b"

readonly new_root_uuid="587d3eb3-3d34-47b5-bec1-391bbf56e634"
readonly new_esp_uuid="2909-BA9A"
readonly new_esp_volume_id="2909BA9A"
readonly new_swap_uuid="bb4a5c9c-268f-4ddd-816a-2d3d062a6137"

# These sector boundaries exactly subdivide the old partition 2 extent. They
# do not touch partition 1 (MSR) or partition 3 (Windows ESP).
readonly nix_esp_start=32768
readonly nix_esp_end=2129919
readonly nix_root_start=2129920
readonly nix_root_end=903939455
readonly nix_swap_start=903939456
readonly nix_swap_end=937493887

readonly old_mount="/mnt/liu-bigpc-old"
readonly new_mount="/mnt/liu-bigpc-new"
readonly data_mount="/mnt/liu-bigpc-data"
readonly confirmation="MIGRATE ${expected_target_serial} DELETE ${expected_data_partuuid}"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

online=false
case "${1-}" in
  "") ;;
  --online) online=true ;;
  *) die "Usage: $0 [--online]" ;;
esac

trim() {
  xargs <<<"$*"
}

partition_by_number() {
  local disk="$1"
  local number="$2"
  lsblk -nrpo PATH,PARTN "$disk" | awk -v number="$number" '$2 == number { print $1 }'
}

single_value() {
  local column="$1"
  local device="$2"
  trim "$(lsblk -dn -o "$column" "$device")"
}

cleanup() {
  sync || true
  mountpoint -q "$new_mount/boot" && umount "$new_mount/boot" || true
  mountpoint -q "$new_mount" && umount "$new_mount" || true
  mountpoint -q "$old_mount" && umount "$old_mount" || true
  mountpoint -q "$data_mount" && umount "$data_mount" || true
}
trap cleanup EXIT

if (( EUID != 0 )); then
  if "$online"; then
    die "Run this script as root: sudo $0 --online"
  else
    die "Run this script as root: sudo $0"
  fi
fi

required_commands=(
  awk blockdev dd findmnt grep lsblk mkfs.ext4 mkfs.fat mkswap mount \
  mountpoint partprobe readlink rsync sfdisk sgdisk swapon sync udevadm umount xargs
)
missing_commands=()
for command in "${required_commands[@]}"; do
  command -v "$command" >/dev/null || missing_commands+=("$command")
done

if (( ${#missing_commands[@]} > 0 )); then
  if [[ "${NIXOS_MIGRATION_TOOL_ENV-}" == 1 ]]; then
    die "Required commands are still missing inside the Nix tool environment: ${missing_commands[*]}"
  fi
  nix_command="$(command -v nix || true)"
  [[ -n "$nix_command" ]] || die "Required commands are missing and nix is unavailable: ${missing_commands[*]}"
  script_path="$(readlink -f "$0")"
  echo "Preparing missing migration tools with Nix: ${missing_commands[*]}"
  exec env NIXOS_MIGRATION_TOOL_ENV=1 "$nix_command" \
    --extra-experimental-features "nix-command flakes" \
    shell \
    nixpkgs#gptfdisk \
    nixpkgs#parted \
    nixpkgs#rsync \
    nixpkgs#dosfstools \
    nixpkgs#e2fsprogs \
    nixpkgs#util-linux \
    -c "$script_path" "$@"
fi

mapfile -t matching_disks < <(lsblk -dpno PATH,TYPE | awk '$2 == "disk" { print $1 }' | while read -r candidate; do
  model="$(single_value MODEL "$candidate")"
  serial="$(single_value SERIAL "$candidate")"
  if [[ "$model" == "$expected_target_model" && "$serial" == "$expected_target_serial" ]]; then
    printf '%s\n' "$candidate"
  fi
done)
(( ${#matching_disks[@]} == 1 )) ||
  die "Expected exactly one target disk matching $expected_target_model / $expected_target_serial; found ${#matching_disks[@]}."

target_disk="$(readlink -f "${matching_disks[0]}")"
target_size="$(blockdev --getsize64 "$target_disk")"
target_pttype="$(single_value PTTYPE "$target_disk")"
[[ "$target_size" == "$expected_target_size" ]] ||
  die "Target size mismatch: expected $expected_target_size, got $target_size."
[[ "$target_pttype" == "gpt" ]] || die "Target partition table is not GPT: $target_pttype"

source_root="$(readlink -f "/dev/disk/by-uuid/$source_root_uuid")"
[[ -b "$source_root" ]] || die "Old NixOS root UUID is missing: $source_root_uuid"
running_root="$(findmnt -nro SOURCE /)"
running_from_source=false
if [[ -b "$running_root" && "$(readlink -f "$running_root")" == "$source_root" ]]; then
  running_from_source=true
fi
if "$running_from_source" && ! "$online"; then
  die "Running from the installed root. Re-run with --online, or use a NixOS live environment."
fi
if "$online" && ! "$running_from_source"; then
  die "--online is only valid while running from the old NixOS root ($source_root_uuid)."
fi
source_parent_name="$(single_value PKNAME "$source_root")"
source_disk="/dev/$source_parent_name"
[[ "$(single_value MODEL "$source_disk")" == "$source_root_model" ]] || die "Old root disk model mismatch."
[[ "$(single_value SERIAL "$source_disk")" == "$source_root_serial" ]] || die "Old root disk serial mismatch."
[[ "$source_disk" != "$target_disk" ]] || die "Source and target resolved to the same disk."

msr_partition="$(partition_by_number "$target_disk" 1)"
partition_two="$(partition_by_number "$target_disk" 2)"
windows_esp_partition="$(partition_by_number "$target_disk" 3)"
[[ -b "$msr_partition" && -b "$partition_two" && -b "$windows_esp_partition" ]] ||
  die "Expected target partitions 1, 2, and 3 were not all found."

[[ "$(single_value PARTUUID "$msr_partition")" == "$expected_msr_partuuid" ]] || die "MSR PARTUUID mismatch."
[[ "$(single_value PARTUUID "$windows_esp_partition")" == "$expected_windows_esp_partuuid" ]] || die "Windows ESP PARTUUID mismatch."
[[ "$(single_value UUID "$windows_esp_partition")" == "$expected_windows_esp_uuid" ]] || die "Windows ESP filesystem UUID mismatch."
[[ "$(single_value FSTYPE "$windows_esp_partition")" == "vfat" ]] || die "Windows ESP is not FAT."

while read -r target_node; do
  if findmnt -rn -S "$target_node" >/dev/null; then
    die "Target device is mounted: $target_node"
  fi
  if swapon --noheadings --raw --show=NAME 2>/dev/null | grep -Fxq "$target_node"; then
    die "Target device is active as swap: $target_node"
  fi
done < <(lsblk -nrpo PATH "$target_disk")

nix_root_partition="$(partition_by_number "$target_disk" 4)"
nix_swap_partition="$(partition_by_number "$target_disk" 5)"
layout_state=""

if [[ "$(single_value PARTUUID "$partition_two")" == "$expected_data_partuuid" ]]; then
  [[ "$(single_value UUID "$partition_two")" == "$expected_data_uuid" ]] || die "D: filesystem UUID mismatch."
  [[ "$(single_value FSTYPE "$partition_two")" == "ntfs" ]] || die "D: is no longer NTFS."
  [[ -z "$nix_root_partition" && -z "$nix_swap_partition" ]] || die "Unexpected partitions 4 or 5 coexist with the old D: partition."
  layout_state="original"
elif [[ -b "$nix_root_partition" && -b "$nix_swap_partition" ]]; then
  # A previous run may have been interrupted during formatting or rsync. Only
  # accept the exact sector geometry created by this script.
  [[ "$(single_value START "$partition_two")" == "$nix_esp_start" ]] || die "Nix ESP start sector mismatch."
  [[ "$(single_value START "$nix_root_partition")" == "$nix_root_start" ]] || die "Nix root start sector mismatch."
  [[ "$(single_value START "$nix_swap_partition")" == "$nix_swap_start" ]] || die "Nix swap start sector mismatch."
  [[ "$(single_value SIZE "$partition_two")" == "$(( (nix_esp_end - nix_esp_start + 1) * 512 ))" ]] || die "Nix ESP size mismatch."
  [[ "$(single_value SIZE "$nix_root_partition")" == "$(( (nix_root_end - nix_root_start + 1) * 512 ))" ]] || die "Nix root size mismatch."
  [[ "$(single_value SIZE "$nix_swap_partition")" == "$(( (nix_swap_end - nix_swap_start + 1) * 512 ))" ]] || die "Nix swap size mismatch."
  layout_state="planned"
else
  die "Target is neither the original D: layout nor the exact resumable NixOS layout."
fi

mkdir -p "$old_mount" "$new_mount" "$data_mount"
if "$online"; then
  source_tree="/"
else
  mount -o ro "/dev/disk/by-uuid/$source_root_uuid" "$old_mount"
  source_tree="$old_mount/"
fi
source_repo="${source_tree%/}/home/liou/nix-tools"
[[ -f "$source_repo/flake.nix" ]] || die "nix-tools is missing from the old root."
hardware_config="$source_repo/nixos/hosts/liu-bigpc/hardware-configuration.nix"
grep -Fq "$new_root_uuid" "$hardware_config" || die "Repository does not contain the planned new root UUID."
grep -Fq "$new_esp_uuid" "$hardware_config" || die "Repository does not contain the planned new ESP UUID."
grep -Fq "$new_swap_uuid" "$hardware_config" || die "Repository does not contain the planned new swap UUID."

mount "/dev/disk/by-uuid/$data_disk_uuid" "$data_mount"
if [[ "$layout_state" == "original" ]]; then
  backup_dir="$data_mount/migration-backups/liu-bigpc-kioxia-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$backup_dir"
  sgdisk --backup="$backup_dir/partition-table.gpt" "$target_disk"
  sfdisk --dump "$target_disk" >"$backup_dir/partition-table.sfdisk"
  dd if="$windows_esp_partition" of="$backup_dir/windows-efi-partition.img" bs=4M status=progress conv=fsync
  sync

  echo
  echo "Validated migration target:"
  echo "  disk:               $target_disk"
  echo "  model:              $expected_target_model"
  echo "  serial:             $expected_target_serial"
  echo "  disk size:          $target_size bytes"
  echo "  DELETE only:        partition 2 / $expected_data_partuuid / NTFS $expected_data_uuid"
  echo "  PRESERVE:           partition 1 / MSR / $expected_msr_partuuid"
  echo "  PRESERVE:           partition 3 / Windows ESP / $expected_windows_esp_partuuid / $expected_windows_esp_uuid"
  echo "  backup directory:   $backup_dir"
  echo
  printf "Type '%s' to continue: " "$confirmation"
  IFS= read -r answer
  [[ "$answer" == "$confirmation" ]] || die "Confirmation did not match; partition table was not changed."

  sgdisk \
    --delete=2 \
    --new=2:${nix_esp_start}:${nix_esp_end} --typecode=2:EF00 --change-name=2:NIXOS-ESP \
    --new=4:${nix_root_start}:${nix_root_end} --typecode=4:8300 --change-name=4:NIXOS-ROOT \
    --new=5:${nix_swap_start}:${nix_swap_end} --typecode=5:8200 --change-name=5:NIXOS-SWAP \
    "$target_disk"
  sgdisk --verify "$target_disk"
  partprobe "$target_disk"
  udevadm settle

  partition_two="$(partition_by_number "$target_disk" 2)"
  nix_root_partition="$(partition_by_number "$target_disk" 4)"
  nix_swap_partition="$(partition_by_number "$target_disk" 5)"
  [[ -b "$partition_two" && -b "$nix_root_partition" && -b "$nix_swap_partition" ]] ||
    die "New partitions did not appear after partition table update."

  mkfs.fat -F 32 -i "$new_esp_volume_id" -n NIXOS-ESP "$partition_two"
  mkfs.ext4 -F -U "$new_root_uuid" -L nixos "$nix_root_partition"
  mkswap -U "$new_swap_uuid" -L swap "$nix_swap_partition"
else
  echo "Exact planned partition layout already exists; resuming without repartitioning."
  esp_uuid="$(single_value UUID "$partition_two")"
  root_uuid="$(single_value UUID "$nix_root_partition")"
  swap_uuid="$(single_value UUID "$nix_swap_partition")"
  [[ -z "$esp_uuid" || "$esp_uuid" == "$new_esp_uuid" ]] || die "Unexpected filesystem on planned Nix ESP."
  [[ -z "$root_uuid" || "$root_uuid" == "$new_root_uuid" ]] || die "Unexpected filesystem on planned Nix root."
  [[ -z "$swap_uuid" || "$swap_uuid" == "$new_swap_uuid" ]] || die "Unexpected filesystem on planned Nix swap."
  [[ -n "$esp_uuid" ]] || mkfs.fat -F 32 -i "$new_esp_volume_id" -n NIXOS-ESP "$partition_two"
  [[ -n "$root_uuid" ]] || mkfs.ext4 -F -U "$new_root_uuid" -L nixos "$nix_root_partition"
  [[ -n "$swap_uuid" ]] || mkswap -U "$new_swap_uuid" -L swap "$nix_swap_partition"
fi

# Prove the preserved Windows partitions still have their original identities.
msr_partition="$(partition_by_number "$target_disk" 1)"
windows_esp_partition="$(partition_by_number "$target_disk" 3)"
[[ "$(single_value PARTUUID "$msr_partition")" == "$expected_msr_partuuid" ]] || die "MSR changed unexpectedly."
[[ "$(single_value PARTUUID "$windows_esp_partition")" == "$expected_windows_esp_partuuid" ]] || die "Windows ESP changed unexpectedly."
[[ "$(single_value UUID "$windows_esp_partition")" == "$expected_windows_esp_uuid" ]] || die "Windows ESP filesystem changed unexpectedly."

mount "$nix_root_partition" "$new_mount"
mkdir -p "$new_mount/boot"
mount "$partition_two" "$new_mount/boot"

copy_root() {
  rsync -aHAXx --numeric-ids --delete --info=progress2 \
    --exclude='/boot' \
    --exclude='/dev/*' \
    --exclude='/proc/*' \
    --exclude='/sys/*' \
    --exclude='/run/*' \
    --exclude='/tmp/*' \
    --exclude='/mnt/*' \
    --exclude='/media/*' \
    --exclude='/lost+found' \
    "$source_tree" "$new_mount/"
}

echo "Copying the old NixOS root to the new SSD..."
copy_root

if "$online"; then
  command -v nixos-rebuild >/dev/null || die "nixos-rebuild is required for --online."
  echo
  echo "Installing a boot generation on the old ESP that points at the new root..."
  nixos-rebuild boot --flake "$source_repo#liu-bigpc"
  echo
  echo "Running the final synchronization pass..."
  sync
  copy_root
fi

mkdir -p "$new_mount/dev" "$new_mount/proc" "$new_mount/sys" "$new_mount/run" "$new_mount/tmp" "$new_mount/mnt" "$new_mount/media"
chmod 1777 "$new_mount/tmp"
sync

echo
echo "Migration copy completed. Windows EFI was preserved and backed up."
echo "Next steps:"
if "$online"; then
  echo "  1. Reboot and select the newest NixOS generation from the old SSD's systemd-boot menu."
  echo "  2. Verify that the new root is active: findmnt -no SOURCE /"
  echo "  3. On the new root, run: nu rerun.nu liou --host liu-bigpc --install-bootloader"
  echo "  4. Test firmware boot from the KIOXIA SSD and test Windows separately."
else
  echo "  1. Reboot into the existing NixOS installation on the old 120 GB SSD."
  echo "  2. cd /home/liou/nix-tools"
  echo "  3. nu rerun.nu liou --host liu-bigpc --boot"
  echo "  4. Reboot; the newest generation should mount root UUID $new_root_uuid."
  echo "  5. Verify: findmnt -no SOURCE /"
  echo "  6. On the new root, run: nu rerun.nu liou --host liu-bigpc --install-bootloader"
  echo "  7. Test firmware boot from the KIOXIA SSD and test Windows separately."
fi
echo "Do not erase the old 120 GB SSD until both systems have passed these tests."
