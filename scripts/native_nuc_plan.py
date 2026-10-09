#!/usr/bin/env python3
"""Read-only NUC topology gate. Never include environment, commands or secrets in output."""
import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path

PREFIX = 'dufs-plus_'
REPLACE = ('tag-server', 'tag-server-readonly', 'dufs', 'dufs-readonly', 'tag-peer-discovery')
KEEP = ('caddy', 'authelia', 'readonly-gateway', 'ddns-go')


def make_plan(config, inventory):
    if config['deployment']['name'] != 'dufs-plus' or config['deployment']['profile'] != 'home-ipv6-cdn':
        raise ValueError('Only the explicit home NUC profile is supported')
    if config['runtime']['engine'] != 'podman':
        raise ValueError('NUC gate requires Podman')
    for key in ('readonly', 'authelia', 'terminal', 'tag_peer_pairing', 'tag_peer_discovery'):
        if config['features'].get(key) is not True:
            raise ValueError('NUC capability missing: ' + key)
    records = {}
    for item in inventory:
        name = item['Name'].lstrip('/')
        if name in records:
            raise ValueError('Duplicate inspected container: ' + name)
        records[name] = item
    paths = config['paths']
    expected = {
        'tag-server': [(paths['tag_data'], '/data', True), (paths['workspace'], '/workspace', True),
                       (paths['media'], '/workspace/media', True), (paths['whisper_models'], '/models', False)],
        'tag-server-readonly': [(paths['readonly_tag_data'], '/data', True), (paths['readonly'], '/workspace', False)],
        'dufs': [(paths['workspace'], '/data', True), (paths['media'], '/data/media', True)],
        'dufs-readonly': [(paths['readonly'], '/data', False)],
        'tag-peer-discovery': [(paths['tag_data'], '/data', True)],
        'caddy': [(paths['caddy_data'], '/data/caddy', True), (paths['dist'], '/srv/dist', False)],
    }
    result = []
    for service in REPLACE + KEEP:
        name = PREFIX + service + '_1'
        if name not in records:
            raise ValueError('Missing inspected container: ' + name)
        item = records[name]
        if not item['State']['Running']:
            raise ValueError('Expected running source: ' + name)
        image = item['Image']
        if not re.fullmatch(r'(sha256:)?[a-f0-9]{64}', image):
            raise ValueError('Source image must be a complete ID: ' + name)
        mounts = item.get('Mounts', [])
        destinations = [m['Destination'] for m in mounts]
        if len(set(destinations)) != len(destinations):
            raise ValueError('Duplicate mount target: ' + name)
        for source, destination, writable in expected.get(service, []):
            if not any(m['Source'] == source and m['Destination'] == destination and m['RW'] is writable for m in mounts):
                raise ValueError('Source mount contract differs: ' + name + ' ' + destination)
        if service == 'tag-server-readonly':
            # Metadata is writable; served content and private credentials must stay separate.
            for m in mounts:
                if m['Destination'] == '/root/.ssh' or m['Destination'].startswith('/root/.ssh/'):
                    raise ValueError('Read-only source must not receive writing Git credentials')
                if m['Destination'] == '/workspace' or m['Destination'].startswith('/workspace/'):
                    if m['RW']:
                        raise ValueError('Read-only workspace mount is writable')
        result.append({'name': name, 'image': image, 'action': 'replace' if service in REPLACE else 'retain'})
    return {
        'schema_version': 1, 'target': 'nuc', 'activated': False, 'cutover_ready': False,
        'read_only_plan': True, 'containers': result,
        'instances': [
            {'role': 'private', 'workspace': paths['workspace'], 'source_state': paths['tag_data'],
             'workspace_read_only': False, 'sync': 'preserve', 'models': paths['whisper_models']},
            {'role': 'readonly', 'workspace': paths['readonly'], 'source_state': paths['readonly_tag_data'],
             'workspace_read_only': True, 'sync': 'disabled', 'models': None}],
        'remaining_adaptations': ['dual-instance units and isolated states',
                                 'private Unix bridge and unchanged ingress guards',
                                 'NUC Whisper inference and runtime Git credentials'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, default=Path(__file__).resolve().parents[1] / 'deploy/instances/home.toml')
    parser.add_argument('--inventory', type=Path, help='Offline fixture; otherwise read NUC via verified SSH')
    args = parser.parse_args()
    config = tomllib.loads(args.instance.read_text())
    if args.inventory:
        inventory = json.loads(args.inventory.read_text())
    else:
        names = [PREFIX + service + '_1' for service in REPLACE + KEEP]
        # Fixed remote command, capture entire inspect privately and emit only allowlisted fields.
        completed = subprocess.run(['ssh', '-F', '/home/liou/.ssh/config', 'liou@nuc.local',
                                    'podman inspect ' + ' '.join(names)],
                                   check=True, capture_output=True, text=True, timeout=45)
        inventory = json.loads(completed.stdout)
    print(json.dumps(make_plan(config, inventory), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
