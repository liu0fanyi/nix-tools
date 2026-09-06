#!/usr/bin/env bash
set -euo pipefail
# Compatibility entry only. Old default-IP /dev/sda installer is retired.
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$repo_dir/scripts/host-install.py" "$@"
