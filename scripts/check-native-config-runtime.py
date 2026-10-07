#!/usr/bin/env python3
"""Adapted synthetic configuration reaches actual core; invalid discovery fails before broadcast."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import tomllib
import urllib.request
from native_pc_config import adapt_configuration, serialize_configuration

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag_all', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0: raise RuntimeError('Owned non-root fixtures only')
    package = json.loads((args.tag_all / '.devenv/native-core-results.json').read_text())['package']
    output = ROOT / '.devenv/native-config-runtime-results.json'
    output.unlink(missing_ok=True)
    proc = None
    with tempfile.TemporaryDirectory(prefix='config-', dir=ROOT / '.devenv') as directory:
        root = Path(directory)
        workspace = root / '中文 space'; workspace.mkdir()
        certs = root / 'certs'; certs.mkdir()
        config = {'node': {'id': 'fixture-config', 'name': '中文 PC'},
                  'locations': [{'id': 'loc_fixture', 'node_id': 'fixture-config', 'name': '目录', 'path': '/workspace', 'writable': True}],
                  'sync': {'enabled': True, 'auto_broadcast': False, 'peers': [], 'poll_interval_secs': 0},
                  'pairing': {'enabled': True, 'trusted_ca_files': []},
                  'discovery': {'enabled': True, 'external_agent': True, 'advertise_url': 'https://fixture.invalid:5009'},
                  'unknown': {'nested': [{'quoted': 'a"\\b\n中文', 'empty': []}]}}
        args_discovery = ['--node-id', 'fixture-config', '--metadata-dir', '/data/metadata', '--advertise-url', 'https://fixture.invalid:5009', '--advertise-ip', '192.168.1.100', '--interface', 'fixture_missing_interface']
        adapted, layout = adapt_configuration(config, {'/workspace': str(workspace), '/etc/tag-server/certs': str(certs)}, args_discovery)
        assert tomllib.loads(serialize_configuration(adapted)) == adapted
        # Positive core startup uses the already-supported external-candidate mode: no mDNS.
        safe = tomllib.loads(serialize_configuration(adapted))
        safe['discovery']['external_agent'] = True
        path = root / 'node.toml'; path.write_text(serialize_configuration(safe)); path.chmod(0o600)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        command = [package + '/bin/tag-all-core', '--state-dir', str(root / 'state'), '--workspace', layout['workspace'], '--config', str(path), '--sync-mode', 'configured', '--addr', f'127.0.0.1:{port}']
        try:
            environment = os.environ.copy(); environment['TAG_PEER_ADMIN_TOKEN'] = 'synthetic-config-only-32-characters-minimum'
            with (root / 'log').open('wb') as log: proc = subprocess.Popen(command, env=environment, stdout=log, stderr=log)
            for _ in range(100):
                if proc.poll() is not None: raise RuntimeError('Owned configured core failed readiness: ' + (root / 'log').read_text()[-2000:])
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/locations/loc_fixture/capabilities', timeout=2) as response:
                        payload = json.load(response)
                    assert payload['node_id'] == 'fixture-config'; break
                except OSError: time.sleep(.05)
            else: raise AssertionError('Owned core readiness timeout')
            proc.terminate(); assert proc.wait(timeout=10) == 0; proc = None
            path.write_text(serialize_configuration(adapted))
            rejected = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
            assert rejected.returncode != 0
            assert 'Discovery advertise_ip must belong to an allowed host interface' in rejected.stderr
            # That check precedes ServiceDaemon creation in the pinned core implementation.
            report = {'toml_roundtrip_preserves_unknown_fields': True, 'adapted_location_identity_actual_core_startup': True,
                      'invalid_builtin_discovery_rejected_before_daemon': True, 'positive_builtin_broadcast_tested': False,
                      'production_state_read': False, 'activated': False}
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate(); proc.wait(timeout=10)
    report['owned_process_and_fixture_cleaned'] = True
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Adapted TOML roundtrip, actual configured core and no-broadcast discovery negative gate passed')


if __name__ == '__main__': main()
