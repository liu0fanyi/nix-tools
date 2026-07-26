#!/usr/bin/env bash
set -euo pipefail

deploy_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
unit_source="$deploy_dir/.generated/dufs-plus-compose.service"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_target="$unit_dir/dufs-plus-compose.service"
terminal_unit_source="$deploy_dir/.generated/ttyd-compose.service"
terminal_unit_target="$unit_dir/ttyd-compose.service"

python3 "$deploy_dir/scripts/manage.py" render
install -d -m 700 "$unit_dir"
install -m 600 "$unit_source" "$unit_target"
if [[ -f "$terminal_unit_source" ]]; then
  install -m 600 "$terminal_unit_source" "$terminal_unit_target"
fi
systemctl --user daemon-reload

echo "Installed $unit_target"
if [[ -f "$terminal_unit_source" ]]; then
  echo "Installed $terminal_unit_target"
fi
echo "It is not enabled yet. Enable it only after the production cutover succeeds:"
echo "  systemctl --user enable dufs-plus-compose.service"
