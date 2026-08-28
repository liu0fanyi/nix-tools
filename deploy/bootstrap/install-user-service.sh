#!/usr/bin/env bash
# Bootstrap generated user units on a new host.
set -euo pipefail

deploy_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="${1:-$deploy_dir/instances/home.toml}"
output="${2:-${XDG_DATA_HOME:-$HOME/.local/share}/dufs-plus/runtime/home}"
unit_source="$output/dufs-plus-compose.service"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_target="$unit_dir/dufs-plus-compose.service"
terminal_unit_source="$output/ttyd-compose.service"
terminal_unit_target="$unit_dir/ttyd-compose.service"

python3 "$deploy_dir/scripts/manage.py" --config "$config" --output "$output" render
install -d -m 700 "$unit_dir"
install -m 600 "$unit_source" "$unit_target"
if [[ -f "$terminal_unit_source" ]]; then
  install -m 600 "$terminal_unit_source" "$terminal_unit_target"
fi
systemctl --user daemon-reload

echo "Installed $unit_target"
if [[ -f "$terminal_unit_source" ]]; then
  echo "Installed $terminal_unit_target"
  units="ttyd-compose.service dufs-plus-compose.service"
else
  units="dufs-plus-compose.service"
fi
echo "After validating the generated configuration, enable the installed units:"
echo "  systemctl --user enable --now $units"
