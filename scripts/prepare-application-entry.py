#!/usr/bin/env python3
"""P1: prepare a private, hash-bound release; never stop or activate services."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import tomllib
import uuid
from application_entry_provider import compatible_readonly_source
from application_entry_release import application_compose, rebind_startup_control, digest, ROOTS, RUNTIME
from application_nuc_ingress import candidate_ingress, candidate_readonly_transport
from native_nuc_ingress import adapt_ingress
from native_nuc_bundle import normalize_closure

ROOT=Path(__file__).resolve().parents[1]
PRODUCT=Path('/data/project/tag-all')
SPEC=PRODUCT/'specs/027-application-entry-boundary'
HOST='liou@nuc.local'
SSH=['ssh','-F','/home/liou/.ssh/config',HOST]
REMOTE='/home/liou/.local/share/tag-all/application-entry-releases'


def private_diagnostic(value):
    fd,name=tempfile.mkstemp(prefix='entry-preparation-diagnostic-')
    with os.fdopen(fd,'w') as stream:stream.write(value)
    return name


def command(args,**kwargs):
    result=subprocess.run(args,capture_output=True,text=True,timeout=kwargs.pop('timeout',1800),**kwargs)
    if result.returncode:
        private_diagnostic(result.stderr)
        raise RuntimeError('Preparation command failed: '+args[0]+'; private output withheld')
    return result.stdout


def remote(code,*args):
    return command(SSH+[shlex.join(['python3','-c',code,*args])])


def normalize(model):
    for service in model['services'].values():
        volumes=[]
        for volume in service.get('volumes',[]):
            if isinstance(volume,dict):volumes.append(volume);continue
            parts=volume.split(':')
            if len(parts) not in (2,3) or not parts[1].startswith('/'):
                raise ValueError('Unreviewed bind notation: '+json.dumps({'parts':len(parts),'source':parts[0],'target':parts[1] if len(parts)>1 else None}))
            if len(parts)==3 and parts[2] not in ['ro','rw']:raise ValueError('Unreviewed bind policy')
            source=Path(parts[0])
            if not source.is_absolute():
                if not parts[0].startswith('./') or '..' in source.parts:raise ValueError('Relative bind escaped fixed runtime')
                source=Path(RUNTIME)/source
            volumes.append({'type':'bind','source':str(source),'target':parts[1],'read_only':len(parts)==3 and parts[2]=='ro'})
        if 'volumes' in service:service['volumes']=volumes
        ports=[]
        for port in service.get('ports',[]):
            if isinstance(port,dict):ports.append(port);continue
            parts=str(port).split(':')
            if len(parts)!=3 or parts[0]!='0.0.0.0' or not all(x.isdecimal() for x in parts[1:]):raise ValueError('Unreviewed port')
            ports.append({'host_ip':parts[0],'published':int(parts[1]),'target':int(parts[2]),'protocol':'tcp'})
        if 'ports' in service:service['ports']=ports
    return model


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true')
    opts=parser.parse_args()
    frozen=json.loads((SPEC/'entry-inventory-results.json').read_text())
    handover=json.loads((SPEC/'entry-handover-results.json').read_text())
    recovery=json.loads((SPEC/'entry-recovery-results.json').read_text())
    assert handover['complete'] and handover['owned_cleanup'] and recovery['owned_units_containers_and_state_cleaned']
    assert digest(SPEC/'entry-inventory-results.json')==handover['inventory_sha256']
    assert digest(SPEC/'entry-recovery-results.json')==handover['recovery_sha256']
    for base,files in frozen['source_manifest'].items():
        for name,sha in files.items():assert digest((PRODUCT if base=='product' else ROOT)/name)==sha,name
    for proof in [handover,recovery]:
        for name,sha in proof['source_manifest'].items():assert digest(PRODUCT/name)==sha,name
    candidate=frozen['nuc']['candidate']
    for name,sha in frozen['nuc']['units'].items():assert digest(Path(candidate)/'lib/systemd/user'/name)==sha
    current_pc=str(Path('/run/current-system').resolve())
    closure=normalize_closure(json.loads(command(['nix','path-info','--recursive','--json',candidate])))
    probe=r"""
