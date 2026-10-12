#!/usr/bin/env python3
"""Actual old/new native program updates over a synthetic database and owned user unit."""
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import uuid

ROOT = Path('/data/project/tag-all')
MANAGER_PACKAGE = Path(sys.argv[1]).resolve()
manager_dir = MANAGER_PACKAGE / 'libexec'
sys.path.insert(0, str(manager_dir))
from native_application_release import Scope, Manager, HEADER, MANAGED

old = Path('/nix/store/ilqv015pfdi113q9h24qxbkmsyila265-tag-all-workspace-native-0.1.0')
packaging = json.loads((ROOT / '.devenv/application-module-release-package-results.json').read_text())
new = Path(packaging['package'])
old_front = Path('/nix/store/09q39kfr4xv8p3k7i37gxw549ggksmx9-dufs-plus-native-frontend')
new_front = (ROOT / '.devenv/application-module-release-frontend').resolve()
unit_root = Path('/home/liou/.config/systemd/user')
owner = uuid.uuid4().hex
unit = 'tag-release-030-fixture-' + owner + '.service'
tools_unit = 'tag-release-030-tools-' + owner + '.service'
target = 'tag-release-030-upholds-' + owner + '.target'
target_link = unit_root / target
assert not target_link.exists() and not target_link.is_symlink()
link = unit_root / unit
assert not (link.exists() or link.is_symlink())
owned_dir = unit_root / (unit + '.d')
assert not owned_dir.exists()
cases = []
cleanup = False

