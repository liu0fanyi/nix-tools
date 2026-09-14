#!/usr/bin/env python3
"""PC-only signed firmware publisher. Preview by default; --apply writes fixed Aliyun path."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import urllib.request

HOST = 'root@47.93.153.102'
BASE = 'https://wttliou.top/releases/esp32'
# This small remote transaction only receives public release bytes, never source trees or keys.
REMOTE = r'''
import base64, fcntl, hashlib, json, os, re, sys, tempfile
from pathlib import Path
ROOT = Path('/root/nix-tools/dufs_data/releases/esp32')
BASE = 'https://wttliou.top/releases/esp32'
PRODUCTS = {'esp32_mp3_player', 'esp32_recorder_bean', 'esp32_multi_timer'}
KEY = '64c8080e1e460e980f069ea161d5e2f439b2e6c55a2fd89bbee2ae6a5b52a9fc'
def digest(data): return hashlib.sha256(data).hexdigest()
def validate(entry):
    assert entry['product'] in PRODUCTS
    assert re.fullmatch(r'(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})', entry['version'])
    assert entry['family'] == 'waveshare-epaper154-v2' and entry['layoutVersion'] == 1 and entry['chip'] == 'esp32s3'
    assert entry['signingKeyId'] == KEY
    assert type(entry['size']) is int and 8192 <= entry['size'] <= 0x300000
    assert re.fullmatch('[a-f0-9]{64}', entry['sha256'])
    for field in ('sourceCommit', 'commonCommit'): assert re.fullmatch('[a-f0-9]{40}', entry[field])
    relative = entry['product'] + '/' + entry['version'] + '/application.bin'
    assert entry['url'] == BASE + '/' + relative
    return relative

def safe(path):
    assert path == ROOT or ROOT in path.parents
    for parent in [path, *path.parents]:
        assert not parent.is_symlink(), 'symlink rejected'

def read_catalog():
    path = ROOT / 'catalog.json'
    safe(path)
    return path.read_bytes() if path.exists() else b''

def merge(old, incoming):
    result = json.loads(old) if old else {'schemaVersion': 1, 'releases': []}
    assert result['schemaVersion'] == 1
    identities = {}
    for entry in result['releases']:
        key = validate(entry)
        assert key not in identities, 'duplicate existing version'
        identities[key] = entry
    for entry in incoming:
        key = validate(entry)
        if key in identities:
            assert identities[key] == entry, 'immutable release conflict'
        else:
            result['releases'].append(entry)
            identities[key] = entry
    assert len(result['releases']) <= 256
    data = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
    assert len(data) <= 256 * 1024
    return data

def atomic(path, data):
    safe(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    fd, name = tempfile.mkstemp(prefix='.publishing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno()); os.fchmod(stream.fileno(), 0o644)
        os.replace(name, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if os.path.exists(name): os.unlink(name)

def main():
    request = json.load(sys.stdin)
    safe(ROOT)
    if request['operation'] == 'read':
        old = read_catalog()
        print(json.dumps({'sha256': digest(old), 'catalog': old.decode()})); return
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o755)
    lock = ROOT / '.publish.lock'; safe(lock)
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        old = read_catalog()
        if request['operation'] == 'assets':
            incoming = [item['entry'] for item in request['assets']]
            merge(old, incoming)  # Reject catalog conflicts before any file is written.
            for item in request['assets']:
                entry = item['entry']; relative = validate(entry)
                data = base64.b64decode(item['data'], validate=True)
                assert len(data) == entry['size'] and digest(data) == entry['sha256']
                path = ROOT / relative; safe(path)
                if path.exists(): assert path.read_bytes() == data, 'immutable image conflict'
                else: atomic(path, data)
            print(json.dumps({'assets': len(incoming)}))
        elif request['operation'] == 'catalog':
            assert digest(old) == request['expected'], 'catalog changed: retry from read'
            for entry in request['entries']:
                path = ROOT / validate(entry); safe(path)
                data = path.read_bytes()
                assert len(data) == entry['size'] and digest(data) == entry['sha256']
            data = merge(old, request['entries'])
            atomic(ROOT / 'catalog.json', data)
            print(json.dumps({'sha256': digest(data)}))
        else: raise ValueError('unknown operation')
if __name__ == '__main__': main()
'''


def remote(payload):
    result = subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=yes', HOST,
                             'python3 -c ' + shlex.quote(REMOTE)], input=json.dumps(payload),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('release download redirects are not allowed')


def download(url, maximum):
    if not url.startswith(BASE + '/'):
        raise ValueError('unexpected download origin')
    request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
        data = response.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError('download exceeds expected size')
        return data


def publish(directories, apply=False):
    assets = []
    namespace = {}
    exec(compile(REMOTE, '<remote-validation>', 'exec'), namespace)
    for directory in directories:
        catalog = json.loads((directory / 'catalog.json').read_text())
        if catalog['schemaVersion'] != 1 or len(catalog['releases']) != 1:
            raise ValueError('one release per package required')
        entry = catalog['releases'][0]
        namespace['validate'](entry)
        data = (directory / 'application.bin').read_bytes()
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('local image mismatch')
        assets.append({'entry': entry, 'data': base64.b64encode(data).decode()})
    before = remote({'operation': 'read'})
    entries = [a['entry'] for a in assets]
    expected_catalog = namespace['merge'](before['catalog'], entries)
    print(json.dumps({'destination': HOST + ':/root/nix-tools/dufs_data/releases/esp32/',
                      'apply': apply, 'releases': [{k: e[k] for k in ('product', 'version', 'url', 'sha256')} for e in entries]}, indent=2))
    if not apply:
        return
    remote({'operation': 'assets', 'assets': assets})
    for entry in entries:
        data = download(entry['url'], entry['size'])
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('public image mismatch: catalog was not updated')
    remote({'operation': 'catalog', 'entries': entries, 'expected': before['sha256']})
    actual = download(BASE + '/catalog.json', 256 * 1024)
    if actual != expected_catalog:
        raise ValueError('catalog committed, but public confirmation differs; inspect cache before retry')
    print('Verified public images and catalog: ' + BASE + '/catalog.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, action='append', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    publish(args.package, args.apply)
