#!/usr/bin/env bash
set -euo pipefail

old_user=liu
new_user=liou
expected_uid=1000
log_file=/var/log/migrate-liu-to-liou.log

fail() {
  echo "error: $*" >&2
  exit 1
}

preflight() {
  [ "$(id -u)" -eq 0 ] || fail "run this script through sudo"
  [ "$(id -u "$old_user")" -eq "$expected_uid" ] || fail "$old_user is not UID $expected_uid"
  ! id "$new_user" >/dev/null 2>&1 || fail "$new_user already exists"
  [ -d "/home/$old_user" ] || fail "/home/$old_user does not exist"
  [ ! -e "/home/$new_user" ] || fail "/home/$new_user already exists"
  local next_system current_system
  next_system="$(readlink -f /nix/var/nix/profiles/system)"
  current_system="$(readlink -f /run/current-system)"
  [ -e "$next_system" ] || fail "the next system closure is missing"
  [ "$next_system" != "$current_system" ] ||
    fail "run 'nu rerun.nu liou --host liu-bigpc --boot' before the migration"
  case "$(basename "$next_system")" in
    *-nixos-system-liu-bigpc-*) ;;
    *) fail "the next system profile is not a liu-bigpc configuration" ;;
  esac
}

perform_migration() {
  exec >>"$log_file" 2>&1
  echo "[$(date --iso-8601=seconds)] beginning account migration"

  # Prevent the display manager and old per-user system services from
  # immediately recreating UID 1000 processes while the account is renamed.
  systemctl stop display-manager.service || true
  systemctl stop syncthing.service || true
  loginctl terminate-user "$old_user" || true
  for _ in $(seq 1 30); do
    if ! pgrep -u "$expected_uid" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if pgrep -u "$expected_uid" >/dev/null 2>&1; then
    ps -u "$expected_uid" -o pid=,comm=
    fail "processes owned by UID $expected_uid are still running"
  fi

  usermod --login "$new_user" --home "/home/$new_user" --move-home "$old_user"

  if [ -e "/var/lib/AccountsService/users/$old_user" ]; then
    mv "/var/lib/AccountsService/users/$old_user" "/var/lib/AccountsService/users/$new_user"
  fi

  [ "$(id -u "$new_user")" -eq "$expected_uid" ] || fail "renamed account has the wrong UID"
  [ -d "/home/$new_user" ] || fail "renamed home directory is missing"
  chown "$new_user:users" "/home/$new_user"

  echo "[$(date --iso-8601=seconds)] migration complete; rebooting"
  systemctl reboot
}

schedule_migration() {
  preflight
  local script_path
  script_path="$(readlink -f "$0")"

  systemd-run \
    --unit=migrate-liu-to-liou \
    --collect \
    --setenv=PATH=/run/current-system/sw/bin:/run/wrappers/bin \
    --on-active=5s \
    /run/current-system/sw/bin/bash "$script_path" --perform

  echo "Migration scheduled. This session will disconnect in about five seconds."
  echo "The machine will reboot into the new configuration when the rename succeeds."
  echo "Log: $log_file"
}

case "${1:-}" in
  --perform)
    preflight
    perform_migration
    ;;
  "")
    schedule_migration
    ;;
  *)
    fail "unknown argument: $1"
    ;;
esac
