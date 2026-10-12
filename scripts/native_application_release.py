#!/usr/bin/env python3
"""Hash-bound native application updates; configuration rollback never restores data."""
from contextlib import contextmanager
from dataclasses import dataclass
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import time
import uuid

from application_entry_transaction import ConfigurationTransaction, atomic, backup_state, create_lock, digest, exclusive, offline_states, private

MANAGED = '80-tag-version.conf'
HEADER = '# Managed by tag-native-release\n'


@dataclass(frozen=True)
class Scope:
    name: str
    units: tuple
    states: tuple
    connections: tuple
    probes: tuple
    release_root: Path
    unit_root: Path
    uphold_target: str | None = None


def fixed_scope(name):
    expected = {'pc': 'liu-bigpc', 'nuc': 'nuc'}
    if name not in expected or socket.gethostname() != expected[name] or os.getuid() != 1000:
        raise ValueError('Fixed host and liou user required')
    data = Path('/home/liou/.local/share/tag-all')
    unit_root = Path('/home/liou/.config/systemd/user')
    if name == 'pc':
        root = data / 'pc-native'
        return Scope(name, ('tag-all-core.service',), (root / 'data',),
                     ('unix://' + str(root / 'tools/runtime.sock'),), ((5006, '/tag-api/tags', 200),),
                     data / 'native-version-releases', unit_root, 'tag-native-stack.target')
    root = data / 'nuc-native'
    return Scope(name, ('tag-nuc-private-core.service', 'tag-nuc-readonly-core.service'),
                 tuple(root / role / 'state' for role in ('private', 'readonly')),
                 tuple('unix://' + str(root / role / 'tools/runtime.sock') for role in ('private', 'readonly')),
                 ((5006, '/', 401), (5008, '/', 401)), data / 'native-version-releases', unit_root, 'tag-native-nuc.target')


def execute(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=180, check=True)
    return result.stdout


def fingerprint(directory):
    directory = Path(directory)
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink(): raise ValueError('Frontend symlink refused')
        if path.is_file(): result[str(path.relative_to(directory))] = digest(path)
        elif not path.is_dir(): raise ValueError('Frontend special file refused')
    if 'index.html' not in result: raise ValueError('Frontend index required')
    return result


def command_line(text):
    starts = [line.split('=', 1)[1] for line in text.splitlines() if line.startswith('ExecStart=') and line.split('=', 1)[1]]
    if len(starts) != 1: raise ValueError('One supported ExecStart required')
    return starts[0]


def replace_command(old, package, frontend):
    arguments = shlex.split(old)
    if not arguments or not re.fullmatch(r'/nix/store/[a-z0-9]{32}-tag-all-workspace-native-0\.1\.0/bin/tag-all-core', arguments[0]):
        raise ValueError('Existing native application launcher required')
    key = '--workspace-entry-frontend'
    if arguments.count(key) != 1: raise ValueError('One existing frontend argument required')
    position = arguments.index(key) + 1
    if position >= len(arguments): raise ValueError('Missing frontend argument')
    previous = arguments[position]
    if not previous.startswith('/nix/store/') or old.count(previous) != 1 or old.count(arguments[0]) != 1:
        raise ValueError('Unambiguous immutable application/frontend paths required')
    changed = old.replace(arguments[0], str(package / 'bin/tag-all-core'), 1).replace(previous, str(frontend), 1)
    actual = shlex.split(changed)
    expected = arguments[:]
    expected[0] = str(package / 'bin/tag-all-core'); expected[position] = str(frontend)
    if actual != expected: raise ValueError('Unrelated command argument changed')
    return changed, [str(Path(arguments[0]).parent.parent), previous]


