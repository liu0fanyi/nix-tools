#!/usr/bin/env python3
"""Fixed PC offline preparation; only a user-run --prepare-offline reads/copies state. No stop/switch."""
import argparse
import json
from pathlib import Path
import socket
import importlib.util
import os
import subprocess
from native_pc_snapshot import offline_snapshot

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = Path('/home/liou/.local/share/tag-all/pc-native')
NAMES = ['dufs-plus-pc_tag-server_1', 'dufs-plus-pc_peer-discovery_1', 'dufs-plus-pc_peer-gateway_1', 'dufs-plus-pc_caddy_1', 'dufs-plus-pc_dufs_1']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-offline', action='store_true', help='User-run only after all five source services and their boot restore are stopped')
    args = parser.parse_args()
    if not args.prepare_offline:
        print('Plan only. Complete S2/S3 first. Never run offline preparation against live services.')
        print('Destination: ' + str(DESTINATION))
        print('No stop, switch, source state read or copy performed.')
        return
    if socket.gethostname() != 'liu-bigpc' or os.getuid() != 1000:
        raise ValueError('Fixed liu-bigpc liou user only')
    spec = importlib.util.spec_from_file_location('native_preflight', ROOT / 'scripts/plan-native-pc.py')
    preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
    def ensure_offline():
        records = {name: preflight.inspect(name) for name in NAMES}
        if any(record['State']['Running'] for record in records.values()):
            raise ValueError('All five fixed PC source containers must be stopped before state access')
        restore = subprocess.run(['systemctl', '--user', 'is-active', 'pc-private-node-restore.service'], capture_output=True, text=True)
        if restore.stdout.strip() != 'inactive':
            raise ValueError('Stop the fixed PC boot restore unit before offline preparation')
        return records
    containers = ensure_offline()
    server = containers[NAMES[0]]
    mounts = {entry['Destination']: entry['Source'] for entry in server['Mounts'] if entry['Type'] == 'bind'}
    if mounts.get('/data') != '/home/liou/.local/share/tag-all/pc/data' or mounts.get('/workspace') != '/home/liou/dufs-lan':
        raise ValueError('Fixed source mount layout changed; rerun preflight')
    pki = {entry['Destination']: entry['Source'] for entry in containers[NAMES[2]]['Mounts'] if entry['Type'] == 'bind'}
    if pki.get('/data') != '/home/liou/.local/share/tag-all/pc/peer-caddy':
        raise ValueError('Fixed peer storage changed')
    caddy = {entry['Destination']: entry['Source'] for entry in containers[NAMES[3]]['Mounts'] if entry['Type'] == 'bind'}
    # This fixed PC candidate preserves the current anonymous local entry.
    # Refuse DUFS credentials rather than silently discarding existing auth.
    dufs_args = containers[NAMES[4]]['Config']['Cmd']
    if any(arg in {'-a', '--auth'} or arg.startswith('--auth=') or arg.startswith('-a=') for arg in dufs_args):
        raise ValueError('Existing DUFS authentication requires an authenticated candidate')
    result = offline_snapshot(DESTINATION, mounts, mounts['/etc/tag-server/tag-server.toml'],
        containers[NAMES[1]]['Config']['Cmd'], caddy['/etc/caddy/Caddyfile'],
        '/home/liou/.local/share/tag-all/pc/peer-admin.env', Path(pki['/data']) / 'caddy',
        server['Config']['Cmd'], 'sha256:' + server['Image'].removeprefix('sha256:'), ensure_offline=ensure_offline,
        source_images={name.removeprefix('dufs-plus-pc_').removesuffix('_1'): 'sha256:' + record['Image'].removeprefix('sha256:') for name, record in containers.items()}, local_authentication='loopback')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
