#!/usr/bin/env python3
"""Read-only guard for the fixed PC candidate. Never stop/start services or write state."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess

ROOT = Path('/home/liou/.local/share/tag-all/pc-native')
NAMES = ['dufs-plus-pc_tag-server_1', 'dufs-plus-pc_peer-discovery_1', 'dufs-plus-pc_peer-gateway_1', 'dufs-plus-pc_caddy_1', 'dufs-plus-pc_dufs_1']
UNITS = ['tag-native-stack.target', 'tag-all-core.service', 'tag-native-files.service', 'tag-native-workspace.service']


def private_regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('Expected an owned private regular marker or manifest')


def manifest(root):
    for directory in [root, root / 'config', root / 'data', root / 'certs', root / 'peer-caddy', root / 'peer-caddy/caddy', root / 'peer-caddy/caddy/pki', root / 'peer-caddy/caddy/pki/authorities', root / 'peer-caddy/caddy/pki/authorities/local']:
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('Expected an owned private snapshot directory')
    for name in ['root.crt', 'root.key', 'intermediate.crt', 'intermediate.key']:
        private_regular(root / 'peer-caddy/caddy/pki/authorities/local' / name)
    private_regular(root / 'data/core.db')
    private_regular(root / 'ready')
    if (root / 'ready').read_text() != 'offline-snapshot-complete\n':
        raise ValueError('Snapshot is not complete')
    private_regular(root / 'config/container-rollback.json')
    return json.loads((root / 'config/container-rollback.json').read_text())


def digest(value):
    value = value.removeprefix('sha256:')
    if not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Expected a pinned image digest')
    return value


def validate(mode, root, records, units=None):
    saved = manifest(root)
    if set(records) != set(NAMES):
        raise ValueError('All five fixed PC containers must be inspected')
    for name, record in records.items():
        if record['Name'].lstrip('/') != name or record['Config']['Labels'].get('io.podman.compose.project') != 'dufs-plus-pc':
            raise ValueError('Container identity is outside the fixed PC project')
    marker = root / 'container-mode'
    if mode == 'native':
        if marker.exists() or marker.is_symlink():
            raise ValueError('Container mode blocks native startup')
        if any(record['State']['Running'] for record in records.values()):
            raise ValueError('All fixed source containers must be stopped before native startup')
        return
    private_regular(marker)
    if units is None or set(units) != set(UNITS) or any(status not in {'inactive', 'failed'} for status in units.values()):
        raise ValueError('Native target and all three services must be stopped before container startup')
    for name in NAMES:
        service = name.removeprefix('dufs-plus-pc_').removesuffix('_1')
        record = records[name]
        expected = saved['services'][service]
        if digest(record['Image']) != digest(expected['image']):
            raise ValueError('Container image differs from the offline snapshot')
        mounts = {entry['Destination']: entry['Source'] for entry in record['Mounts'] if entry['Type'] == 'bind'}
        required = {}
        if service in {'tag-server', 'peer-discovery'}: required['/data'] = str(root / 'data')
        if service == 'peer-gateway': required['/data'] = str(root / 'peer-caddy')
        if service in {'tag-server', 'dufs'}:
            required.update({'/workspace': '/home/liou/dufs-lan', '/workspace/project': '/data/project'})
        if service == 'tag-server': required['/etc/tag-server/certs'] = str(root / 'certs')
        if any(mounts.get(target) != source for target, source in required.items()):
            raise ValueError('Container still points to old or unexpected state/workspace')
        if service == 'tag-server' and record['Config']['Cmd'] != expected['command']:
            raise ValueError('Container command differs from the offline rollback command')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['native', 'container'], required=True)
    parser.add_argument('--podman', default='podman')
    parser.add_argument('--systemctl', default='systemctl')
    args = parser.parse_args()
    if socket.gethostname() != 'liu-bigpc' or os.getuid() != 1000:
        raise ValueError('Fixed liu-bigpc user liou only')
    podman = [args.podman, '--remote', '--url', 'unix:///run/user/1000/podman/podman.sock']
    result = subprocess.run([*podman, 'container', 'inspect', *NAMES], capture_output=True, text=True, check=True, timeout=30)
    records = json.loads(result.stdout)
    if len(records) != len(NAMES): raise ValueError('Expected five distinct container records')
    records = {entry['Name'].lstrip('/'): entry for entry in records}
    units = None
    if args.mode == 'container':
        units = {}
        for name in UNITS:
            result = subprocess.run([args.systemctl, '--user', 'is-active', name], capture_output=True, text=True, timeout=15)
            units[name] = result.stdout.strip()
    validate(args.mode, ROOT, records, units)
    print('Fixed PC startup guard passed: ' + args.mode)


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Never print inspect output or potentially private subprocess stderr.
        print('Fixed PC startup guard refused: ' + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=__import__('sys').stderr)
        raise SystemExit(1)
