#!/usr/bin/env python3
"""Prepare exact N3-tested artifacts on NUC; no service control, database reads or activation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from native_nuc_bundle import load_manifest,normalize_closure
from native_nuc_plan import make_plan
import tomllib

ROOT=Path(__file__).resolve().parents[1]
HOST='liou@nuc.local'
SSH=['ssh','-F','/home/liou/.ssh/config',HOST]
REMOTE='/home/liou/.local/share/tag-all/nuc-native-release'
CONTROLS={name:ROOT/'scripts'/name for name in ['native_nuc_bundle.py','native_nuc_snapshot.py','native_nuc_guard.py','native_nuc_plan.py',
          'native_nuc_runtime.py','native_pc_snapshot.py','native_pc_config.py','native_nuc_startup.py','native_nuc_switch.py','native_nuc_ingress.py']}
CONTROLS.update({name:ROOT/'deploy/scripts'/name for name in ['manage.py','render.py']})


def run(argv,**options):
    return subprocess.run(argv,check=True,capture_output=True,text=True,timeout=1800,**options)


def closure(candidate):
    result=json.loads(run(['nix','path-info','--recursive','--json',candidate]).stdout)
    return normalize_closure(result)


def remote_python(code,*args):
    return run(SSH+[shlex.join(['python3','-c',code,*args])])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',help='Copy fixed closure and private control bundle; never stop production')
    args=parser.parse_args()
    manifest=load_manifest();manifest['closure']=closure(manifest['candidate'])
    manifest['controls']={name:hashlib.sha256(source.read_bytes()).hexdigest() for name,source in CONTROLS.items()}
    # Bind the assembly input without copying user secrets or runtime directories.
    instance=ROOT/'deploy/instances/home.toml';manifest['instance_sha256']=hashlib.sha256(instance.read_bytes()).hexdigest()
    data=json.dumps(manifest,sort_keys=True,indent=2)+'\n'
    report={'manifest_sha256':hashlib.sha256(data.encode()).hexdigest(),'candidate':manifest['candidate'],
        'closure_paths':len(manifest['closure']),'closure_nar_bytes':sum(p['narSize'] for p in manifest['closure'].values()),
        'destination':REMOTE,'activated':False,'production_services_changed':False,'source_database_read':False,'own_artifact_import':'existing trusted liou user; explicit per-copy import; system trust policy unchanged'}
    if not args.prepare:
        report.update(dry_run=True,planned_actions=['nix copy exact tested closure','copy private manifest/config/control modules','verify remote store hashes and file digests'])
        print(json.dumps(report,indent=2));return
    remote_python("import os,socket;assert socket.gethostname()=='nuc' and os.getuid()==1000")
    inventory=json.loads(run(SSH+['podman inspect '+ ' '.join(sorted(manifest['source_images']))]).stdout)
    plan=make_plan(tomllib.loads(instance.read_text()),inventory)
    if {p['name']:p['image'].removeprefix('sha256:') for p in plan['containers']}!=manifest['source_images']:
        raise ValueError('NUC production topology changed since the accepted gates')
    env=dict(os.environ,NIX_SSHOPTS='-F /home/liou/.ssh/config')
    trusted=run(SSH+[shlex.join(['/run/current-system/sw/bin/nix','config','show','trusted-users'])]).stdout.split()
    if 'liou' not in trusted:raise ValueError('Explicit own-artifact import requires existing trusted liou user; no trust changes allowed')
    # Only our fixed, unpublished PC builds need this trusted-user import. The system signature policy is unchanged.
    run(['nix','copy','--no-check-sigs','--to','ssh-ng://'+HOST,manifest['candidate']],env=env)
    received=json.loads(run(SSH+[shlex.join(['/run/current-system/sw/bin/nix','path-info','--recursive','--json',manifest['candidate']])]).stdout)
    actual=normalize_closure(received)
    if actual!=manifest['closure']:raise ValueError('Remote closure differs from tested artifacts')
    # Publish a new private release directory; never overwrite a previously prepared release.
    destination=REMOTE+'/'+report['manifest_sha256']
    remote_python("import os,pathlib,sys;p=pathlib.Path(sys.argv[1]);assert not p.exists() and not p.is_symlink();p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);assert not p.parent.is_symlink();p.mkdir(mode=0o700)",destination)
    with tempfile.TemporaryDirectory(prefix='nuc-release-') as temporary:
        local=Path(temporary);(local/'manifest.json').write_text(data);(local/'manifest.json').chmod(0o600)
        files=[local/'manifest.json',instance,*CONTROLS.values()]
        # Exact allowlist, no directory recursion/delete/source/private runtime data.
        run(['scp','-F','/home/liou/.ssh/config',*[str(p) for p in files],HOST+':'+destination+'/'])
    remote_python("import hashlib,json,pathlib,sys;p=pathlib.Path(sys.argv[1]);m=json.loads((p/'manifest.json').read_text());expected={**m['controls'],'home.toml':m['instance_sha256']};assert set(q.name for q in p.iterdir())==set(expected)|{'manifest.json'};assert hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest()==sys.argv[2];[(q.chmod(0o600)) for q in p.iterdir()];assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in expected.items())",destination,report['manifest_sha256'])
    # Retain the unused candidate against server GC; all paths were verified valid, no remote build.
    run(SSH+[shlex.join(['/run/current-system/sw/bin/nix-store','--add-root',destination+'/candidate','--indirect','--realise',manifest['candidate']])])
    remote_python("import pathlib,sys;p=pathlib.Path(sys.argv[1]);assert p.is_symlink() and str(p.resolve())==sys.argv[2]",destination+'/candidate',manifest['candidate'])
    report.update(dry_run=False,prepared_release=destination,remote_closure_verified=True,control_files_verified=True,remote_gc_root_verified=True)
    (ROOT/'.devenv/native-nuc-preparation-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        print('NUC preparation refused: '+(str(error) if isinstance(error,ValueError) else type(error).__name__),file=__import__('sys').stderr)
        raise SystemExit(1)
