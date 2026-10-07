#!/usr/bin/env python3
"""Run namespaced copies of generated units; only owned fixtures and runtime links."""
import argparse
import base64
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


def run(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=300)
    if check and result.returncode:
        raise RuntimeError('Owned stack command failed: ' + result.stderr[:1500])
    return result.stdout.strip()


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag_all', type=Path)
    parser.add_argument('dufs_plus', type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError('Non-root user manager required')
    parent = ROOT / '.devenv'; parent.mkdir(exist_ok=True)
    output = parent / 'native-stack-runtime-results.json'; output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='s', dir=parent) as directory:
        root = Path(directory); home = root / 'home'; home.mkdir(mode=0o700)
        workspace = home / 'work space % $ 中文'; workspace.mkdir()
        target = workspace / 'project'; target.mkdir()
        source = root / 'project source % $ 中文'; source.mkdir()
        (source / 'proof.md').write_text('mapped fixture proof')
        gateway_port, core_port = port(), port(); assert gateway_port != core_port
        prefix = 'native-runtime-' + uuid.uuid4().hex
        originals = ['tag-all-core.service', 'tag-native-files.service', 'tag-native-workspace.service', 'tag-native-stack.target']
        names = {name: prefix + '-' + name for name in originals}
        expression = 'import ' + str(ROOT / 'tests/native-stack-install.nix') + ' { infrastructure = ' + json.dumps(str(ROOT))
        expression += '; tagAll = ' + json.dumps(str(args.tag_all.resolve())) + '; dufsPlus = ' + json.dumps(str(args.dufs_plus.resolve()))
        expression += '; homeDirectory = ' + json.dumps(str(home)) + '; gatewayPort = ' + str(gateway_port) + '; corePort = ' + str(core_port)
        expression += '; workspaceMounts = { project = ' + json.dumps(str(source), ensure_ascii=False) + '; }; }'
        generation = Path(run(['nix-build', '--no-out-link', '-A', 'generation', '--expr', expression]))
        unit_root = generation / 'home-files/.config/systemd/user'
        native = json.loads((args.tag_all / '.devenv/native-core-results.json').read_text())
        assert native['native_http_gate'] and native['configured_peer_gate']
        caddy = json.loads((ROOT / 'specs/012-native-core-gateway/results.json').read_text())['caddy_package'] + '/bin/caddy'
        password = secrets.token_urlsafe(32)
        hashed = subprocess.run([caddy, 'hash-password', '--algorithm', 'bcrypt', '--bcrypt-cost', '10'],
            input=password + '\n', text=True, capture_output=True, check=True, timeout=30).stdout.strip()
        (home / 'auth.entries').write_text('native-runtime ' + hashed + '\n'); (home / 'auth.entries').chmod(0o600)
        authorization = 'Basic ' + base64.b64encode(('native-runtime:' + password).encode()).decode()
        base = f'http://127.0.0.1:{gateway_port}'
        owned_units = root / 'units'; owned_units.mkdir()
        runtime_units = Path(os.environ['XDG_RUNTIME_DIR']) / 'systemd/user'
        links = []
        for original, name in names.items():
            content = (unit_root / original).read_text()
            for old, new in names.items(): content = content.replace(old, new)
            assert hashed not in content
            path = owned_units / name; path.write_text(content)
            link = runtime_units / name
            assert not link.exists() and not link.is_symlink(), 'Refuse existing runtime unit'
            links.append((link, path))

        def ctl(*arguments, check=True):
            return run(['systemctl', '--user', *arguments], check=check)

        def pid(original):
            return int(ctl('show', names[original], '--property=MainPID', '--value') or '0')

        def request(path, body=None, method=None):
            data = json.dumps(body).encode() if isinstance(body, dict) else body
            req = urllib.request.Request(base + path, data, {'Authorization': authorization,
                'Content-Type': 'application/json' if isinstance(body, dict) else 'text/plain'}, method=method)
            with urllib.request.urlopen(req, timeout=3) as res:
                raw = res.read(); return res.status, raw

        def ready(old_pid=None, original='tag-all-core.service'):
            for _ in range(150):
                try:
                    status, raw = request('/tag-api/v1/locations/default/capabilities')
                    assert json.loads(raw)['node_id'] == 'pc-core-trial'
                    current = pid(original)
                    if status == 200 and current and current != old_pid: return current
                except (OSError, ValueError): pass
                time.sleep(.1)
            raise RuntimeError('Owned stack did not recover: ' + ctl('status', *names.values(), '--no-pager', check=False)[-2500:])

        try:
            ctl('link', '--runtime', *[str(path) for _, path in links])
            ctl('start', names['tag-native-stack.target']); ready()
            assert request('/project/proof.md')[1] == b'mapped fixture proof'
            status, raw = request('/tag-api/items/text/read', {'path': 'project/proof.md', 'location_id': 'default'})
            assert status == 200 and json.loads(raw)['text'] == 'mapped fixture proof'
            assert request('/tag-api/items/text/write', {'path': 'project/created.md', 'location_id': 'default',
                'text': 'written through native core', 'create_only': True})[0] == 201
            assert (source / 'created.md').read_text() == 'written through native core'
            assert request('/project/upload.txt', b'written through native files', 'PUT')[0] in {200, 201}
            assert (source / 'upload.txt').read_bytes() == b'written through native files'
            assert list(target.iterdir()) == [], 'Host workspace mount point must remain empty'
            assert request('/tag-api/tags', {'name': 'stack-runtime-persist'})[0] == 201
            recovered = []
            for original in ['tag-all-core.service', 'tag-native-files.service', 'tag-native-workspace.service']:
                before = pid(original)
                ctl('kill', '--signal=SIGKILL', '--kill-whom=main', names[original])
                ready(before, original)
                assert request('/project/proof.md')[1] == b'mapped fixture proof'
                assert 'stack-runtime-persist' in request('/tag-api/tags')[1].decode()
                recovered.append(original)
            ctl('stop', names['tag-native-stack.target'])
            # Stopping a target returns before its PartOf services finish exiting.
            for _ in range(100):
                states = [ctl('is-active', names[o], check=False) for o in originals[:-1]]
                if all(state not in {'active', 'activating', 'deactivating'} for state in states): break
                time.sleep(.05)
            else: raise RuntimeError('Owned stack children did not stop: ' + repr(states))
            with socket.socket() as s: assert s.connect_ex(('127.0.0.1', gateway_port)) != 0
            ctl('start', names['tag-native-stack.target']); ready()
            assert 'stack-runtime-persist' in request('/tag-api/tags')[1].decode()
            assert list(target.iterdir()) == []
            results = {'generation': str(generation), 'native_package': native['package'],
                'actual_generated_service_units': True, 'runtime_names_only_changed': True,
                'private_namespace_mapped_reads_and_writes': True, 'host_mount_target_unchanged': True,
                'all_three_sigkill_recovery': recovered, 'whole_target_stop_and_restart': True,
                'tag_and_mapped_files_persist': True, 'production_touched': False,
                'real_boot_tested': False, 'configured_peer_gateway_tested': False}
        finally:
            ctl('stop', names['tag-native-stack.target'], *[names[o] for o in originals[:-1]], check=False)
            ctl('reset-failed', *names.values(), check=False)
            for link, path in links:
                if link.is_symlink():
                    assert link.resolve() == path.resolve(), 'Refuse unowned link removal'
                    link.unlink()
                else: assert not link.exists(), 'Runtime path was replaced'
            ctl('daemon-reload')
            for name in names.values(): assert ctl('is-active', name, check=False) not in {'active', 'activating', 'deactivating'}
            assert list(target.iterdir()) == []
    results['owned_units_links_and_fixture_cleaned'] = True
    output.write_text(json.dumps(results, indent=2) + '\n')
    print('Generated native stack: mapped paths, read/write, all three crash recoveries, whole stop/restart and cleanup passed')


if __name__ == '__main__': main()
