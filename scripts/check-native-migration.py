#!/usr/bin/env python3
"""Synthetic full-server -> offline snapshot -> native core -> full-server rollback.

Only generated fixtures are touched. This is not a production migration command.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def files(root):
    result = {}
    for p in root.rglob('*'):
        if p.is_symlink():
            raise ValueError('Snapshot refuses symlinks')
        if p.is_file():
            result[p.relative_to(root).as_posix()] = digest(p)
        elif not p.is_dir():
            raise ValueError('Snapshot refuses special files')
    return result


def snapshot(source, destination):
    # Caller has stopped and waited for its owned source process. This helper
    # deliberately has no CLI accepting production state or service names.
    files(source)
    if destination.exists():
        raise ValueError('Snapshot destination must be new')
    destination.mkdir(mode=0o700)
    source_db = source / 'core.db'
    with sqlite3.connect(source_db.as_uri() + '?mode=ro', uri=True) as origin:
        with sqlite3.connect(destination / 'core.db') as target:
            origin.backup(target)
            assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    if (source / 'metadata').exists():
        shutil.copytree(source / 'metadata', destination / 'metadata')
    for p in destination.rglob('*'):
        p.chmod(0o700 if p.is_dir() else 0o600)
    return files(destination)


def export_full(evidence, destination):
    archive = Path(evidence['image_output'])
    assert digest(archive) == evidence['archive_sha256'], 'Full candidate archive changed'
    contents = None
    with tarfile.open(archive) as image:
        manifests = json.load(image.extractfile('manifest.json'))
        assert len(manifests) == 1
        for name in manifests[0]['Layers']:
            with tarfile.open(fileobj=io.BytesIO(image.extractfile(name).read())) as layer:
                for member in layer:
                    if member.name.removeprefix('./') == 'app/tag-server':
                        assert member.isfile(), 'Full server must be regular bytes'
                        contents = layer.extractfile(member).read()
    assert contents is not None
    expected = evidence['artifacts']['app/tag-server']['sha256']
    assert hashlib.sha256(contents).hexdigest() == expected
    destination.write_bytes(contents)
    destination.chmod(0o700)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag_all', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError('Non-root host required')
    tag = args.tag_all.resolve()
    native = json.loads((tag / '.devenv/native-core-results.json').read_text())
    full = json.loads((tag / '.devenv/nix-private-report.json').read_text())
    assert native['native_http_gate'] and full['full_isolated_probe']
    native_bin = Path(native['package']) / 'libexec/tag-server-core'
    assert digest(native_bin) == native['binary_sha256']
    parent = ROOT / '.devenv'
    parent.mkdir(exist_ok=True)
    output = parent / 'native-migration-results.json'
    output.unlink(missing_ok=True)
    processes = []
    with tempfile.TemporaryDirectory(prefix='native-migration-', dir=parent) as folder:
        root = Path(folder)
        workspace = root / 'workspace'; workspace.mkdir()
        original = workspace / 'note.md'; original.write_text('original workspace content')
        full_bin = root / 'full-server'
        full_sha = export_full(full, full_bin)
        node_id = 'migration-' + uuid.uuid4().hex
        config = root / 'node.toml'
        config.write_text('[node]\nid = ' + json.dumps(node_id) + '\nname = "Migration Gate"\n'
            + '[[locations]]\nid = "loc_migration"\nnode_id = ' + json.dumps(node_id)
            + '\nname = "Migration Workspace"\npath = ' + json.dumps(str(workspace)) + '\nwritable = true\n')
        source = root / 'full-state'; source.mkdir(mode=0o700)
        metadata = source / 'metadata'; metadata.mkdir(mode=0o700)
        identity = metadata / 'peer-identity.pk8'
        identity.write_bytes(b'opaque existing identity; pairing disabled')
        identity.chmod(0o600)
        pending = metadata / 'disabled-fixture/pending.json'
        pending.parent.mkdir(mode=0o700)
        pending.write_text('{"state":"queued","fixture":true}')
        meta_before = files(metadata)

        def start(binary, state, native_mode=False):
            server_port = port()
            command = [str(binary)]
            if native_mode:
                command += ['--state-dir', str(state)]
            else:
                command += ['--database', str(state / 'core.db'), '--metadata-dir', str(state / 'metadata'), '--disable-sync']
            command += ['--workspace', str(workspace), '--config', str(config), '--addr', f'127.0.0.1:{server_port}']
            with (root / ('server-' + str(server_port) + '.log')).open('wb') as log:
                proc = subprocess.Popen(command, stdout=log, stderr=log)
            processes.append(proc)
            base = f'http://127.0.0.1:{server_port}'

            def request(path, body=None):
                req = urllib.request.Request(base + path, None if body is None else json.dumps(body).encode(),
                                             {'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=3) as res:
                    data = res.read()
                    return json.loads(data) if data else None
            for _ in range(120):
                if proc.poll() is not None:
                    raise RuntimeError('Owned synthetic process exited before ready')
                try:
                    target = request('/v1/locations/loc_migration/capabilities')
                    assert target['node_id'] == node_id
                    return proc, request
                except OSError:
                    time.sleep(.05)
            raise RuntimeError('Owned synthetic process failed readiness')

        def stop(proc):
            proc.terminate()
            assert proc.wait(timeout=15) == 0

        try:
            proc, req = start(full_bin, source)
            tag_created = req('/tags', {'name': 'full-before'})
            req('/tag/set', {'path': 'https://example.invalid/migration', 'text': 'Synthetic saved web',
                            'tag_ids': [tag_created['id']], 'location_id': 'loc_migration'})
            req('/tag/set', {'path': '/note.md', 'tag_ids': [tag_created['id']], 'location_id': 'loc_migration'})
            stop(proc)  # offline database AND metadata; no live filesystem copy
            backup = root / 'backup'
            backup_manifest = snapshot(source, backup)
            source_manifest = files(source)
            migrated = root / 'native-state'
            snapshot(backup, migrated)
            proc, req = start(Path(native['package']) / 'bin/tag-all-core', migrated, True)
            assert 'full-before' in json.dumps(req('/tags'))
            items = json.dumps(req('/items?path=&sparse=true'))
            assert 'https://example.invalid/migration' in items and 'note.md' in items
            req('/tags', {'name': 'native-after'})
            assert req('/v1/capabilities')['capabilities']['pdf']['compiled'] is False
            # Native lock rejects an additional writer, even on another port.
            duplicate = subprocess.run([str(Path(native['package']) / 'bin/tag-all-core'),
                '--state-dir', str(migrated), '--workspace', str(workspace), '--config', str(config),
                '--addr', f'127.0.0.1:{port()}'], capture_output=True, timeout=5)
            assert duplicate.returncode == 73
            stop(proc)
            assert files(migrated / 'metadata') == meta_before
            # Binary rollback keeps native-period data; never restore old DB by default.
            proc, req = start(full_bin, migrated)
            tags = json.dumps(req('/tags'))
            assert 'full-before' in tags and 'native-after' in tags
            items = json.dumps(req('/items?path=&sparse=true'))
            assert 'https://example.invalid/migration' in items and 'note.md' in items
            stop(proc)
            # Explicit pre-cutover recovery is checked separately, in a NEW directory.
            recovered = root / 'recovered'
            snapshot(backup, recovered)
            proc, req = start(full_bin, recovered)
            tags = json.dumps(req('/tags'))
            assert 'full-before' in tags and 'native-after' not in tags
            stop(proc)
            assert files(source) == source_manifest and files(backup) == backup_manifest
            assert original.read_text() == 'original workspace content'
            assert files(recovered / 'metadata') == meta_before
            symlink_state = root / 'bad-state'; symlink_state.mkdir()
            (symlink_state / 'metadata').symlink_to(metadata, target_is_directory=True)
            try:
                snapshot(symlink_state, root / 'rejected')
            except ValueError:
                pass
            else:
                raise AssertionError('Symlink snapshot should be rejected')
            assert not (root / 'rejected').exists()
            results = {'full_binary_sha256': full_sha, 'full_archive_sha256': full['archive_sha256'],
                'native_binary_sha256': native['binary_sha256'], 'offline_sqlite_backup_integrity': True,
                'native_reads_full_database': True, 'explicit_location_saved_web_and_file_tags_preserved': True,
                'native_duplicate_writer_rejected': True,
                'full_binary_rollback_keeps_native_writes': True, 'explicit_backup_recovery_in_new_directory': True,
                'opaque_identity_and_disabled_fixture_preserved': True, 'source_backup_workspace_unchanged': True,
                'symlink_rejected_before_destination_created': True, 'production_migration': False,
                'active_pairing_sync_tested': False, 'real_task_recovery_tested': False}
        finally:
            for p in processes:
                if p.poll() is None:
                    p.terminate()
                    try: p.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        p.kill(); p.wait(timeout=5)
            assert all(p.poll() is not None for p in processes)
    results['owned_cleanup'] = True
    output.write_text(json.dumps(results, indent=2) + '\n')
    print('Synthetic offline native migration and full-server rollback passed: ' + str(output))


if __name__ == '__main__':
    main()
