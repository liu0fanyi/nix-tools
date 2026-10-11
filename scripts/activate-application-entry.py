#!/usr/bin/env python3
"""Hash-bound NUC entry update/rollback. Default is read-only; no database restore."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tarfile
import time
from application_entry_transaction import ConfigurationTransaction, atomic, backup_state, create_lock, digest, exclusive, offline_states, private
from native_nuc_startup import host_environment, load_control, read_inventory, lock, ROOT, CONTROL
from native_nuc_bundle import UNITS
from native_nuc_guard import validate

RUNTIME = CONTROL.parent
RELEASES = Path('/home/liou/.local/share/tag-all/application-entry-releases')
UNIT_DIR = Path('/home/liou/.config/systemd/user')
NEW_UNITS = set(UNITS) - {'tag-nuc-bridge.service'}
ENTRIES = {'private-' + n: ROOT / 'private/config' / n for n in ['application-entry.toml', 'basic.entries']}
ENTRIES.update({'readonly-' + n: ROOT / 'readonly/config' / n for n in ['application-entry.toml', 'basic.entries']})
ENTRIES.update({n: RUNTIME / n for n in ['Caddyfile', 'haproxy.readonly.cfg', 'application-compose.json', 'native-nuc-control.json']})
PKI = [Path('/home/liou/.local/share/caddy'), Path('/home/liou/.local/share/caddy-container-config')]


def run(argv, check=True, capture_output=True):
    return subprocess.run(argv, check=check, capture_output=capture_output, text=True, timeout=300, env=host_environment(os.environ))


def legacy_transport(path):
    path = Path(path); info = path.lstat()
    # Existing non-secret HAProxy routing file is 644; new reviewed config is 600.
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) not in {0o600,0o644}:
        raise ValueError('Unexpected legacy HAProxy file ownership/mode')
    return path.read_text()


def preflight(release, expected, rollback=False):
    if socket.gethostname() != 'nuc' or os.getuid() != 1000: raise ValueError('Fixed NUC user/host required')
    release = private(release, True)
    if release.parent != RELEASES or release.name != expected or digest(private(release / 'manifest.json')) != expected:
        raise ValueError('Fixed prepared release digest required')
    manifest = json.loads((release / 'manifest.json').read_text())
    if manifest['state_policy'] != 'reuse-current-database-metadata-ca-and-identity-no-restore': raise ValueError('Wrong state policy')
    if set(manifest['files']) != set(ENTRIES): raise ValueError('Unexpected runtime file allowlist')
    for name, sha in manifest['files'].items():
        if digest(private(release / name)) != sha: raise ValueError('Prepared configuration changed')
    candidate = Path(manifest['candidate'])
    if not str(candidate).startswith('/nix/store/') or candidate != (release / 'candidate').resolve(): raise ValueError('Candidate GC root changed')
    if set(manifest['units']) != NEW_UNITS: raise ValueError('Wrong seven-unit candidate')
    for name, sha in manifest['units'].items():
        if digest(candidate / 'lib/systemd/user' / name) != sha: raise ValueError('Candidate unit changed')
    units = unit_status()
    if rollback:
        images = {v['name']:v['image'] for v in manifest['live_inventory']}
        for name, image in images.items():
            item = container(name, allow_missing=name in {'dufs-plus_caddy_1','dufs-plus_readonly-gateway_1'})
            if item and (item['Image'].removeprefix('sha256:') != image.removeprefix('sha256:') or item['Config']['Labels'].get('io.podman.compose.project') != 'dufs-plus'):
                raise ValueError('Rollback container identity changed')
    if not rollback:
        records, units = read_inventory(run)
        if (ROOT / 'startup-mode').read_text() != 'native\n' or any(v != 'active' for v in units.values()):
            raise ValueError('Current native stack must be active before update')
        control = load_control()
        if digest(CONTROL) != manifest['startup_control_before_sha256']: raise ValueError('Startup control drifted')
        transport = legacy_transport(RUNTIME / 'haproxy.readonly.cfg')
        old = 'server caddy_http caddy:5008 check'; new = 'server native_http host.containers.internal:18182 check'
        if transport.count(old) != 1 or transport.replace(old, new) != (release / 'haproxy.readonly.cfg').read_text():
            raise ValueError('Readonly transport drifted')
        auth = private('/home/liou/.config/dufs-plus/secrets/caddy_lan_basic_auth').read_text().strip() + '\n'
        if auth != (release / 'private-basic.entries').read_text(): raise ValueError('Basic credentials changed after preparation')
        validate('native', ROOT, records, units, source_images=control['source_images'])
        current = sorted([{'name':n, 'id':v['Id'], 'image':v['Image'], 'running':v['State']['Running'],
                           'restart':v['HostConfig']['RestartPolicy']['Name']} for n,v in records.items()], key=lambda p:p['name'])
        if current != sorted(manifest['live_inventory'], key=lambda p:p['name']): raise ValueError('Container inventory drifted')
        for name in UNITS:
            link = UNIT_DIR / name
            if not link.is_symlink() or not str(link.resolve()).startswith('/nix/store/49gihkvq010kiscjjvcgzmbll7yklvps-tag-all-native-nuc-candidate/lib/systemd/user/'):
                raise ValueError('Previous unit registration changed')
    # Never inspect a user database or metadata during preflight.
    private(ROOT, True)
    for role in ['private', 'readonly']:
        private(ROOT / role, True); private(ROOT / role / 'config', True)
        private(ROOT / role / 'state', True)
        if units['tag-nuc-' + role + '-tools.service'] == 'active':
            result = run(['podman', '--remote', '--url', 'unix://' + str(ROOT / role / 'tools/runtime.sock'), 'ps', '--format', 'json'])
            if json.loads(result.stdout): raise ValueError('Processing tasks still active; wait before cutover')
        elif not rollback:
            raise ValueError('Processing runtime unavailable')
    for path in PKI:
        if path.is_symlink() or not path.is_dir() or path.stat().st_uid != 1000: raise ValueError('Fixed owned Caddy state missing')
    if not rollback:
        mounts = {m['Destination']: m['Source'] for m in records['dufs-plus_caddy_1']['Mounts'] if m['Type'] == 'bind'}
        if [mounts.get(n) for n in ['/data/caddy', '/config/caddy']] != list(map(str, PKI)): raise ValueError('Caddy PKI mount changed')
    return manifest


def replacements(release, manifest):
    result = {path: {'kind':'file', 'source':str(release / name), 'sha256':manifest['files'][name]} for name,path in ENTRIES.items()}
    result.update({UNIT_DIR / name: {'kind':'symlink', 'target':str(Path(manifest['candidate']) / 'lib/systemd/user' / name)} for name in NEW_UNITS})
    result[UNIT_DIR / 'tag-nuc-bridge.service'] = {'kind':'absent'}
    return result


def unit_status():
    result = {}
    for name in UNITS:
        fields = dict(line.split('=',1) for line in run(['systemctl','--user','show',name,'--property=LoadState,ActiveState'],check=False).stdout.splitlines() if '=' in line)
        result[name] = 'unknown' if fields.get('LoadState') == 'not-found' else fields.get('ActiveState')
        if not result[name]: raise ValueError('Incomplete unit inventory')
    return result


def container(name, allow_missing=False):
    result = run(['podman','inspect',name],check=False)
    if result.returncode:
        # A failed recreate can leave an ingress container absent. Verify absence by
        # the actual inventory, not by treating every inspect error as missing.
        if allow_missing:
            names = run(['podman','ps','-a','--format','{{.Names}}']).stdout.splitlines()
            if name not in names: return None
        raise ValueError('Required container inspection failed')
    values = json.loads(result.stdout)
    if len(values) != 1 or values[0]['Name'].lstrip('/') != name: raise ValueError('Unexpected container inspection')
    return values[0]


def stopped():
    if any(v not in {'inactive','failed','unknown'} for v in unit_status().values()): raise ValueError('All native units must stop')
    for name in ['caddy','readonly-gateway','dufs','dufs-readonly','tag-server','tag-server-readonly','tag-peer-discovery']:
        item = container('dufs-plus_' + name + '_1', allow_missing=name in {'caddy','readonly-gateway'})
        if item and item['State']['Running']: raise ValueError('Conflicting listeners or old writers still running')
    for port in [5006, 5008, 5009, 18182]:
        with socket.socket(socket.AF_INET6) as probe:
            probe.bind(('::', port))


def stop_stack():
    # The target must stop before members; otherwise Upholds may restart a writer.
    run(['systemctl','--user','stop','tag-native-nuc.target'])
    run(['systemctl','--user','stop', *sorted(set(UNITS) - {'tag-native-nuc.target'})])
    for name in ['dufs-plus_caddy_1','dufs-plus_readonly-gateway_1']:
        if container(name, allow_missing=True): run(['podman','stop',name])
    stopped()


def set_mode(value):
    with lock(ROOT / 'startup.lock'): atomic(ROOT / 'startup-mode', value + '\n')


def start_stack(transaction, rollback=False):
    run(['systemctl','--user','daemon-reload'])
    run(['systemctl','--user','reset-failed',*sorted(UNITS)], check=False)
    # Release the persistent barrier only after the full configuration transaction.
    load_control()
    set_mode('native')
    run(['systemctl','--user','start','tag-native-nuc.target'])
    deadline = time.monotonic() + 60
    expected = set(UNITS) if rollback else NEW_UNITS
    while True:
        _, status = read_inventory(run)
        if all(status[n] == 'active' for n in expected): break
        if time.monotonic() >= deadline: raise ValueError('Native target did not become healthy')
        time.sleep(1)
    control = load_control()
    run([*control['compose'],'up','-d','--no-deps','--force-recreate','caddy','readonly-gateway'])
    records, status = read_inventory(run)
    validate('native', ROOT, records, status, source_images=control['source_images'])
    if not all(records['dufs-plus_' + n + '_1']['State']['Running'] for n in ['caddy','readonly-gateway','authelia','ddns-go']):
        raise ValueError('Retained ingress unavailable')
    transaction.phase('rolled-back-current-state' if rollback else 'activated-awaiting-P3')


def execute(release, manifest, rollback=False, verify_inputs=lambda: None):
    desired = replacements(release, manifest)
    transaction = ConfigurationTransaction(release / 'p2', desired)
    if rollback: transaction.load()
    else: transaction.create(desired)
    with exclusive(ROOT / 'startup.lock'):
        verify_inputs()
        atomic(ROOT / 'startup-mode', 'transition\n')
    transaction.phase('rollback-stopping' if rollback else 'stopping')
    try:
        stop_stack()
        states = [ROOT / role / 'state' for role in ['private','readonly']]
        with offline_states(states, stopped):
            if not rollback:
                receipts = {role: backup_state(ROOT / role / 'state', release / 'p2' / ('backup-' + role)) for role in ['private','readonly']}
                archive = release / 'p2/caddy-state.tar'
                with tarfile.open(archive, 'x', dereference=False) as out:
                    for path in PKI: out.add(path, arcname=path.name)
                archive.chmod(0o600)
                with archive.open('rb') as stream: os.fsync(stream.fileno())
                atomic(release / 'p2/offline-backup.json', json.dumps({'states':receipts,'pki_sha256':digest(archive),'restore_allowed':False}) + '\n')
                apps = ROOT / 'private/apps'
                if apps.exists(): private(apps, True)
                else: apps.mkdir(mode=0o700)
                for name in ['devices','transcriptions','recorder-bean','bevy-game','bevy-sketch','project-planner','quick-note']:
                    path = apps / name
                    if path.exists(): private(path, True)
                    else: path.mkdir(mode=0o700)
            transaction.install(rollback=rollback)
        start_stack(transaction, rollback)
    except BaseException:
        # Fail closed. Recovery is explicit and always uses the newest state.
        set_mode('transition')
        run(['systemctl','--user','stop',*UNITS],check=False)
        run(['podman','stop','dufs-plus_caddy_1','dufs-plus_readonly-gateway_1'],check=False)
        transaction.phase('failed-use-explicit-current-state-rollback')
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release');parser.add_argument('--manifest-sha256',required=True)
    group=parser.add_mutually_exclusive_group();group.add_argument('--apply',action='store_true');group.add_argument('--rollback',action='store_true')
    parser.add_argument('--editors-saved',action='store_true')
    opts=parser.parse_args();release=Path(opts.release)
    if (opts.apply or opts.rollback) and not opts.editors_saved: raise ValueError('Fresh saved-editor confirmation required')
    if opts.apply or opts.rollback:
        # Controller-wide lock remains held; startup checks use a different lock.
        control_lock = RELEASES / 'cutover.lock'
        create_lock(control_lock)
        with exclusive(control_lock):
            manifest=preflight(release,opts.manifest_sha256,opts.rollback)
            execute(release,manifest,opts.rollback,verify_inputs=lambda:preflight(release,opts.manifest_sha256,opts.rollback))
    else:
        with lock(ROOT / 'startup.lock', shared=True):
            manifest=preflight(release,opts.manifest_sha256)
        print(json.dumps({'stage':'E5/P2','dry_run':True,'candidate':manifest['candidate'],
            'replace_units':sorted(NEW_UNITS),'stop_bridge':True,'offline_backup_after_stop':True,
            'rollback_restores_state':False,'untouched_containers':['authelia','ddns-go'],
            'database_read':False,'production_changed':False},indent=2))


if __name__=='__main__':
    try:main()
    except Exception as error:
        # subprocess output and config contents may contain credentials; never print them.
        print('Entry cutover refused: '+type(error).__name__+'; inspect private journal',file=sys.stderr)
        raise SystemExit(1)
