#!/usr/bin/env python3
"""Own native core + Caddy + Unix DUFS fixtures, real consumer checks, no deployment."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    result = subprocess.run(args, timeout=kwargs.pop('timeout', 60),
                            capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError('Owned check command failed: ' + result.stderr)
    return result


def port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag_all', type=Path)
    parser.add_argument('dufs_plus', type=Path)
    parser.add_argument('tag_browser', type=Path)
    args = parser.parse_args()
    tag, dufs, browser = [p.resolve() for p in (args.tag_all, args.dufs_plus, args.tag_browser)]
    native = json.loads((tag / '.devenv/native-core-results.json').read_text())
    package = Path(native['package'])
    binary = package / 'libexec/tag-server-core'
    if hashlib.sha256(binary.read_bytes()).hexdigest() != native['binary_sha256'] or not native['native_http_gate']:
        raise RuntimeError('Native core does not match passed packaging gate')
    dist = dufs / 'dist'
    if not (dist / 'index.html').is_file():
        raise RuntimeError('Build frontend using its own just build first')
    lock = json.loads((tag / 'devenv.lock').read_text())['nodes']['nixpkgs']['locked']
    expr = '((builtins.fetchTree (builtins.fromJSON ' + json.dumps(json.dumps(lock)) + ')).outPath)'
    nixpkgs = run(['nix', 'eval', '--offline', '--impure', '--raw', '--expr', expr]).stdout.strip()
    temp_parent = ROOT / '.devenv'
    temp_parent.mkdir(exist_ok=True)
    report_path = temp_parent / 'native-workspace-results.json'
    report_path.unlink(missing_ok=True)
    processes = []
    with tempfile.TemporaryDirectory(prefix='native-workspace-', dir=temp_parent) as folder:
        root = Path(folder)
        environment = os.environ.copy()
        environment['XDG_CONFIG_HOME'] = str(root / 'xdg-config')
        environment['XDG_DATA_HOME'] = str(root / 'xdg-data')
        workspace = root / 'workspace'
        workspace.mkdir()
        file_socket = root / 'files.sock'
        auth_file = root / 'auth.entries'
        node_id = 'native-gateway-' + uuid.uuid4().hex
        config = root / 'node.toml'
        config.write_text('[node]\nid = ' + json.dumps(node_id) + '\nname = "Native Gateway Gate"\n')
        ports = [port(), port()]
        if len(set(ports)) != 2:
            raise RuntimeError('Port collision; retry with new owned fixture')
        gateway_port, core_port = ports
        expression = root / 'gateway.nix'
        expression.write_text('let pkgs = import ' + json.dumps(nixpkgs) + ' { system = "x86_64-linux"; }; in import '
            + str(ROOT / 'packages/native-workspace.nix') + ' { inherit pkgs; '
            + 'frontendRoot = ' + json.dumps(str(dist)) + '; authFile = ' + json.dumps(str(auth_file))
            + '; fileSocket = ' + json.dumps(str(file_socket)) + '; gatewayPort = ' + str(gateway_port)
            + '; corePort = ' + str(core_port) + '; }\n')
        outputs = {}
        for attr in ['caddy', 'dufs', 'config']:
            outputs[attr] = run(['nix-build', str(expression), '-A', attr, '--no-out-link'], timeout=300).stdout.strip().splitlines()[-1]
        caddy = str(Path(outputs['caddy']) / 'bin/caddy')
        file_server = str(Path(outputs['dufs']) / 'bin/dufs')
        username, password = 'native-gate', secrets.token_urlsafe(32)
        password_hash = run([caddy, 'hash-password', '--algorithm', 'bcrypt', '--bcrypt-cost', '10'], input=password + '\n').stdout.strip()
        auth_file.write_text(username + ' ' + password_hash + '\n')
        auth_file.chmod(0o600)
        # Hash content is only in this private runtime file, never a store path.
        assert password_hash not in Path(outputs['config']).read_text()
        authorization = 'Basic ' + base64.b64encode((username + ':' + password).encode()).decode()
        base = f'http://127.0.0.1:{gateway_port}'
        def request(path, data=None, method=None, auth=True, headers=None):
            body = json.dumps(data).encode() if isinstance(data, dict) else data
            values = {'Content-Type': 'application/json'} if isinstance(data, dict) else {}
            if auth:
                values['Authorization'] = authorization
            values.update(headers or {})
            req = urllib.request.Request(base + path, data=body, headers=values, method=method)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.status, response.read(), dict(response.headers)
            except urllib.error.HTTPError as error:
                return error.code, error.read(), dict(error.headers)
        def start(command, name):
            log = (root / (name + '.log')).open('wb')
            try:
                process = subprocess.Popen(command, stdout=log, stderr=log, env=environment)
            finally:
                log.close()
            processes.append(process)
        try:
            run(['node', str(dufs / 'tests/native-core-entry.browser.cjs'), '--write-fixture', str(workspace / 'book.pdf')])
            original_pdf = (workspace / 'book.pdf').read_bytes()
            start([str(package / 'bin/tag-all-core'), '--state-dir', str(root / 'core-state'),
                   '--workspace', str(workspace), '--config', str(config), '--addr', f'127.0.0.1:{core_port}'], 'core')
            start([file_server, str(workspace), '--bind', str(file_socket), '--allow-upload',
                   '--allow-delete', '--allow-search', '--allow-archive'], 'dufs')
            run([caddy, 'validate', '--config', outputs['config'], '--adapter', 'caddyfile'], env=environment)
            start([caddy, 'run', '--config', outputs['config'], '--adapter', 'caddyfile'], 'gateway')
            for _ in range(150):
                if any(p.poll() is not None for p in processes):
                    details = '\n'.join(p.read_text() for p in root.glob('*.log'))
                    raise RuntimeError('Owned service startup failed: ' + details)
                try:
                    status, data, _ = request('/tag-api/v1/locations/default/capabilities')
                    if status == 200:
                        target = json.loads(data)
                        assert target['node_id'] == node_id
                        break
                except OSError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError('Owned gateway failed to start')
            assert file_socket.is_socket()
            for path in ['/', '/.dufs-plus/capabilities.json', '/tag-api/tags', '/book.pdf', '/?json']:
                assert request(path, auth=False)[0] == 401, path
                assert request(path, headers={'Authorization': 'Basic eDp5'})[0] == 401, path
            assert request('/tag-api/tags', {'name': 'unauth-write'}, auth=False)[0] == 401
            assert request('/forbidden.md', b'forbidden', method='PUT', auth=False)[0] == 401
            assert not (workspace / 'forbidden.md').exists()
            assert request('/')[0] == 200
            capabilities = json.loads(request('/.dufs-plus/capabilities.json')[1])
            assert capabilities['tag_write'] and capabilities['dufs_write'] and not capabilities['terminal']
            assert target['report']['capabilities']['pdf']['compiled'] is False
            assert request('/tag-api/tags', {'name': 'native-gateway'})[0] in {200, 201}
            assert request('/tag-api/items/text/write', {'path': 'note.md', 'location_id': 'default',
                     'text': 'native gateway text', 'create_only': True})[0] == 201
            assert (workspace / 'note.md').read_text() == 'native gateway text'
            assert request('/upload.txt', b'actual native upload', method='PUT')[0] in {200, 201}
            assert request('/upload.txt')[1] == b'actual native upload'
            assert request('/?json')[0] == 200
            assert request('/book.pdf')[1] == original_pdf
            assert request('/tag-api/v1/proxy/stream/default/book.pdf')[1] == original_pdf
            for path in ['/device-api', '/dist/devices/', '/dist/transcriptions/', '/dist/recorder-bean/']:
                assert request(path)[0] == 404, path
            secret_payload = json.dumps({'base': base, 'username': username, 'password': password, 'nodeId': node_id})
            for entry in [browser / 'tests/native-core-entry.mjs', dufs / 'tests/native-core-entry.browser.cjs']:
                result = run(['node', str(entry)], input=secret_payload, timeout=180)
                print(result.stdout.strip())
            assert (workspace / 'book.pdf').read_bytes() == original_pdf
            results = {'native_core_binary_sha256': native['binary_sha256'], 'nixpkgs_locked': lock,
                'caddy_package': outputs['caddy'], 'dufs_package': outputs['dufs'],
                'frontend_index_sha256': hashlib.sha256((dist / 'index.html').read_bytes()).hexdigest(),
                'authenticated_gateway': True, 'anonymous_and_wrong_credentials_denied': True,
                'anonymous_write_denied': True, 'file_upstream_private_unix_socket': True,
                'no_credentials_in_store': True, 'tags_text_upload_listing_stream': True,
                'sidebar_actual_methods': True, 'wasm_pdfjs_actual_http': True,
                'synthetic_pdf_unchanged': True, 'deployed': False,
                'full_firefox_ui_tested': False, 'real_pc_migration_tested': False}
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            assert all(p.poll() is not None for p in processes)
    results['owned_fixture_cleanup'] = True
    report_path.write_text(json.dumps(results, indent=2) + '\n')
    report_path.chmod(0o644)
    print('Verified authenticated native workspace; report: ' + str(report_path))


if __name__ == '__main__':
    main()
