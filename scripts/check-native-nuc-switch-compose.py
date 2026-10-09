#!/usr/bin/env python3
"""Actual isolated Compose and fixed old/new CLI gate. No production database or runtime."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).parent/'tests'))
from test_native_nuc_switch import Switch
from native_nuc_switch import atomic_file,native_overlay,fallback_overlay
from native_nuc_snapshot import snapshot
from native_nuc_guard import validate
from native_nuc_plan import PREFIX,REPLACE,KEEP
from native_nuc_bundle import UNITS,digest
sys.path.insert(0,'/data/project/tag-all/scripts')
from native_tool_runtime import runtime
IMAGE='2d8b1708bf8008935c0e2a9b6564f7f080cf9a73af3b27718f286230449b7101'
LEGACY='/nix/store/6fqry14ldg45lvxkh4y7wsfgc60zzpa4-tag-private-tested-artifacts/app/tag-server'
NATIVE='/nix/store/irhihmrj1vb3a8avmjvq4kczgnl14zcw-tag-all-workspace-native-0.1.0/libexec/tag-server-workspace'
PROVIDER='/etc/profiles/per-user/liou/bin/podman-compose'


def call(argv,timeout=90):
    result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr)[-3500:])
    return result


def main():
    assert digest(LEGACY)=='d729c3a764ca182cf2fd1aa01bf15f2f59f71a8f60df8abfdc3e833d8d66fa51'
    assert digest(NATIVE)=='c6907e9829ddb1c49dcf0271b6c573616b42a5e72a40b4055935143cab73b659'
    h=Switch();h.setUp();cases=[];processes=[]
    try:
        root=h.root;archive=root/'caddy.tar'
        call(['podman','--remote','--url','unix:///run/user/1000/podman/podman.sock','save','--output',str(archive),IMAGE],180)
        project='nuc-switch-gate-'+uuid.uuid4().hex[:10]
        role_config=root/'isolated.toml';atomic_file(role_config,'[node]\nid="isolated-nuc-switch"\n[sync]\nenabled=false\n[pairing]\nenabled=false\n[discovery]\nenabled=false\n')
        atomic_file(h.runtime/'tag-server.toml','[node]\nid="nuc"\n[sync]\nenabled=false\n[pairing]\nenabled=false\n[discovery]\nenabled=false\n')
        services={}
        for service,item in h.records.items():
            s=service[len(PREFIX):-2]
            command='exec /bin/busybox sleep 600'
            mounts=[m['Source']+':'+m['Destination']+(':'+('rw' if m['RW'] else 'ro')) for m in item['Mounts']]
            if s in ['tag-server','tag-server-readonly']:
                mounts += [LEGACY+':/fixture-legacy:ro',str(role_config)+':/fixture-config:ro']
                command='exec /fixture-legacy --database /data/tag_all.db --metadata-dir /data/metadata --workspace /workspace --config /fixture-config --disable-sync --addr 127.0.0.1:8081'
            services[s]={'image':'sha256:'+IMAGE,'entrypoint':['/bin/sh','-ec'],'command':[command],'network_mode':'none','restart':'no','volumes':mounts}
        base=root/'base.json';atomic_file(base,json.dumps({'services':services}));env=root/'compose.env';atomic_file(env,'COMPOSE_PROJECT_NAME='+project+'\n')
        with runtime(root,archive,IMAGE) as connection:
            engine=['podman','--remote','--url',connection]
            wrapper=root/'podman-owned'
            atomic_file(wrapper,'#!/bin/sh\nexec '+shlex.join(engine)+' \"$@\"\n',0o700)
            def compose(files,action):
                argv=[PROVIDER,'--podman-path',str(wrapper),'--env-file',str(env),'-p',project]
                for p in files:argv+=['-f',str(p)]
                return call(argv+action,180)
            def inventory():
                actual=json.loads(call(engine+['inspect',*[project+'_'+s+'_1' for s in REPLACE+KEEP]]).stdout)
                records={}
                for r in actual:
                    assert r['Config']['Labels']['io.podman.compose.project']==project
                    r['Name']=PREFIX+r['Name'][len(project)+1:];r['Config']['Labels']['io.podman.compose.project']='dufs-plus'
                    records[r['Name']]=r
                return records
            def old_tags(service,name=None):
                argv=engine+['exec',project+'_'+service+'_1','/bin/busybox','wget','-q','-O','-','--timeout=3']
                if name:argv+=['--header','Content-Type: application/json','--post-data',json.dumps({'name':name})]
                return call(argv+['http://127.0.0.1:8081/tags'],8).stdout
            try:
                compose([base],['up','-d','--no-deps',*REPLACE,*KEEP])
                for s in ['tag-server','tag-server-readonly']:
                    for _ in range(150):
                        try:old_tags(s);break
                        except (subprocess.CalledProcessError,RuntimeError):time.sleep(.1)
                    else:raise ValueError('Isolated source CLI failed to become ready')
                    old_tags(s,'before-'+s)
                records=inventory();images={n:IMAGE for n in records}
                old_ids={s:records[PREFIX+s+'_1']['Id'] for s in KEEP}
                for s in REPLACE:call(engine+['stop','--time','3',project+'_'+s+'_1'],20)
                for s in REPLACE:call(engine+['update','--restart=no',project+'_'+s+'_1'])
                print('Owned source applications stopped; checking double snapshot',flush=True)
                original={r:digest(Path(v['mounts']['/data'])/'tag_all.db') for r,v in h.roles.items()}
                def offline():validate('snapshot',h.dest,inventory(),dict.fromkeys(UNITS,'inactive'),source_images=images)
                snapshot(h.dest,h.roles,source_config=h.runtime/'tag-server.toml',discovery_args=h.args,environment_files=[root/'secrets/tag-server.env',root/'secrets/tag-peer-admin.env'],caddyfile=h.runtime/'Caddyfile',pki=h.pki,whisper_package='/nix/store/fixture-whisper',models=root/'models',source_images=images,ensure_offline=offline)
                cases.append('actual old CLI containers stop before offline snapshot; both source DB hashes recorded')
                native=root/'native.json';fallback=root/'fallback.json'
                atomic_file(native,json.dumps(native_overlay(records,h.dest)));atomic_file(fallback,json.dumps(fallback_overlay(records,h.dest)))
                compose([base,native],['up','-d','--no-deps','--force-recreate','caddy'])
                changed=inventory()
                for s in KEEP:
                    if s!='caddy':assert changed[PREFIX+s+'_1']['Id']==old_ids[s] and changed[PREFIX+s+'_1']['State']['Running']
                assert all(not changed[PREFIX+s+'_1']['State']['Running'] for s in REPLACE)
                caddy=changed[PREFIX+'caddy_1'];mount=next(m for m in caddy['Mounts'] if m['Destination']=='/run/tag-native')
                assert mount['Source']==str(h.dest/'sockets') and mount['RW'] is False
                for m in records[PREFIX+'caddy_1']['Mounts']:
                    assert any(p['Source']==m['Source'] and p['Destination']==m['Destination'] and p['RW']==m['RW'] for p in caddy['Mounts'])
                cases.append('real scoped Caddy recreation retains all prior binds, adds readonly socket bind, keeps other ingress IDs and does not start old apps')
                import socket
                for role in ['private','readonly']:
                    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
                    log=(root/(role+'-native.log')).open('wb')
                    proc=subprocess.Popen([NATIVE,'--database',str(h.dest/role/'state/core.db'),'--metadata-dir',str(h.dest/role/'state/metadata'),'--workspace',h.roles[role]['mounts']['/workspace'],'--config',str(role_config),'--disable-sync','--addr','127.0.0.1:'+str(port)],stdout=log,stderr=log)
                    log.close();processes.append(proc)
                    url='http://127.0.0.1:'+str(port)+'/tags'
                    for _ in range(150):
                        assert proc.poll() is None,'Owned native CLI exited'
                        try:
                            with urllib.request.urlopen(url,timeout=2) as response:response.read()
                            break
                        except OSError:time.sleep(.1)
                    else:raise ValueError('Owned native CLI readiness failed')
                    request=urllib.request.Request(url,data=json.dumps({'name':'native-new-'+role}).encode(),headers={'Content-Type':'application/json'},method='POST')
                    with urllib.request.urlopen(request,timeout=3) as response:assert response.status==201
                for proc in processes:proc.terminate();assert proc.wait(timeout=15)==0
                processes=[]
                cases.append('both fixed actual native CLIs write new tags to migrated databases and stop')
                compose([base,native,fallback],['up','--no-start','--no-deps','--force-recreate',*REPLACE])
                after=inventory();atomic_file(h.dest/'container-mode','explicit-container-fallback\n')
                validate('container',h.dest,after,dict.fromkeys(UNITS,'inactive'),source_images=images)
                assert all(not after[PREFIX+s+'_1']['State']['Running'] for s in REPLACE)
                for s in KEEP:assert after[PREFIX+s+'_1']['Id']==changed[PREFIX+s+'_1']['Id']
                readonly=after[PREFIX+'tag-server-readonly_1'];assert next(m for m in readonly['Mounts'] if m['Destination']=='/workspace')['RW'] is False
                cases.append('actual no-start fallback create merges new state bind and core.db command; readonly workspace remains OS readonly; ingress untouched')
                compose([base,native,fallback],['start',*REPLACE])
                for s,role in [('tag-server','private'),('tag-server-readonly','readonly')]:
                    for _ in range(150):
                        try:data=old_tags(s);break
                        except (subprocess.CalledProcessError,RuntimeError):time.sleep(.1)
                    else:raise ValueError('Actual fallback failed to become ready')
                    assert 'native-new-'+role in data and 'before-'+s in data
                    assert digest(Path(h.roles[role]['mounts']['/data'])/'tag_all.db')==original[role]
                    assert (h.dest/role/'state/metadata/identity').read_text()==role+'-identity'
                cases.append('actual old container CLIs reopen both migrated databases with native tags; original source DBs and metadata proof unchanged')
            finally:
                for proc in processes:
                    if proc.poll() is None:proc.terminate();proc.wait(timeout=15)
                ids=call(engine+['ps','-aq']).stdout.split()
                if ids:
                    actual=json.loads(call(engine+['inspect',*ids]).stdout)
                    assert all(p['Image'].removeprefix('sha256:')==IMAGE and p['Config']['Labels']['io.podman.compose.project']==project for p in actual)
                    call(engine+['rm','-f',*ids])
                assert not call(engine+['ps','-aq']).stdout.strip()
        report={'schema_version':1,'cases':cases,'source_runtime':'owned rootless VFS only','old_cli_sha256':digest(LEGACY),'native_cli_sha256':digest(NATIVE),'compose_provider':os.path.realpath(PROVIDER),'both_new_databases_reopened':True,'readonly_workspace_preserved':True,'owned_containers_and_runtime_cleaned':True,'production_services_changed':False,'input_sha256':{name:digest(Path(__file__).parent/name) for name in ['check-native-nuc-switch-compose.py','native_nuc_switch.py','native_nuc_snapshot.py','native_nuc_guard.py','native_nuc_startup.py','tests/test_native_nuc_switch.py']}}
        output=Path(__file__).parents[1]/'.devenv/native-nuc-switch-compose-results.json';output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:h.doCleanups()

if __name__=='__main__':main()
