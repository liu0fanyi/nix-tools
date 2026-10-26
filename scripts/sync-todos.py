#!/usr/bin/env python3
"""Publish this project's Markdown overview through the centrally managed skill."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HELPER = Path.home() / '.codex/skills/work-progress/scripts/overview.py'
if __name__ == '__main__':
    if not HELPER.is_file():
        raise SystemExit('Install work-progress with nix-tools: just agent-rules --apply')
    if any(arg != '--dry-run' for arg in sys.argv[1:]):
        raise SystemExit('Only --dry-run is supported; project destination is centrally registered')
    subprocess.run([sys.executable, str(HELPER), '--repo', str(ROOT), '--publish', *sys.argv[1:]], check=True)