with tempfile.TemporaryDirectory(prefix='native-release-fixture-', dir=ROOT / '.devenv') as temporary:
    root = Path(temporary); root.chmod(0o700)
    state = root / 'state'; workspace = root / 'workspace'; runtime = root / 'runtime'
    for folder in (workspace, runtime): folder.mkdir(mode=0o700)
    config = root / 'node.toml'
    config.write_text('[node]\nid="release-fixture-' + owner + '"\n[discovery]\nenabled=false\n'); config.chmod(0o600)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
    entry = root / 'entry.toml'
    entry.write_text('peer_socket=' + json.dumps(str(runtime / 'peer.sock')) + '\npeer_authorities=["localhost:18009"]\n'); entry.chmod(0o600)
    argv = [str(old / 'bin/tag-all-core'), '--state-dir', str(state), '--workspace', str(workspace),
            '--config', str(config), '--sync-mode', 'isolated', '--addr', '127.0.0.1:' + str(port),
            '--workspace-entry-frontend', str(old_front), '--workspace-entry-dufs-socket', str(runtime / 'files.sock'),
            '--workspace-entry-read-only', 'false', '--workspace-entry-config', str(entry)]
    connection = 'unix://' + str(root / 'tools/runtime.sock')
    environment = []
    for kind in ('PDF', 'ARCHIVE', 'AUDIO_VIDEO', 'EPUB'):
        environment.extend(['Environment=TAG_NATIVE_' + kind + '_IMAGE=' + packaging['image_id'],
                            'Environment=TAG_NATIVE_' + kind + '_STATE=' + str(root / ('executor-' + kind.lower())),
                            'Environment=TAG_NATIVE_' + kind + '_CONNECTION=' + connection])
    source = root / 'fixture.service'
    source.write_text('[Unit]\nDescription=Owned native release fixture\n[Service]\nType=simple\nRestart=no\nUMask=0077\nEnvironment=RUST_BACKTRACE=1\nEnvironment=DUFS_WHISPER_CLI=/missing-fixture-cli DUFS_WHISPER_MODEL=/missing-fixture-model DUFS_FFMPEG=/missing-fixture-ffmpeg\nExecStart=' + shlex.join(argv) + '\n')
    source.write_text(source.read_text().replace('ExecStart=', '\n'.join(environment) + '\nExecStart=', 1))
    source.chmod(0o600)
    target_source = root / 'fixture.target'
    target_source.write_text('[Unit]\nDescription=Owned actual uphold fixture\nWants=' + unit + '\nUpholds=' + unit + '\n')
    target_source.chmod(0o600)
    scope = Scope('fixture', (unit,), (state,), (connection,), ((port, '/tag-api/tags', 200),), root / 'releases', unit_root, target)
    manager = Manager(scope)

    def api(name=None):
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
        try:
            if name:
                connection.request('POST', '/tag-api/tags', body=json.dumps({'name': name}), headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:' + str(port)})
            else: connection.request('GET', '/tag-api/tags')
            response = connection.getresponse(); body = response.read()
            assert response.status == (201 if name else 200), (response.status, body[:100])
            return body
        finally: connection.close()

    files = None
    try:
        files = subprocess.Popen(['/nix/store/ph17xq80q9by2vmivfvm97a1729q4cgl-dufs-0.46.0/bin/dufs',
                                  str(workspace), '--bind', str(runtime / 'files.sock'), '--allow-all'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time
        deadline = time.monotonic() + 10
        while not (runtime / 'files.sock').is_socket():
            assert files.poll() is None and time.monotonic() < deadline
            time.sleep(.05)
        link.symlink_to(source)
        target_link.symlink_to(target_source)
        manager.run(['systemctl', '--user', 'daemon-reload'])
        manager.run(['systemd-run', '--user', '--collect', '--unit=' + tools_unit,
                     '--property=Type=notify', '--property=NotifyAccess=main', '--property=TimeoutStartSec=180',
                     '--property=UMask=0077', str(new / 'libexec/tag-tools-runtime'),
                     '--state', str(root / 'tools'), '--workspace', str(workspace),
                     '--archive', packaging['tool_archive'], '--archive-sha256', packaging['archive_sha256'],
                     '--image', packaging['image_id']])
        manager.run(['systemctl', '--user', 'start', target]); manager.ready(old)
        api('before-update')
        inode = (state / 'core.db').stat().st_ino
        release = manager.prepare(new, new_front)
        original = manager.unit_input(unit)
        try: manager.change(release)
        except ValueError: pass
        else: raise AssertionError('Missing fresh editor confirmation was accepted')
        assert manager.unit_input(unit) == original
        cases.append('fresh_editor_confirmation_required_before_mutation')

        manager.change(release, editors_saved=True)
        manager.ready(new); api('written-by-new-version')
        manager.change(release, editors_saved=True, rollback=True)
        manager.ready(old)
        assert b'written-by-new-version' in api() and (state / 'core.db').stat().st_ino == inode
        cases.append('real_update_and_explicit_rollback_keep_new_database_writes_and_inode')

        release = manager.prepare(new, new_front)
        def fail_after_write():
            api('retained-after-failure')
            raise RuntimeError('Owned simulated post-start failure')
        try: manager.change(release, editors_saved=True, after_start=fail_after_write)
        except RuntimeError: pass
        else: raise AssertionError('Injected failure was ignored')
        manager.ready(old)
        assert b'retained-after-failure' in api() and (state / 'core.db').stat().st_ino == inode
        cases.append('post_start_failure_restores_old_program_and_keeps_current_data')

        release = manager.prepare(new, new_front)
        interrupted = root / 'interrupt.py'
        interrupted.write_text('import os,signal,sys\nfrom pathlib import Path\nsys.path.insert(0,' + repr(str(manager_dir)) + ')\nfrom native_application_release import Scope,Manager\ns=Scope("fixture",(' + repr(unit) + ',),(Path(' + repr(str(state)) + '),),(),((' + str(port) + ',"/tag-api/tags",200),),Path(' + repr(str(scope.release_root)) + '),Path(' + repr(str(unit_root)) + '),' + repr(target) + ')\nManager(s).change(Path(' + repr(str(release)) + '),editors_saved=True,after_install=lambda:os.kill(os.getpid(),signal.SIGKILL))\n')
        result = subprocess.run([sys.executable, str(interrupted)], capture_output=True)
        assert result.returncode == -signal.SIGKILL, result.stderr[-500:]
        manager.stopped()
        manager.change(release, editors_saved=True, rollback=True)
        manager.ready(old)
        assert b'written-by-new-version' in api() and b'retained-after-failure' in api()
        assert (state / 'core.db').stat().st_ino == inode
        cases.append('controller_sigkill_after_install_recovers_old_program_without_state_restore')

        release = manager.prepare(new, new_front)
        extra = owned_dir / '95-unrelated.conf'
        owned_dir.mkdir(mode=0o700, exist_ok=True); extra.write_text('[Service]\nTimeoutStopSec=31\n'); extra.chmod(0o600)
        try: manager.change(release, editors_saved=True)
        except ValueError: pass
        else: raise AssertionError('Configuration drift was accepted')
        assert manager.properties(unit)['ActiveState'] == 'active'
        extra.unlink()
        cases.append('unrelated_unit_drift_refused_before_stop')

        jobs = state / 'metadata/transcriptions/jobs'
        jobs.mkdir(parents=True, mode=0o700, exist_ok=True)
        active = jobs / 'owned-active.json'; active.write_text('{"status":"queued"}'); active.chmod(0o600)
        try: manager.prepare(new, new_front)
        except ValueError: pass
        else: raise AssertionError('Active processing queue was accepted')
        active.unlink()
        assert manager.properties(unit)['ActiveState'] == 'active'
        cases.append('active_queue_refused_without_stopping_current_service')
    finally:
        manager.run(['systemctl', '--user', 'stop', target])
        assert target_link.is_symlink() and target_link.resolve() == target_source
        target_link.unlink()
        manager.run(['systemctl', '--user', 'stop', unit])
        assert link.is_symlink() and link.resolve() == source
        link.unlink()
        if owned_dir.exists():
            owned_files = list(owned_dir.iterdir()); assert all((p.name == MANAGED and p.read_text().startswith(HEADER)) or (p.name == '95-unrelated.conf' and p.read_text() == '[Service]\nTimeoutStopSec=31\n') for p in owned_files)
            for path in owned_files: path.unlink()
            owned_dir.rmdir()
        manager.run(['systemctl', '--user', 'daemon-reload'])
        assert manager.properties(unit)['ActiveState'] in ('inactive', 'failed')
        subprocess.run(['systemctl', '--user', 'stop', tools_unit], check=False, capture_output=True)
        status = subprocess.run(['systemctl', '--user', 'is-active', tools_unit], check=False, capture_output=True, text=True).stdout.strip()
        assert status not in ('active', 'activating', 'deactivating')
        storage = root / 'tools/storage'
        if storage.exists():
            subprocess.run(['podman', '--remote=false', '--root', str(storage), '--runroot', str(root / 'tools/run'),
                            '--storage-driver=vfs', '--tmpdir', str(root / 'tools/libpod'), 'unshare', sys.executable, '-c',
                            'import shutil,sys;shutil.rmtree(sys.argv[1])', str(storage)], check=True, capture_output=True)
        if files is not None and files.poll() is None:
            files.terminate(); files.wait(timeout=10)
        cleanup = True

result = {'cases': cases, 'actual_old_and_new_packaged_programs': True, 'actual_owned_user_unit': True, 'actual_upholds_target_and_interrupted_recovery': True,
          'latest_writes_retained_on_rollback': True, 'database_inode_preserved': True,
          'owned_units_and_files_cleaned': cleanup, 'production_access': False, 'production_activated': False,
          'manager_package': str(MANAGER_PACKAGE), 'old_package': str(old), 'new_package': str(new)}
(ROOT / '.devenv/native-version-update-runtime-results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
