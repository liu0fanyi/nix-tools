#!/usr/bin/env python3
"""Synthetic offline Caddy storage takeover and live renewal; never production PKI."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise RuntimeError('Owned fixture command failed: ' + result.stderr[-3500:])
    return result.stdout.strip()


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag_all', type=Path)
    parser.add_argument('dufs_plus', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError('Non-root owned fixtures required')
    output = ROOT / '.devenv/native-peer-renewal-results.json'
    output.unlink(missing_ok=True)
    caddy = json.loads((ROOT / 'specs/012-native-core-gateway/results.json').read_text())['caddy_package'] + '/bin/caddy'
    proc = None
    with tempfile.TemporaryDirectory(prefix='r-', dir=ROOT / '.devenv') as directory:
        state = Path(directory)
        source = state / 'source-storage'
        target = state / 'native-storage'
        auth = state / 'auth'
        auth.write_text('fixture ' + run([caddy, 'hash-password', '--plaintext', 'synthetic-only']) + '\n')
        auth.chmod(0o600)
        tls_port = port()
        params = {'authFile': str(auth), 'fileSocket': str(state / 'files.sock'),
                  'gatewayPort': port(), 'corePort': port(), 'peer': {
                  'serverName': 'localhost', 'listenAddress': '127.0.0.1', 'port': tls_port,
                  'allowedNetworks': ['127.0.0.1/32'], 'tlsMode': 'internal', 'storageDirectory': str(source)}}
        settings = state / 'settings.json'
        settings.write_text(json.dumps(params))
        expr = f'import {ROOT}/tests/native-peer-gateway.nix {{ infrastructure = {json.dumps(str(ROOT))}; tagAll = {json.dumps(str(args.tag_all.resolve()))}; dufsPlus = {json.dumps(str(args.dufs_plus.resolve()))}; settings = {json.dumps(str(settings))}; }}'
        generated = Path(run(['nix-build', '--no-out-link', '-A', 'config', '--expr', expr]))
        original = generated.read_text()
        assert 'auto_https disable_redirects' in original and 'skip_install_trust' in original
        assert 'tls internal' in original and 'storage file_system' in original
        # Only fixture timing changes; production uses Caddy defaults (12h / 10m).
        accelerated = original.replace('skip_install_trust', 'skip_install_trust\n renew_interval 1s').replace('tls internal', 'tls {\n issuer internal {\n lifetime 30s\n }\n }')
        config = state / 'Caddyfile'
        config.write_text(accelerated)
        def stop():
            nonlocal proc
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
            proc = None
        def start():
            nonlocal proc
            env = os.environ.copy()
            env.update(XDG_CONFIG_HOME=str(state / 'config'), XDG_DATA_HOME=str(state / 'unrelated-data'), TAG_PEER_ADMIN_TOKEN='synthetic-only')
            with (state / 'log').open('ab') as log:
                proc = subprocess.Popen([caddy, 'run', '--config', str(config), '--adapter', 'caddyfile'], env=env, stdout=log, stderr=log)
        def certificate(context):
            with socket.create_connection(('127.0.0.1', tls_port), timeout=2) as sock:
                with context.wrap_socket(sock, server_hostname='localhost') as connection:
                    return connection.getpeercert(binary_form=True)
        try:
            start()
            root = source / 'pki/authorities/local/root.crt'
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError('Synthetic bootstrap exited: ' + (state / 'log').read_text()[-2000:])
                if root.exists():
                    context = ssl.create_default_context(cafile=str(root))
                    try:
                        initial = certificate(context)
                        break
                    except OSError: pass
                time.sleep(.1)
            else: raise AssertionError('Synthetic certificate bootstrap timed out')
            stop()
            source_hashes = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in source.rglob('*') if p.is_file()}
            shutil.copytree(source, target)
            for p in [target, *target.rglob('*')]: p.chmod(0o700 if p.is_dir() else 0o600)
            config.write_text(accelerated.replace(str(source), str(target)))
            start()
            for _ in range(100):
                try:
                    resumed = certificate(context)
                    break
                except OSError: time.sleep(.1)
            else: raise AssertionError('Synthetic takeover timed out')
            assert resumed == initial, 'Offline takeover must retain cached leaf before renewal'
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                assert proc.poll() is None
                renewed = certificate(context)
                if renewed != resumed: break
                time.sleep(.5)
            else: raise AssertionError('Managed leaf certificate was not renewed automatically')
            assert (target / 'pki/authorities/local/root.crt').read_bytes() == root.read_bytes()
            conn = http.client.HTTPSConnection('localhost', tls_port, context=context, timeout=3)
            try:
                conn.request('GET', '/tag-api/v1/peers/approvals', headers={'x-tag-admin-token': 'synthetic-only'})
                response = conn.getresponse(); assert response.status == 404; response.read()
            finally: conn.close()
            try:
                certificate(ssl.create_default_context())
                raise AssertionError('Untrusted private CA must be rejected')
            except ssl.SSLCertVerificationError: pass
            stop()
            # Build the actual module, then execute its private-storage guard on fixture paths.
            home = state / 'h'; home.mkdir(mode=0o700)
            (home / 'work space % $ 中文').mkdir()
            unit_expr = f'import {ROOT}/tests/native-stack-install.nix {{ infrastructure = {json.dumps(str(ROOT))}; tagAll = {json.dumps(str(args.tag_all.resolve()))}; dufsPlus = {json.dumps(str(args.dufs_plus.resolve()))}; configured = true; peerEnabled = true; peerInternal = true; peerStorage = {json.dumps(str(target))}; homeDirectory = {json.dumps(str(home))}; }}'
            generation = Path(run(['nix-build', '--no-out-link', '-A', 'generation', '--expr', unit_expr]))
            unit = (generation / 'home-files/.config/systemd/user/tag-native-workspace.service').read_text()
            guard = next(line.split('=', 1)[1] for line in unit.splitlines() if line.startswith('ExecStartPre=') and 'native-peer-tls-check' in line)
            run([guard])
            key = target / 'pki/authorities/local/root.key'
            key.chmod(0o644)
            assert subprocess.run([guard], capture_output=True).returncode != 0
            key.chmod(0o600)
            saved = key.with_suffix('.saved'); key.rename(saved)
            assert subprocess.run([guard], capture_output=True).returncode != 0
            key.symlink_to(saved)
            assert subprocess.run([guard], capture_output=True).returncode != 0
            key.unlink(); saved.rename(key)
            run([guard])
            assert source_hashes == {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in source.rglob('*') if p.is_file()}
            report = {'synthetic_offline_storage_takeover': True, 'cached_leaf_retained': True,
                      'live_automatic_leaf_renewal': True, 'original_root_trust_preserved': True,
                      'untrusted_ca_rejected': True, 'peer_admin_route_still_denied': True,
                      'actual_generated_private_storage_guard': True,
                      'unsafe_missing_symlink_key_rejected': True, 'source_snapshot_unchanged': True,
                      'fixture_leaf_lifetime_seconds': 30, 'fixture_renew_interval_seconds': 1,
                      'production_keys_read': False, 'activated': False, 'generation': str(generation)}
        finally: stop()
    report['owned_process_and_storage_cleaned'] = True
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Synthetic CA takeover, live certificate renewal, trust and private-storage guards passed')


if __name__ == '__main__': main()