class Manager:
    def __init__(self, scope, run=execute):
        self.scope, self.run = scope, run

    def properties(self, unit):
        value = self.run(['systemctl', '--user', 'show', unit, '-p', 'LoadState', '-p', 'ActiveState', '-p', 'FragmentPath', '-p', 'DropInPaths', '-p', 'MainPID', '-p', 'ControlGroup'])
        return dict(line.split('=', 1) for line in value.splitlines() if '=' in line)

    def unit_input(self, unit):
        properties = self.properties(unit)
        if properties.get('LoadState') != 'loaded': raise ValueError('Current core unit unavailable')
        paths = [Path(properties['FragmentPath']), *map(Path, shlex.split(properties.get('DropInPaths', '')))]
        for path in sorted((self.scope.unit_root / (unit + '.d')).glob('*.conf')):
            if path not in paths: paths.append(path)
        command = command_line(paths[0].read_text())
        sources = []
        for index, path in enumerate(paths):
            contents = path.read_text()
            sources.append({'path': str(path), 'sha256': digest(path)})
            if index and any(line.startswith('ExecStart=') for line in contents.splitlines()):
                if path != self.scope.unit_root / (unit + '.d') / MANAGED or not contents.startswith(HEADER):
                    raise ValueError('Unmanaged ExecStart override refused')
                private(path)
                command = command_line(contents)
        return {'command': command, 'sources': sources}

    def tasks_idle(self):
        for connection in self.scope.connections:
            tasks = json.loads(self.run(['podman', '--remote', '--url', connection, 'ps', '--format', 'json']))
            if tasks: raise ValueError('Processing containers active; pause uploads and wait')
        for state in self.scope.states:
            for folder in ('music-jobs', 'transcriptions/jobs'):
                directory = state / 'metadata' / folder
                if directory.is_symlink(): raise ValueError('Task directory symlink refused')
                for path in directory.glob('*.json'):
                    if path.is_symlink() or not path.is_file(): raise ValueError('Unsafe task record')
                    if json.loads(path.read_text()).get('status') in ('queued', 'running'):
                        raise ValueError('Processing queue active; wait before update')

    def live_program(self, properties, package):
        # The entry adapter intentionally remains MainPID while its child runs
        # the Rust API. Verify the real binary among this unit's descendants.
        pending = [int(properties['MainPID'])]; seen = set()
        expected = package / 'libexec/tag-server-workspace'
        group = properties.get('ControlGroup', '')
        if not group: return False
        while pending and len(seen) < 128:
            pid = pending.pop()
            if pid <= 0 or pid in seen: continue
            seen.add(pid); process = Path('/proc') / str(pid)
            try:
                if process.stat().st_uid != os.getuid(): continue
                groups = [row.split(':', 2)[2] for row in (process / 'cgroup').read_text().splitlines()]
                if not any(value == group or value.startswith(group + '/') for value in groups): continue
                if (process / 'exe').resolve() == expected: return True
                pending.extend(map(int, (process / 'task' / str(pid) / 'children').read_text().split()))
            except (OSError, ValueError): continue
        return False

    def ready(self, package=None):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                for unit in self.scope.units:
                    properties = self.properties(unit)
                    if properties['ActiveState'] != 'active': raise ValueError('Core not active')
                    if package and not self.live_program(properties, package):
                        raise ValueError('Expected application binary is not running in the core unit')
                for port, path, expected in self.scope.probes:
                    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
                    try:
                        connection.request('GET', path)
                        response = connection.getresponse()
                        if response.status != expected: raise ValueError('Application readiness/authentication mismatch')
                        if expected == 401 and 'Basic' not in (response.getheader('WWW-Authenticate') or ''):
                            raise ValueError('Basic authentication challenge missing')
                        response.read()
                    finally: connection.close()
                return
            except (OSError, ValueError, KeyError, http.client.HTTPException): time.sleep(.2)
        raise ValueError('Native application did not become ready')

    def uphold_path(self):
        runtime = Path('/run/user/' + str(os.getuid()) + '/systemd/user.control')
        return runtime / self.scope.uphold_target

    def uphold_binding(self):
        if not self.scope.uphold_target: return None
        props = self.run(['systemctl', '--user', 'show', self.scope.uphold_target,
                          '-p', 'ActiveState', '-p', 'Upholds', '-p', 'FragmentPath', '-p', 'DropInPaths'])
        values = dict(line.split('=', 1) for line in props.splitlines() if '=' in line)
        if values['ActiveState'] != 'active': raise ValueError('Existing uphold target must be active')
        paths = [Path(values['FragmentPath']), *map(Path, shlex.split(values.get('DropInPaths', '')))]
        owned = self.uphold_path()
        sources = {str(path): digest(path) for path in paths if path != owned}
        return {'target': self.scope.uphold_target, 'fragment': values['FragmentPath'], 'sources': sources,
                'units': sorted(values.get('Upholds', '').split())}

    @contextmanager
    def suspend_upholding(self, plan):
        expected = plan.get('upholding')
        if not self.scope.uphold_target:
            if expected is not None: raise ValueError('Unexpected uphold target')
            yield
            return
        if not expected or expected['target'] != self.scope.uphold_target:
            raise ValueError('Prepared uphold target binding required')
        path = self.uphold_path()
        retained = sorted(set(expected['units']) - set(self.scope.units))
        fragment = Path(expected['fragment'])
        if any(digest(Path(source)) != sha for source, sha in expected['sources'].items()):
            raise ValueError('Original uphold sources drifted')
        lines = fragment.read_text().splitlines(keepends=True)
        content = HEADER + ''.join(('Upholds=' + ' '.join(sorted(set(line.split('=', 1)[1].split()) - set(self.scope.units))) + '\n')
                                  if line.startswith('Upholds=') else line for line in lines)
        current = self.uphold_binding()
        original_sources = dict(expected['sources'])
        if current['fragment'] == str(path): original_sources.pop(str(fragment))
        elif current['fragment'] != str(fragment): raise ValueError('Unknown uphold unit override')
        if current['sources'] != original_sources or current['units'] not in (expected['units'], retained):
            raise ValueError('Uphold target drifted')
        if path.exists() or path.is_symlink():
            if private(path).read_text() != content: raise ValueError('Unknown uphold inhibition refused')
        else:
            if current['units'] != expected['units']: raise ValueError('Unowned uphold inhibition refused')
            if not path.parent.exists(): path.parent.mkdir(parents=True, mode=0o700)
            private(path.parent, True)
            atomic(path, content)
        self.run(['systemctl', '--user', 'daemon-reload'])
        try:
            if self.uphold_binding()['units'] != retained: raise ValueError('Core uphold inhibition failed')
            yield
        finally:
            if private(path).read_text() != content: raise ValueError('Uphold inhibition changed')
            path.unlink()
            self.run(['systemctl', '--user', 'daemon-reload'])
            if self.uphold_binding() != expected: raise ValueError('Original upholding did not recover')

    def stopped(self):
        if any(self.properties(unit)['ActiveState'] not in ('inactive', 'failed') for unit in self.scope.units):
            raise ValueError('All scoped core writers must be stopped')

    def plan(self, package, frontend):
        package, frontend = Path(package), Path(frontend)
        for path in (package, frontend):
            if not re.fullmatch(r'/nix/store/[a-z0-9]{32}-[^/]+', str(path)) or not path.is_dir():
                raise ValueError('Existing immutable Nix output required')
        if (package / 'share/tag-all/application-entry').read_text() != 'enabled\n': raise ValueError('Application entry package required')
        self.ready(); self.tasks_idle()
        if self.scope.uphold_target and self.uphold_path().exists(): raise ValueError('Recover interrupted update before preparing another')
        upholding = self.uphold_binding()
        inputs, commands, previous = {}, {}, []
        for unit in self.scope.units:
            inputs[unit] = self.unit_input(unit)
            commands[unit], old = replace_command(inputs[unit]['command'], package, frontend)
            previous.extend(old)
        pointer = self.scope.release_root / 'current.json'
        if pointer.is_symlink(): raise ValueError('Version pointer symlink refused')
        return {'scope': self.scope.name, 'upholding': upholding, 'units': inputs, 'commands': commands, 'package': str(package),
                'binary_sha256': digest(package / 'libexec/tag-server-workspace'), 'frontend': str(frontend),
                'frontend_sha256': fingerprint(frontend), 'previous_outputs': sorted(set(previous)),
                'pointer_before': digest(private(pointer)) if pointer.exists() else None,
                'state_policy': 'reuse-current-state-never-restore-backup'}

    def prepare(self, package, frontend):
        plan = self.plan(package, frontend)
        root = self.scope.release_root
        if not root.exists():
            root.mkdir(mode=0o700)
            atomic(root / 'manager-version', 'native-release-v1\n')
        private(root, True)
        if private(root / 'manager-version').read_text() != 'native-release-v1\n': raise ValueError('Unknown release manager namespace')
        plan['preparation_id'] = uuid.uuid4().hex
        encoded = json.dumps(plan, sort_keys=True, indent=2) + '\n'
        identity = hashlib.sha256(encoded.encode()).hexdigest()
        release = root / identity
        if release.exists():
            if private(release / 'manifest.json').read_text() != encoded: raise ValueError('Prepared release changed')
            return release
        release.mkdir(mode=0o700)
        atomic(release / 'manifest.json', encoded)
        for unit, command in plan['commands'].items():
            atomic(release / unit, HEADER + '[Service]\nExecStart=\nExecStart=' + command + '\n')
        atomic(release / 'current.json', json.dumps({'manifest': identity, 'package': plan['package'], 'frontend': plan['frontend']}) + '\n')
        for index, output in enumerate([*plan['previous_outputs'], plan['package'], plan['frontend']]):
            self.run(['nix-store', '--add-root', str(release / ('output-' + str(index))), '--indirect', '--realise', output])
        return release

    def validate(self, release, rollback=False):
        release = Path(release)
        if release.parent != self.scope.release_root or not re.fullmatch('[0-9a-f]{64}', release.name): raise ValueError('Fixed prepared release required')
        private(self.scope.release_root, True); private(release, True)
        if private(self.scope.release_root / 'manager-version').read_text() != 'native-release-v1\n': raise ValueError('Unknown release manager namespace')
        manifest = private(release / 'manifest.json')
        if digest(manifest) != release.name: raise ValueError('Manifest changed')
        plan = json.loads(manifest.read_text())
        if plan['scope'] != self.scope.name or set(plan['units']) != set(self.scope.units) or set(plan['commands']) != set(self.scope.units): raise ValueError('Release scope changed')
        if plan['state_policy'] != 'reuse-current-state-never-restore-backup': raise ValueError('Wrong rollback policy')
        package, frontend = Path(plan['package']), Path(plan['frontend'])
        if digest(package / 'libexec/tag-server-workspace') != plan['binary_sha256'] or fingerprint(frontend) != plan['frontend_sha256']: raise ValueError('Candidate changed')
        for unit, command in plan['commands'].items():
            expected, _ = replace_command(plan['units'][unit]['command'], package, frontend)
            if command != expected: raise ValueError('Unrelated prepared command argument changed')
            if private(release / unit).read_text() != HEADER + '[Service]\nExecStart=\nExecStart=' + command + '\n': raise ValueError('Prepared unit changed')
            for source in plan['units'][unit]['sources']:
                path = Path(source['path'])
                if rollback and path == self.scope.unit_root / (unit + '.d') / MANAGED: continue
                if digest(path) != source['sha256']: raise ValueError('Existing unit drifted')
        pointer_text = json.dumps({'manifest': release.name, 'package': plan['package'], 'frontend': plan['frontend']}) + '\n'
        if private(release / 'current.json').read_text() != pointer_text: raise ValueError('Prepared version pointer changed')
        if rollback:
            for unit in self.scope.units:
                target = self.scope.unit_root / (unit + '.d') / MANAGED
                keep = lambda rows: [row for row in rows if Path(row['path']) != target]
                if keep(self.unit_input(unit)['sources']) != keep(plan['units'][unit]['sources']): raise ValueError('Unrelated unit input changed')
        else:
            if any(self.unit_input(unit) != plan['units'][unit] for unit in self.scope.units): raise ValueError('Effective service input drifted')
            pointer = self.scope.release_root / 'current.json'
            actual = digest(private(pointer)) if pointer.exists() else None
            if actual != plan['pointer_before']: raise ValueError('Current version changed')
        return plan

    def targets(self):
        targets = {self.scope.unit_root / (unit + '.d') / MANAGED for unit in self.scope.units}
        return targets | {self.scope.release_root / 'current.json'}

    def known_transaction(self, transaction, plan, release):
        journal = transaction.load()
        for name, record in journal['records'].items():
            target = Path(name)
            if target == self.scope.release_root / 'current.json':
                source = release / 'current.json'; before_sha = plan['pointer_before']
            else:
                unit = target.parent.name.removesuffix('.d')
                source = release / unit
                previous = [item['sha256'] for item in plan['units'][unit]['sources'] if Path(item['path']) == target]
                if len(previous) > 1: raise ValueError('Duplicate managed source')
                before_sha = previous[0] if previous else None
            expected_after = {'kind': 'file', 'source': str(source), 'sha256': digest(source)}
            if record['after'] != expected_after: raise ValueError('Transaction replacement changed')
            before = record['before']
            if before_sha is None:
                if before != {'kind': 'absent'}: raise ValueError('Unexpected original managed file')
            else:
                if before.get('kind') != 'file' or before.get('sha256') != before_sha or before.get('mode') != 0o600 or not re.fullmatch('[0-9]+', before.get('saved', '')):
                    raise ValueError('Original file binding changed')
                if digest(private(transaction.directory / 'before' / before['saved'])) != before_sha: raise ValueError('Original bytes changed')
            if target.exists() or target.is_symlink():
                if digest(private(target)) not in (before_sha, expected_after['sha256']): raise ValueError('Managed target drifted')
            elif before_sha is not None: raise ValueError('Original managed file disappeared')
        return journal

    def change(self, release, editors_saved=False, rollback=False, after_start=None, after_install=None):
        if not editors_saved: raise ValueError('Fresh saved-editor confirmation required')
        root = self.scope.release_root
        private(root, True); create_lock(root / 'update.lock')
        with exclusive(root / 'update.lock'):
            plan = self.validate(release, rollback)
            release = Path(release)
            transaction = ConfigurationTransaction(release / 'transaction', self.targets())
            self.tasks_idle()
            if rollback:
                phase = self.known_transaction(transaction, plan, release)['phase']
                if phase not in ('prepared', 'backed-up', 'installing', 'configuration-installed', 'activated', 'rolling-back', 'configuration-restored', 'rollback-failed'): raise ValueError('Release cannot be rolled back from this phase')
            else:
                self.ready()
                if transaction.journal.exists(): raise ValueError('Release transaction already exists; explicitly recover or roll back')
                replacements = {self.scope.unit_root / (unit + '.d') / MANAGED:
                                {'kind': 'file', 'source': str(release / unit), 'sha256': digest(release / unit)} for unit in self.scope.units}
                replacements[root / 'current.json'] = {'kind': 'file', 'source': str(release / 'current.json'), 'sha256': digest(release / 'current.json')}
                for target in replacements:
                    if not target.parent.exists(): target.parent.mkdir(mode=0o700)
                    if target.parent.is_symlink() or target.parent.stat().st_uid != os.getuid() or target.parent.stat().st_mode & 0o022: raise ValueError('Unsafe managed drop-in directory')
                transaction.create(replacements); transaction.verify_before()
            with self.suspend_upholding(plan):
                changed = False
                self.run(['systemctl', '--user', 'stop', *self.scope.units])
                try:
                    with offline_states(self.scope.states, self.stopped):
                        self.tasks_idle()
                        backup = release / ('rollback-backup-' + str(time.time_ns()) if rollback else 'backup')
                        backup.mkdir(mode=0o700)
                        states = [backup_state(state, backup / str(index)) for index, state in enumerate(self.scope.states)]
                        atomic(backup / 'results.json', json.dumps(states, indent=2) + '\n')
                        transaction.phase('backed-up' if not rollback else 'rolling-back')
                        changed = True
                        if not rollback: transaction.phase('installing')
                        transaction.install(rollback=rollback)
                        if rollback: transaction.verify_before()
                        else: transaction.verify_after()
                        if after_install: after_install()
                    self.run(['systemctl', '--user', 'daemon-reload'])
                    self.run(['systemctl', '--user', 'start', *self.scope.units])
                    self.ready(None if rollback else Path(plan['package']))
                    if after_start: after_start()
                    if any((state / 'core.db').stat().st_ino != record['database_inode'] for state, record in zip(self.scope.states, states)):
                        raise ValueError('Current database inode changed')
                    transaction.phase('rolled-back' if rollback else 'activated')
                    return {'phase': 'rolled-back' if rollback else 'activated', 'manifest': release.name, 'backup': str(backup), 'database_restored': False}
                except Exception:
                    self.run(['systemctl', '--user', 'stop', *self.scope.units])
                    self.stopped()
                    if changed:
                        if rollback: transaction.phase('rollback-failed'); raise
                        transaction.install(rollback=True); transaction.verify_before()
                    self.run(['systemctl', '--user', 'daemon-reload'])
                    self.run(['systemctl', '--user', 'start', *self.scope.units])
                    self.ready(); transaction.phase('failed-old-program-restored-current-data')
                    raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=('pc', 'nuc'), required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--prepare', action='store_true'); action.add_argument('--apply'); action.add_argument('--rollback')
    parser.add_argument('--package'); parser.add_argument('--frontend'); parser.add_argument('--editors-saved', action='store_true')
    args = parser.parse_args(); manager = Manager(fixed_scope(args.scope))
    if args.apply or args.rollback:
        result = manager.change(args.apply or args.rollback, args.editors_saved, bool(args.rollback))
    else:
        if not args.package or not args.frontend: parser.error('--package and --frontend required')
        if args.prepare:
            result = {'prepared': str(manager.prepare(args.package, args.frontend)), 'activated': False}
        else:
            plan = manager.plan(args.package, args.frontend)
            result = {'scope': args.scope, 'package': plan['package'], 'frontend': plan['frontend'], 'core_units': list(manager.scope.units), 'processing_idle': True, 'activated': False}
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
