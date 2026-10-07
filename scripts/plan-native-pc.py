#!/usr/bin/env python3
"""Read-only PC native cutover preflight; never stop, copy state or activate."""
import argparse
import json
import os
from native_pc_config import adapt_configuration
from pathlib import Path
import subprocess
import tomllib


def inspect(name):
    connection = os.environ.get('TAG_PODMAN_URL')
    command = ['podman']
    if connection:
        if connection != f'unix:///run/user/{os.getuid()}/podman/podman.sock':
            raise ValueError('Only the current user local Podman socket is allowed')
        command += ['--remote', '--url', connection]
    result = subprocess.run([*command, 'container', 'inspect', name], text=True,
                            capture_output=True, check=True, timeout=15)
    records = json.loads(result.stdout)
    if len(records) != 1:
        raise ValueError('Expected exactly one PC container')
    record = records[0]
    if record['Config']['Labels'].get('io.podman.compose.project') != 'dufs-plus-pc':
        raise ValueError('Container is outside fixed PC project')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # deliberately no --apply / arbitrary command option
    server = inspect('dufs-plus-pc_tag-server_1')
    mounts = {m['Destination']: m['Source'] for m in server['Mounts'] if m['Type'] == 'bind'}
    config = tomllib.loads(Path(mounts['/etc/tag-server/tag-server.toml']).read_text())
    agent = inspect('dufs-plus-pc_peer-discovery_1')
    candidate, layout = adapt_configuration(config, mounts, agent['Config']['Cmd'])
    peers = config.get('sync', {}).get('peers', [])
    pairing = config.get('pairing', {}).get('enabled', False)
    discovery = config.get('discovery', {}).get('enabled', False)
    nested = [path for path in mounts if path.startswith('/workspace/')]
    reasons = []
    if server['State']['Running']:
        reasons.append('Source writer is active; offline DB/metadata snapshot is not permitted yet.')
    reasons.extend([
        'Current host full configuration and Home Manager generation build is still required.',
        'Reviewed cutover must include an offline private CA-storage snapshot; never share live writable storage.',
        'Real LAN discovery observation remains an activation gate; temporary tests never broadcast.',
        'Existing PC boot restore must be disabled in the reviewed cutover configuration.',
        'Complete tools/fallback compatibility must be confirmed before replacing the current full service.',
    ])
    # No environment, auth material, peer URL, database content or key bytes are output.
    result = {'mode': 'read-only-preflight', 'source_container': server['Name'].lstrip('/'),
        'source_image_id': server['Image'], 'source_running': server['State']['Running'],
        'data_root': mounts.get('/data'), 'workspace': mounts.get('/workspace'),
        'nested_workspace_targets': nested, 'configured_location_count': len(config.get('locations', [])),
        'configured_peer_count': len(peers), 'pairing_enabled': pairing, 'discovery_enabled': discovery,
        'proposed_gateway': 'http://127.0.0.1:18006', 'proposed_core': '127.0.0.1:18081',
        'native_config_adaptation': {
            'source_unchanged': True, 'identity_and_peers_preserved': candidate['node'] == config['node'] and candidate.get('sync') == config.get('sync'),
            'translated_location_paths': [loc['path'] for loc in candidate.get('locations', [])],
            'translated_ca_paths': candidate.get('pairing', {}).get('trusted_ca_files', []),
            'workspace_mounts': layout['workspace_mounts'],
            'discovery_mode': 'built-in' if discovery else 'disabled',
            'discovery_interfaces': candidate.get('discovery', {}).get('interfaces', []),
            'candidate_config_written': False},
        'proposed_native_sync_enabled': bool(peers), 'cutover_ready': not reasons, 'blocking_reasons': reasons,
        'database_or_key_contents_read': False, 'writes_or_stops_performed': False,
        'next_steps': ['Keep current containers as the active node.',
            'Resolve topology, location IDs, CA and nested mounts before planning activation.',
            'Stop the explicitly selected writer, back up SQLite consistently and metadata offline.',
            'Use new private state; verify before selecting the browser entry.',
            'On failure restore old service entry; never overwrite DB automatically.']}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