import base64,hashlib,json,os,pathlib,socket,subprocess
assert socket.gethostname()=='nuc' and os.getuid()==1000
root=pathlib.Path('/home/liou/.local/share/tag-all/nuc-native');runtime=pathlib.Path('/home/liou/.local/share/dufs-plus/runtime/home')
control=json.loads((runtime/'native-nuc-control.json').read_text())
assert control['root']==str(root) and control['uid']==1000 and control['hostname']=='nuc'
assert (root/'startup-mode').read_text().strip()=='native'
assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in control['files'].items())
expected=set(control['source_images'])
records=json.loads(subprocess.check_output(['podman','inspect',*sorted(expected)]))
inventory=[]
for item in records:
 name=item['Name'].lstrip('/');assert name in expected and item['Image'].removeprefix('sha256:')==control['source_images'][name].removeprefix('sha256:')
 assert item['Config']['Labels']['io.podman.compose.project']=='dufs-plus'
 inventory.append({'name':name,'id':item['Id'],'image':item['Image'],'running':item['State']['Running'],'restart':item['HostConfig']['RestartPolicy']['Name']})
allowed=[runtime/'Caddyfile',runtime/'haproxy.readonly.cfg',root/'backup/Caddyfile',pathlib.Path('/home/liou/.config/dufs-plus/secrets/caddy_lan_basic_auth')]
files={str(p):base64.b64encode(p.read_bytes()).decode() for p in allowed}
argv=control['compose']+['config']
merged=subprocess.run(argv,capture_output=True,text=True,check=True).stdout
apps={n:(pathlib.Path('/home/liou/dufs-lan/dist')/n).is_dir() for n in ['devices','transcriptions','recorder-bean','bevy-game','bevy-sketch','project-planner','quick-note']}
assert all(apps.values())
print(json.dumps({'control':control,'control_sha256':hashlib.sha256((runtime/'native-nuc-control.json').read_bytes()).hexdigest(),'files':files,'merged':merged,'inventory':inventory,'apps':apps}))
"""
    live=json.loads(remote(probe))
    for item in live['inventory']:
        old=item['name'].removeprefix('dufs-plus_').removesuffix('_1') not in ['caddy','authelia','readonly-gateway','ddns-go']
        assert item['running'] is (not old)
        if old:assert item['restart']=='no'
    sys_path='/nix/store/iw39pw567acajnaf1iywnwz6fwcb6cxg-python3.14-pyyaml-6.0.3/lib/python3.14/site-packages'
    import sys
    sys.path.insert(0,sys_path)
    import yaml
    model=normalize(yaml.safe_load(live['merged']))
    candidate_model=application_compose(model)
    decode=lambda p:base64.b64decode(live['files'][p]).decode()
    original=decode(ROOTS['nuc']+'/backup/Caddyfile')
    assert adapt_ingress(original)[0]==decode(RUNTIME+'/Caddyfile'),'Current ingress changed beyond frozen migration'
    config=tomllib.loads((ROOT/'deploy/instances/home.toml').read_text())
    caddy,contract=candidate_ingress(original,config)
    transport=candidate_readonly_transport(decode(RUNTIME+'/haproxy.readonly.cfg'))
    auth=decode('/home/liou/.config/dufs-plus/secrets/caddy_lan_basic_auth').strip()+'\n'
    assert re.fullmatch(r'[A-Za-z0-9_.-]+\s+\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}\n',auth)
    contents={'application-compose.json':json.dumps(candidate_model,sort_keys=True,indent=2)+'\n',
              'Caddyfile':caddy,'haproxy.readonly.cfg':transport}
    reviewed={RUNTIME+'/'+name:hashlib.sha256(value.encode()).hexdigest() for name,value in contents.items()}
    for role in ['private','readonly']:
        for name,value in [('application-entry.toml',(Path(candidate)/(role+'-entry.toml')).read_text()),('basic.entries',auth)]:
            if role == 'readonly' and name == 'application-entry.toml': value = compatible_readonly_source(value)
            contents[role+'-'+name]=value
            reviewed[ROOTS['nuc']+'/'+role+'/config/'+name]=hashlib.sha256(value.encode()).hexdigest()
    control=rebind_startup_control(live['control'],reviewed)
    contents['native-nuc-control.json']=json.dumps(control,sort_keys=True,indent=2)+'\n'
    manifest={'schema_version':1,'stage':'E5/P1','candidate':candidate,'closure':closure,'units':frozen['nuc']['units'],
              'inventory_sha256':digest(SPEC/'entry-inventory-results.json'),'handover_sha256':digest(SPEC/'entry-handover-results.json'),
              'startup_control_before_sha256':live['control_sha256'],'live_inventory':live['inventory'],
              'files':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in contents.items()},
              'source_manifest':{'scripts/prepare-application-entry.py':digest(Path(__file__))},
              'pc':{**frozen['pc'],'observed_rollback_system':current_pc},
              'state_policy':'reuse-current-database-metadata-ca-and-identity-no-restore',
              'offline_backup_required_in_P2':True,'backup_scope':['private/state','readonly/state','existing-caddy-pki','current-runtime-config-and-units'],
              'backup_is_offline_and_never_rollback_restore':True,
              'activation_order':['fresh-editor-confirmation','stop-current-writers-and-conflicting-entry','offline-backup-current-state',
                                  'install-hash-reviewed-config-and-seven-units','start-files-tools-core-before-recreate-caddy-and-readonly-gateway',
                                  'verify-LAN-private-readonly-and-peer'],
              'removed_unit':'tag-nuc-bridge.service','unmodified_services':['authelia','ddns-go'],
              'application_contract':contract,'activated':False}
    data=json.dumps(manifest,sort_keys=True,indent=2)+'\n';release_id=hashlib.sha256(data.encode()).hexdigest()
    destination=REMOTE+'/'+release_id
    report={k:manifest[k] for k in ['stage','candidate','startup_control_before_sha256','live_inventory','pc','state_policy','activated']}
    report.update(manifest_sha256=release_id,closure_paths=len(closure),prepared_release=destination,
                  live_configuration_reviewed=True,credentials_output=False,production_database_read=False,production_service_changed=False,
                  transfer_completed=False,configuration_staged=False)
    if opts.prepare:
        trusted=command(SSH+['nix config show trusted-users']).split();assert 'liou' in trusted
        command(['nix','copy','--no-check-sigs','--to','ssh-ng://'+HOST,candidate],env=dict(os.environ,NIX_SSHOPTS='-F /home/liou/.ssh/config'))
        received=normalize_closure(json.loads(command(SSH+[shlex.join(['nix','path-info','--recursive','--json',candidate])])))
        assert received==closure
        remote("import os,pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(mode=0o700,exist_ok=True);assert p.parent.stat().st_uid==os.getuid() and p.parent.stat().st_mode&0o777==0o700 and not p.parent.is_symlink();p.mkdir(mode=0o700)",destination)
        with tempfile.TemporaryDirectory(prefix='entry-release-private-') as temp:
            local=Path(temp)
            for name,value in {**contents,'manifest.json':data}.items():
                path=local/name;path.write_text(value);path.chmod(0o600)
            command(['scp','-F','/home/liou/.ssh/config',*[str(p) for p in local.iterdir()],HOST+':'+destination+'/'])
        remote("import hashlib,json,pathlib,sys;p=pathlib.Path(sys.argv[1]);m=json.loads((p/'manifest.json').read_text());assert set(x.name for x in p.iterdir())==set(m['files'])|{'manifest.json'};assert hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest()==sys.argv[2];assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==sha for n,sha in m['files'].items());[(x.chmod(0o600)) for x in p.iterdir()]",destination,release_id)
        command(SSH+[shlex.join(['nix-store','--add-root',destination+'/candidate','--indirect','--realise',candidate])])
        report.update(transfer_completed=True,configuration_staged=True,remote_closure_verified=True)
    # Only sanitized receipt is written locally; live configuration/credentials stay in private staging.
    output=PRODUCT/'.devenv/application-entry-preparation-results.json'
    output.write_text(json.dumps(report,indent=2)+'\n');output.chmod(0o644)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    try:main()
    except Exception as error:
        if not isinstance(error,RuntimeError):
            private_diagnostic(type(error).__name__+': '+str(error))
        print('Preparation refused: '+type(error).__name__+'; private diagnostic content withheld',file=__import__('sys').stderr)
        raise SystemExit(1)
