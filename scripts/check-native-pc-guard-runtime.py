#!/usr/bin/env python3
"""Exercise generated ExecCondition in owned transient units; no real container mutations."""
import argparse
import copy
import json
from pathlib import Path
import shlex
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent / 'tests'))
from test_native_pc_mode_guard import StartupGuard
from native_pc_mode_guard import NAMES, UNITS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = StartupGuard(); fixture.setUp()
    f = fixture.fixture
    try:
        unit_root = args.generation / 'home-files/.config/systemd/user'
        commands = {}
        for mode, unit in [('native', 'tag-all-core.service'), ('container', 'pc-private-node-restore.service')]:
            text = (unit_root / unit).read_text()
            command = next(line.removeprefix('ExecCondition=') for line in text.splitlines() if line.startswith('ExecCondition='))
            commands[mode] = shlex.split(command)
            assert commands[mode][2:4] == ['--mode', mode]
            assert Path(commands[mode][1]).read_text() == (Path(__file__).parent / 'native_pc_mode_guard.py').read_text()
        for unit in ['tag-native-files.service', 'tag-native-workspace.service']:
            assert ' --mode native ' in (unit_root / unit).read_text()
        restore = (unit_root / 'pc-private-node-restore.service').read_text()
        assert 'WantedBy=default.target' in restore
        assert 'ConditionPathExists=/home/liou/.local/share/tag-all/pc-native/container-mode' in restore
        assert 'ConditionPathExists=/home/liou/.local/share/tag-all/pc-native/ready' in restore
        start = shlex.split(next(line.removeprefix('ExecStart=') for line in restore.splitlines() if line.startswith('ExecStart=')))
        start_text = Path(start[0]).read_text()
        assert all(name in start_text for name in NAMES)
        assert 'podman.sock start' in start_text and 'ps -a' not in start_text
        guard = f.root / 'guard.py'
        guard.write_text(Path(commands['native'][1]).read_text().replace("ROOT = Path('/home/liou/.local/share/tag-all/pc-native')", 'ROOT = Path(' + repr(str(f.dest)) + ')'))
        records_file = f.root / 'records.json'; units_file = f.root / 'units.json'
        podman = f.root / 'fixture-podman'; systemctl = f.root / 'fixture-systemctl'
        podman.write_text('#!' + sys.executable + '\nimport sys\nfrom pathlib import Path\nassert sys.argv[1:6] == ["--remote", "--url", "unix:///run/user/1000/podman/podman.sock", "container", "inspect"]\nprint(Path(' + repr(str(records_file)) + ').read_text())\n')
        systemctl.write_text('#!' + sys.executable + '\nimport sys,json\nfrom pathlib import Path\nassert sys.argv[1:3] == ["--user", "is-active"]\nprint(json.loads(Path(' + repr(str(units_file)) + ').read_text())[sys.argv[3]])\n')
        podman.chmod(0o700); systemctl.chmod(0o700)
        mark = f.root / 'mark.py'; mark.write_text('import sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text("executed")\n')
        def run(case, mode, records, units, expected):
            records_file.write_text(json.dumps(list(records.values()))); units_file.write_text(json.dumps(units))
            marker = f.root / (case + '.executed')
            command = list(commands[mode]); command[1] = str(guard)
            command[command.index('--podman')+1] = str(podman)
            command[command.index('--systemctl')+1] = str(systemctl)
            result = subprocess.run(['systemd-run', '--user', '--wait', '--collect', '--quiet',
                '--unit=native-pc-guard-' + uuid.uuid4().hex,
                '--property=PrivateUsers=yes', '--property=PrivateMounts=yes',
                '--property=ExecCondition=' + shlex.join(command),
                sys.executable, str(mark), str(marker)], text=True, capture_output=True, timeout=30)
            if marker.exists() != expected or (expected and result.returncode):
                raise RuntimeError('Transient startup guard case failed: ' + case)
        run('native-stopped', 'native', fixture.records, fixture.units, True)
        running = copy.deepcopy(fixture.records); running[NAMES[0]]['State']['Running'] = True
        run('native-source-running', 'native', running, fixture.units, False)
        fixture.container_mode()
        run('container-new-state', 'container', fixture.records, fixture.units, True)
        old = copy.deepcopy(fixture.records)
        next(m for m in old[NAMES[0]]['Mounts'] if m['Destination']=='/data')['Source'] = '/old/source/data'
        run('container-old-state', 'container', old, fixture.units, False)
        run('container-native-active', 'container', fixture.records, fixture.units | {UNITS[1]: 'active'}, False)
        changed = copy.deepcopy(fixture.records); changed[NAMES[3]]['Image']='sha256:'+'b'*64
        run('container-other-image', 'container', changed, fixture.units, False)
        run('container-tools-active', 'container', fixture.records, fixture.units | {'tag-all-tools.service': 'active'}, False)
        run('container-tools-absent-core-only', 'container', fixture.records, fixture.units | {'tag-all-tools.service': 'unknown'}, True)
        report={'generated_generation': str(args.generation), 'transient_execcondition_cases_passed': 8,
            'private_user_and_mount_namespace': True, 'default_container_restore_is_guarded': True,
            'only_five_fixed_restore_names': True, 'real_container_commands_mutated': False,
            'production_state_read': False, 'activated': False}
        args.output.write_text(json.dumps(report, indent=2)+'\n')
        print('Eight generated ExecCondition cases passed; owned transient units collected')
    finally: fixture.doCleanups()


if __name__ == '__main__': main()
