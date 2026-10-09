#!/usr/bin/env python3
"""Register the verified PC units independently of a transient HM candidate generation."""
import json
import os
from pathlib import Path
import socket
import subprocess

ROOT = Path('/home/liou/.local/share/tag-all/pc-native')
REPO = Path(__file__).resolve().parents[1]
NAMES = ['tag-all-core.service', 'tag-all-tools.service', 'tag-native-files.service', 'tag-native-workspace.service', 'tag-native-stack.target']


def main():
    if socket.gethostname() != 'liu-bigpc' or os.getuid() != 1000:
        raise ValueError('Only the fixed PC liou account is supported')
    subprocess.run(['python3', str(REPO / 'scripts/native_pc_mode_guard.py'), '--mode', 'native'], check=True)
    report = json.loads((REPO / 'specs/012-native-core-gateway/native-final-combination-results.json').read_text())
    generation = Path(report['actual_home_generation'])
    source = generation / 'home-files/.config/systemd/user'
    units = Path('/home/liou/.local/share/systemd/user')
    if units.is_symlink(): raise ValueError('User unit directory must not be a symlink')
    units.mkdir(parents=True, exist_ok=True)
    mappings = {units / name: (source / name).resolve(strict=True) for name in NAMES}
    wants = units / 'default.target.wants'
    if wants.is_symlink(): raise ValueError('Wants directory must not be a symlink')
    wants.mkdir(exist_ok=True)
    mappings[wants / 'tag-native-stack.target'] = mappings[units / 'tag-native-stack.target']
    for destination, target in mappings.items():
        if not str(target).startswith('/nix/store/') or not target.is_file():
            raise ValueError('Only the immutable verified unit is allowed')
        if destination.exists() or destination.is_symlink():
            if not destination.is_symlink() or destination.resolve() != target:
                raise ValueError('Refusing to replace an unrelated user unit')
    restore = (source / 'pc-private-node-restore.service').read_text().splitlines()
    def directive(key):
        return next(line for line in restore if line.startswith(key + '='))
    override = Path('/home/liou/.config/systemd/user/pc-private-node-restore.service.d/native-cutover-guard.conf')
    text = '[Unit]\nConditionPathExists=\nConditionPathExists=' + str(ROOT / 'ready') + '\nConditionPathExists=' + str(ROOT / 'container-mode') + '\n[Service]\nKillMode=process\nExecCondition=\n' + directive('ExecCondition') + '\nExecStart=\n' + directive('ExecStart') + '\n'
    if override.exists() or override.is_symlink():
        if override.is_symlink() or override.read_text() != text:
            raise ValueError('Refusing to replace an unrelated restore override')
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(text); override.chmod(0o644)
    subprocess.run(['nix-store', '--add-root', str(ROOT / 'config/native-home-gc-root'), '--indirect', '--realise', str(generation)], check=True)
    for destination, target in mappings.items():
        if not destination.is_symlink(): destination.symlink_to(target)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    (ROOT / 'config/user-unit-registration.json').write_text(json.dumps({str(k): str(v) for k, v in mappings.items()}, indent=2)+'\n')
    (ROOT / 'config/user-unit-registration.json').chmod(0o600)
    subprocess.run(['systemctl', '--user', 'enable', 'tag-native-stack.target'], check=True)
    print('Verified PC user units registered persistently; old restore is guarded; system generation untouched')


if __name__ == '__main__': main()
