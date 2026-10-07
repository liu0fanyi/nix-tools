#!/usr/bin/env python3
"""Reuse the product's real signed peers through two actual generated Caddy gateways."""
import argparse
import base64
import secrets
import importlib.util
import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag_all', type=Path)
    parser.add_argument('dufs_plus', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError('Non-root owned peer tests required')
    output = ROOT / '.devenv/native-peer-gateway-results.json'
    output.unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location('native_peers', args.tag_all / 'scripts/check-native-peers.py')
    peers = importlib.util.module_from_spec(spec); spec.loader.exec_module(peers)
    processes = []; configs = []; checks = []
    with tempfile.TemporaryDirectory(prefix='peer-gateway-', dir=ROOT / '.devenv') as directory:
        state = Path(directory)
        def proxy(name, node, certificates):
            peer_port = port()
            for file in ['tls.pem', 'tls.key']: (certificates / file).chmod(0o600)
            private = state / name; private.mkdir(mode=0o700)
            auth = private / 'auth.entries'
            caddy = json.loads((ROOT / 'specs/012-native-core-gateway/results.json').read_text())['caddy_package'] + '/bin/caddy'
            password = secrets.token_urlsafe(32)
            hashed = subprocess.run([caddy, 'hash-password', '--algorithm', 'bcrypt', '--bcrypt-cost', '10'],
                input=password + '\n', text=True, capture_output=True, check=True, timeout=30).stdout.strip()
            auth.write_text('fixture ' + hashed + '\n'); auth.chmod(0o600)
            params = {'authFile': str(auth), 'fileSocket': str(private / 'files.sock'),
                'gatewayPort': port(), 'corePort': node['core_port'], 'peer': {
                'serverName': 'localhost', 'listenAddress': '127.0.0.1', 'port': peer_port,
                'allowedNetworks': ['127.0.0.1/32'], 'certificateFile': str(certificates / 'tls.pem'),
                'privateKeyFile': str(certificates / 'tls.key')}}
            settings = private / 'settings.json'; settings.write_text(json.dumps(params))
            expression = 'import ' + str(ROOT / 'tests/native-peer-gateway.nix') + ' { infrastructure = ' + json.dumps(str(ROOT))
            expression += '; tagAll = ' + json.dumps(str(args.tag_all.resolve())) + '; dufsPlus = ' + json.dumps(str(args.dufs_plus.resolve()))
            expression += '; settings = ' + json.dumps(str(settings)) + '; }'
            result = subprocess.run(['nix-build', '--no-out-link', '-A', 'config', '--expr', expression],
                check=True, capture_output=True, text=True, timeout=300)
            config = Path(result.stdout.strip()); configs.append(str(config))
            caddy = json.loads((ROOT / 'specs/012-native-core-gateway/results.json').read_text())['caddy_package'] + '/bin/caddy'
            environment = os.environ.copy(); environment.update(TAG_PEER_ADMIN_TOKEN=node['token'], XDG_CONFIG_HOME=str(private / 'config'), XDG_DATA_HOME=str(private / 'data'))
            with (private / 'caddy.log').open('wb') as log:
                proc = subprocess.Popen([caddy, 'run', '--config', str(config), '--adapter', 'caddyfile'],
                    env=environment, stdout=log, stderr=log)
            processes.append(proc)
            base = f'https://localhost:{peer_port}'
            context = ssl.create_default_context(cafile=str(certificates / 'ca.pem'))
            def status(path, headers=None):
                request = urllib.request.Request(base + path, headers=headers or {})
                try:
                    with urllib.request.urlopen(request, context=context, timeout=3) as response:
                        return response.status, response.read()
                except urllib.error.HTTPError as error: return error.code, b''
            last = 'not connected'
            for _ in range(100):
                if proc.poll() is not None: raise RuntimeError('Owned Caddy peer gateway exited')
                try:
                    code, raw = status('/tag-api/v1/peers/identity'); last = str(code)
                    if code == 200:
                        assert json.loads(raw)['node_id'] == node['node']; break
                except OSError as error: last = type(error).__name__ + ': ' + str(error)
                time.sleep(.05)
            else: raise RuntimeError('Owned Caddy peer readiness failed: ' + last + '\n' + (private / 'caddy.log').read_text()[-2500:])
            browser = 'http://127.0.0.1:' + str(params['gatewayPort'])
            try:
                urllib.request.urlopen(browser + '/tag-api/v1/peers/candidates', timeout=3)
                raise AssertionError('Anonymous browser management must be rejected')
            except urllib.error.HTTPError as error: assert error.code == 401
            authorized = 'Basic ' + base64.b64encode(('fixture:' + password).encode()).decode()
            req = urllib.request.Request(browser + '/tag-api/v1/peers/candidates', headers={'Authorization': authorized})
            with urllib.request.urlopen(req, timeout=3) as response: assert response.status == 200
            assert status('/tag-api/v1/sync/changes')[0] == 401
            assert status('/tag-api/v1/sync/changes', {'x-tag-admin-token': node['token']})[0] == 401
            denied = http.client.HTTPSConnection('localhost', peer_port, context=context,
                source_address=('127.0.0.2', 0), timeout=3)
            try:
                denied.request('GET', '/tag-api/v1/peers/identity')
                response = denied.getresponse(); assert response.status == 404; response.read()
            finally: denied.close()
            for path in ['/', '/tags', '/tag-api/tags', '/tag-api/v1/peers/approvals', '/device-api/v1/session',
                         '/tag-api/v1/peers/web/requests', '/tag-api/v1/peers/requests']:
                assert status(path, {'x-tag-admin-token': node['token'], 'x-dufs-device-api': '1'})[0] == 404
            checks.append(name)
            return base
        try:
            peers.main(proxy_factory=proxy, result_path=state / 'peer-results.json', exercise_requests=True)
            report = json.loads((state / 'peer-results.json').read_text())
            assert len(checks) == 2 and all(proc.poll() is None for proc in processes)
            report.update(actual_caddy_peer_gateway_tested=True, generated_gateway_configs=configs,
                peer_route_allowlist_and_admin_exclusion=True, authenticated_browser_management=True, unsigned_sync_over_https_rejected=True,
                default_peer_entry_disabled=True, real_discovery_broadcast=False)
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
            assert all(proc.poll() is not None for proc in processes)
    report['owned_gateway_processes_and_fixture_cleaned'] = True
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Actual Caddy peer gateways: trusted TLS, two approvals, signed sync, negative gates and cleanup passed')


if __name__ == '__main__': main()
