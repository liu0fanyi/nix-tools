#!/usr/bin/env python3
"""Real temporary user-manager gate. Synthetic inventory only; no production Podman."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from native_nuc_startup import unit_dropins
from native_nuc_bundle import UNITS
from native_nuc_plan import PREFIX,REPLACE,KEEP

SOURCE=Path(__file__).resolve().parent

def run(argv,check=True):
    return subprocess.run(argv,check=check,capture_output=True,text=True,timeout=40)

def main():
    prefix='tag-nuc-startup-check-'+uuid.uuid4().hex[:10]+'-'
    mapping={n:prefix+n for n in UNITS}
    keeper=prefix+'keepers.service'
    names=[*mapping.values(),keeper]
    links=Path.home()/'.config/systemd/user'
    for n in names:
        if (links/n).exists() or (links/n).is_symlink():raise ValueError('Owned unit collision')
    with tempfile.TemporaryDirectory(prefix='nuc-startup-gate-') as tmp:
        root=Path(tmp);root.chmod(0o700)
        def write(name,text):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);path.chmod(0o600);return path
        records={}
        for service in REPLACE+KEEP:
            role='readonly' if service=='tag-server-readonly' else 'private'
            name=PREFIX+service+'_1'
            records[name]={'Name':name,'Image':'a'*64,'Config':{'Labels':{'io.podman.compose.project':'dufs-plus'},'Cmd':['--database','/data/core.db']},'State':{'Running':service in KEEP},'HostConfig':{'RestartPolicy':{'Name':'no' if service in REPLACE else 'unless-stopped'}},'Mounts':[{'Type':'bind','Destination':'/data','Source':str(root/role/'state')}]}
        write('inventory.json',json.dumps(list(records.values())))
        (root/'readonly-workspace').mkdir(mode=0o700)
        write('startup-mode','native\n');write('startup.lock','');write('ready','offline-double-snapshot-complete\n')
        write('backup/source-images.json',json.dumps({n:'a'*64 for n in records}))
        config={'root':str(root),'source_images':{n:'a'*64 for n in records},'compose':['fixture-compose'], 'unit_mapping':mapping}
        write('fixture.json',json.dumps(config))
        driver=write('driver.py',
            'import json,sys,subprocess\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(SOURCE))+')\n'
            'from native_nuc_startup import dispatch\nroot=Path('+repr(str(root))+')\nconfig=json.loads((root/"fixture.json").read_text())\n'
            'def invoke(argv,check=True,capture_output=True):\n'
            ' if argv[:2]==["podman","inspect"]:return subprocess.CompletedProcess(argv,0,(root/"inventory.json").read_text(),"")\n'
            ' if argv[0]=="fixture-compose":\n'
            '  with (root/"compose-calls.jsonl").open("a") as file:file.write(json.dumps(argv)+"\\n")\n'
            '  return subprocess.CompletedProcess(argv,0,"","")\n'
            ' if argv[:3]==["systemctl","--user","show"]:argv[3]=config["unit_mapping"][argv[3]]\n'
            ' return subprocess.run(argv,check=check,capture_output=capture_output,text=True,timeout=20)\n'
            'with (root/"guard-namespaces.jsonl").open("a") as file:file.write(json.dumps({"uid":__import__("os").getuid(),"namespace":__import__("os").readlink("/proc/self/ns/user")})+"\\n")\n'
            'try:sys.exit(dispatch(config,sys.argv[1:],invoke))\nexcept Exception as e:print(type(e).__name__+": "+str(e),file=sys.stderr);sys.exit(1)\n')
        drops=unit_dropins([sys.executable,str(driver)])
        for original,name in mapping.items():
            if original.endswith('.service'):
                write(name,'[Unit]\nPartOf='+mapping['tag-native-nuc.target']+'\n[Service]\nPrivateUsers=yes\nBindReadOnlyPaths='+str(root/'readonly-workspace')+'\nExecStart=/run/current-system/sw/bin/sleep 600\n'+drops[original].replace('dufs-plus-compose.service',keeper))
            else:
                write(name,'[Unit]\nWants='+' '.join(n for n in mapping.values() if n.endswith('.service'))+'\n'+drops[original].replace('dufs-plus-compose.service',keeper))
        write(keeper,'[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart='+shlex.join([sys.executable,str(driver),'compose','up','-d'])+'\n')
        cases=[]
        try:
            run(['systemctl','--user','link',*[str(root/n) for n in names]])
            run(['systemctl','--user','daemon-reload'])
            run(['systemctl','--user','start',mapping['tag-native-nuc.target']])
            for name in names:assert run(['systemctl','--user','is-active',name]).stdout.strip()=='active',name
            calls=[json.loads(line) for line in (root/'compose-calls.jsonl').read_text().splitlines()]
            assert calls==[['fixture-compose','up','-d','--no-deps',*KEEP]]
            cases.append('real target boot starts seven guarded services and only four retained containers')
            host_namespace=os.readlink('/proc/self/ns/user')
            prechecks=[json.loads(line) for line in (root/'guard-namespaces.jsonl').read_text().splitlines()]
            assert len(prechecks)==8 and all(row['uid']==os.getuid() and row['namespace']==host_namespace for row in prechecks),(host_namespace,prechecks)
            for name in mapping.values():
                if not name.endswith('.service'):continue
                pid=run(['systemctl','--user','show',name,'--property=MainPID','--value']).stdout.strip()
                assert os.readlink('/proc/'+pid+'/ns/user')!=host_namespace
            cases.append('guard runs as existing user in host namespace; seven actual service user namespaces remain isolated')
            run(['systemctl','--user','stop',*mapping.values()])
            for service in REPLACE:
                records[PREFIX+service+'_1']['State']['Running']=True
                write('inventory.json',json.dumps(list(records.values())))
                for name in mapping.values():
                    if not name.endswith('.service'):continue
                    assert run(['systemctl','--user','start',name],check=False).returncode!=0,(service,name)
                    assert run(['systemctl','--user','is-active',name],check=False).stdout.strip()=='failed'
                records[PREFIX+service+'_1']['State']['Running']=False
            cases.append('each of five old application writers blocks all seven native service starts')
            write('inventory.json',json.dumps(list(records.values())))
            write('startup-mode','transition\n')
            assert run([sys.executable,str(driver),'compose','up','-d'],check=False).returncode!=0
            for name in mapping.values():
                if name.endswith('.service'):assert run(['systemctl','--user','start',name],check=False).returncode!=0
            cases.append('persistent transition blocks both startup paths')
            write('startup-mode','native\n')
            run(['systemctl','--user','reset-failed',*[n for n in mapping.values() if n.endswith('.service')]])
            run(['systemctl','--user','start',mapping['tag-native-nuc.target']])
            for name in names:assert run(['systemctl','--user','is-active',name]).stdout.strip()=='active'
            cases.append('native target recovers after blockers clear')
            write('startup-mode','container\n');write('container-mode','explicit-container-fallback\n')
            assert run([sys.executable,str(driver),'compose','start'],check=False).returncode!=0
            run(['systemctl','--user','stop',*names])
            run([sys.executable,str(driver),'compose','start'])
            records[PREFIX+'tag-server_1']['Mounts'][0]['Source']='/stale/source/state'
            write('inventory.json',json.dumps(list(records.values())))
            assert run([sys.executable,str(driver),'compose','start'],check=False).returncode!=0
            cases.append('fallback requires every native unit stopped and new state mounts')
        finally:
            run(['systemctl','--user','stop',*names],check=False)
            for n in names:
                link=links/n
                if link.is_symlink() and link.resolve()==root/n:link.unlink()
                elif link.exists():raise ValueError('Refusing cleanup of an unowned unit')
            run(['systemctl','--user','daemon-reload'])
            run(['systemctl','--user','reset-failed',*names],check=False)
            assert all(not (links/n).exists() and not (links/n).is_symlink() for n in names)
        report={'schema_version':1,'cases':cases,'real_user_manager':True,'old_container_inventory':'synthetic only',
            'temporary_units_cleaned':True,'production_units_installed':False,'production_services_changed':False,
            'input_sha256':{str(p.relative_to(SOURCE.parent)):__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in [SOURCE/'native_nuc_startup.py',SOURCE/'native_nuc_guard.py',SOURCE/'check-native-nuc-startup.py',SOURCE.parent/'deploy/scripts/render.py',SOURCE.parent/'deploy/scripts/manage.py',SOURCE.parent/'deploy/scripts/release_pc.py']}}
    out=SOURCE.parent/'.devenv/native-nuc-startup-results.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
