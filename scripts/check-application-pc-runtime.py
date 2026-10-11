#!/usr/bin/env python3
"""Synthetic fixed-candidate TLS gate; never use default XDG or production state."""
import sys, hashlib, json, shlex, subprocess, socket, tempfile, time, ssl, urllib.request, urllib.error, os, shutil
from pathlib import Path
metadata = Path(sys.argv[1])
d = metadata.parent
m = json.loads(metadata.read_text())
proof = json.loads(Path(sys.argv[2]).read_text())
assert hashlib.sha256(Path(m['nativePackage'] + '/libexec/tag-server-workspace').read_bytes()).hexdigest() == proof['binary_sha256']
cmd = shlex.split(m['services']['tag-native-workspace']['Service']['ExecStart'][0])
caddy = cmd[0]
source = Path(cmd[cmd.index('--config') + 1])
root = Path(tempfile.mkdtemp(prefix='e3b-'))
root.chmod(448)
procs = []

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def spawn(args, name):
    with (root / (name + '.log')).open('wb') as log:
        p = subprocess.Popen(args, stdout=log, stderr=log, start_new_session=True, env={**os.environ, 'XDG_CONFIG_HOME': str(root / 'caddy-config'), 'XDG_DATA_HOME': str(root / 'caddy-data'), 'TAG_PEER_ADMIN_TOKEN': 'synthetic-e3b-admin-token-00000000000'})
    procs.append(p)
    return p

def stop(p):
    if p.poll() is None:
        p.terminate()
        p.wait(timeout=15)

def req(url, headers={}, context=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'Origin': base, **headers} if url.startswith(base) else headers), context=context, timeout=3) as r:
            return (r.status, r.read())
    except urllib.error.HTTPError as e:
        return (e.code, e.read())

def wait(predicate, process):
    for _ in range(500):
        assert process.poll() is None, 'Synthetic process failed: ' + str(process.returncode)
        try:
            if predicate():
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    raise RuntimeError('Synthetic endpoint did not become ready')
try:
    for n in ['workspace', 'frontend', 'state', 'sockets']:
        (root / n).mkdir(mode=448)
    (root / 'frontend/index.html').write_text('e3b application')
    (root / 'workspace/note.md').write_text('e3b file')
    appport = port()
    tlsport = port()
    base = f'http://127.0.0.1:{appport}'
    peer = f'https://localhost:{tlsport}'
    files = root / 'sockets/files.sock'
    psock = root / 'sockets/peer.sock'
    node = root / 'node.toml'
    node.write_text('[node]\nid="e3b-synthetic"\n[discovery]\nenabled=false\n[sync]\nenabled=true\n[pairing]\nenabled=true\n')
    node.chmod(384)
    entry = root / 'sockets/entry.toml'
    entry.write_text('peer_socket=' + json.dumps(str(psock)) + '\npeer_authorities=[' + json.dumps(f'localhost:{tlsport}') + ']\npeer_write_delegation=true\n')
    entry.chmod(384)
    dufs = shlex.split(m['services']['tag-native-files']['Service']['ExecStart'][0])[0]
    fp = spawn([dufs, str(root / 'workspace'), '--bind', str(files), '--allow-upload', '--allow-delete', '--allow-search', '--allow-archive'], 'files')
    wait(lambda: files.exists(), fp)
    app = spawn([m['nativePackage'] + '/libexec/tag-server-workspace', '--workspace', str(root / 'workspace'), '--database', str(root / 'state/db.sqlite'), '--metadata-dir', str(root / 'state/metadata'), '--config', str(node), '--addr', f'127.0.0.1:{appport}', '--workspace-entry-frontend', str(root / 'frontend'), '--workspace-entry-dufs-socket', str(files), '--workspace-entry-config', str(entry)], 'app')
    wait(lambda: req(base + '/') == (200, b'e3b application') and psock.exists(), app)
    assert req(base + '/note.md') == (200, b'e3b file'), req(base + '/note.md')
    assert req(base + '/tag-api/tags')[0] == 200
    template = source.read_text()
    assert 'http://127.0.0.1:5006' not in template and 'uri strip_prefix' not in template and ('basic_auth' not in template) and ('respond `' not in template)
    cf = root / 'Caddyfile'
    cf.write_text(template.replace('liu-bigpc.local:5009', f'localhost:{tlsport}').replace('192.168.1.100', '127.0.0.1').replace('192.168.1.0/24', '127.0.0.1/32').replace(m['entryConfiguration']['peer_socket'], str(psock)).replace('/home/liou/.local/share/tag-all/pc-native/peer-caddy/caddy', str(root / 'tls')))
    cp = spawn([caddy, 'run', '--config', str(cf), '--adapter', 'caddyfile'], 'caddy')
    ca = root / 'tls/pki/authorities/local/root.crt'
    wait(lambda: ca.is_file(), cp)
    context = ssl.create_default_context(cafile=str(ca))
    wait(lambda: req(peer + '/tag-api/v1/peers/identity', context=context)[0] == 200, cp)
    for path in ['/', '/note.md', '/tag-api/tags', '/tag-api/peer-manager']:
        assert req(peer + path, headers={'X-Tag-Admin-Token': 'forged', 'Remote-User': 'admin', 'Remote-Groups': 'admins', 'Authorization': 'Basic YTpi'}, context=context)[0] in [403, 404], path
    wrong = req(peer + '/tag-api/v1/peers/identity', headers={'Host': 'untrusted.example'}, context=context)
    assert wrong[0] in (403, 404, 421) or wrong == (200, b''), wrong
    stop(cp)
    assert req(base + '/note.md') == (200, b'e3b file') and req(base + '/tag-api/tags')[0] == 200
    cf.write_text(cf.read_text().replace('remote_ip 127.0.0.1/32', 'remote_ip 192.0.2.0/24'))
    cp = spawn([caddy, 'run', '--config', str(cf), '--adapter', 'caddyfile'], 'caddy-denied')
    wait(lambda: req(peer + '/tag-api/v1/peers/identity', context=context)[0] == 404, cp)
    result = {'cases': ['same_process_web_api_files', 'candidate_tls_only_configuration', 'real_tls_private_peer_socket_identity', 'peer_business_authorization_and_forged_header_denial', 'peer_host_denial', 'local_application_survives_caddy_stop', 'caddy_source_network_denial'], 'passed': True, 'production_access': False, 'activated': False, 'synthetic_data_only': True, 'runtime_binary': m['nativePackage'] + '/libexec/tag-server-workspace'}
    (d / 'application-entry-pc-runtime-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print('7 PC candidate TLS and application runtime cases passed')
except Exception:
    for p in root.glob('*.log'):
        print(p.name, p.read_text()[-2000:])
    raise
finally:
    for p in reversed(procs):
        stop(p)
    shutil.rmtree(root)

assert not root.exists() and all(p.poll() is not None for p in procs)
result['owned_processes_and_runtime_cleaned'] = True
(d / 'application-entry-pc-runtime-results.json').write_text(json.dumps(result, indent=2) + '\n')
