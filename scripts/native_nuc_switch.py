"""Fixed NUC cutover controller. Never automatically restores an old database."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time
import tomllib
import uuid
from native_nuc_bundle import UNITS,digest
from native_nuc_guard import validate
from native_nuc_ingress import adapt_ingress
from native_nuc_plan import PREFIX,REPLACE,KEEP,make_plan
from native_nuc_snapshot import snapshot
from native_nuc_startup import ROOT,CONTROL,host_environment,lock,read_inventory,unit_dropins
from native_pc_snapshot import private_file
RUNTIME=CONTROL.parent
STOPPED={'inactive','failed','unknown'}


def atomic_file(path,data,mode=0o600):
    path=Path(path)
    if path.is_symlink():raise ValueError('Refusing symlink destination')
    temporary=path.with_name(path.name+'.pending-'+uuid.uuid4().hex)
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data.encode() if isinstance(data,str) else data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if temporary.exists():temporary.unlink()


def fallback_overlay(records,root):
    # Verify actual merged mounts/commands before any fallback process starts.
    services={s:{'image':'sha256:'+records[PREFIX+s+'_1']['Image'].removeprefix('sha256:')} for s in REPLACE+KEEP}
    for service,role in [('tag-server','private'),('tag-server-readonly','readonly'),('tag-peer-discovery','private')]:
        command=records[PREFIX+service+'_1']['Config']['Cmd']
        if service!='tag-peer-discovery':
            if sum(a.count('/data/tag_all.db') for a in command)!=1:raise ValueError('Expected one fixed original database command')
            command=[a.replace('/data/tag_all.db','/data/core.db') for a in command]
        services[service].update(command=command,volumes=[str(Path(root)/role/'state')+':/data:rw'])
    for service in REPLACE:services[service]['restart']='no'
    return {'services':services}


def native_overlay(records,root):
    result={'services':{s:{'image':'sha256:'+records[PREFIX+s+'_1']['Image'].removeprefix('sha256:')} for s in REPLACE+KEEP}}
    for service in REPLACE:result['services'][service]['restart']='no'
    result['services']['caddy']['volumes']=[str(Path(root)/'sockets')+':/run/tag-native:ro']
    return result


def hook_control(original,hook):
    lines=original.splitlines(keepends=True)
    if not original.startswith('#!/bin/sh\nset -eu\n') or not lines[-1].startswith('exec ') or not lines[-1].rstrip().endswith('"$@"'):
        raise ValueError('Unknown original Compose startup script')
    # Preserve required disk checks; replace only the unrestricted final invocation.
    return ''.join(lines[:-1])+'exec '+shlex.quote(str(hook))+' compose "$@"\n'


class Controller:
    # Trusted local assembly inputs; production CLI accepts only the fixed prepared release.
    def __init__(self,release,manifest,config,run,*,root=ROOT,runtime=RUNTIME,units_dir=None,python=None,management_dir=None):
        self.release=Path(release);self.manifest=manifest;self.config=config;self.run=run
        self.root=Path(root);self.runtime=Path(runtime)
        self.units_dir=Path(units_dir or Path.home()/'.config/systemd/user')
        self.management_dir=Path(management_dir or '/media/liou/project/me/nix-tools/deploy/scripts')
        self.python=python or sys.executable;self.source_images=manifest['source_images']
        self.journal=self.release/'transaction.json';self.saved=self.release/'runtime-backup'
    def inventory(self):return read_inventory(self.run)
    def phase(self,name,**values):
        previous=json.loads(self.journal.read_text()) if self.journal.exists() else {}
        previous.update(phase=name,**values);atomic_file(self.journal,json.dumps(previous,sort_keys=True)+'\n')
    def mode(self,value):
        with lock(self.root/'startup.lock'):atomic_file(self.root/'startup-mode',value+'\n')
    def compose(self,files):
        argv=['podman','compose','--env-file',str(self.runtime/'compose.env')]
        for path in files:argv.extend(['-f',str(path)])
        return argv
    def checked_input(self,path):
        path=Path(path)
        if path==self.runtime/'compose-files.txt':
            # Renderer historically emits this non-secret filename list with the host umask.
            if path.is_symlink() or not path.is_file() or path.stat().st_uid!=os.getuid():
                raise ValueError('Owned regular Compose filename list required')
        else:private_file(path)
    def base_files(self):
        self.checked_input(self.runtime/'compose-files.txt')
        files=[Path(p) for p in (self.runtime/'compose-files.txt').read_text().splitlines() if p]
        if not files or len(set(files))!=len(files):raise ValueError('Complete unique Compose input list required')
        for p in files:
            if p.parent!=self.runtime:raise ValueError('Compose input outside fixed runtime')
            private_file(p)
        private_file(self.runtime/'compose.env');return files
    def pinned_inputs(self):
        files=[*self.base_files(),self.runtime/'compose-files.txt',self.runtime/'compose.env',self.runtime/'Caddyfile',self.runtime/'tag-server.toml',*[Path(self.config['paths']['secrets'])/n for n in ['tag-server.env','tag-peer-admin.env']]]
        for p in files:self.checked_input(p)
        return {str(p):digest(p) for p in files}
    def check_inputs(self):
        private_file(self.saved/'inputs.json')
        for path,expected in json.loads((self.saved/'inputs.json').read_text()).items():
            if Path(path).name!='Caddyfile' and digest(path)!=expected:raise ValueError('Original runtime input changed')
    def startup_config(self,files):
        inputs=self.pinned_inputs()
        for path in files:inputs[str(path)]=digest(path)
        data={'root':str(self.root),'hostname':'nuc','uid':1000,'files':inputs,'compose':self.compose(files),'source_images':self.source_images}
        atomic_file(self.runtime/'native-nuc-control.json',json.dumps(data,sort_keys=True)+'\n')
    def wait_stopped(self,native=False):
        for attempt in range(60):
            records,units=self.inventory()
            stopped=all(v in STOPPED for v in units.values()) if native else all(not records[PREFIX+s+'_1']['State']['Running'] for s in REPLACE)
            if stopped:return records,units
            time.sleep(1)
        raise ValueError('Complete stop timed out; target status alone is insufficient')
    def verify_offline(self):
        records,units=self.inventory();validate('snapshot',self.root,records,units,source_images=self.source_images)
    def plan(self):
        if self.journal.exists():
            private_file(self.journal)
            return {'target':'nuc','dry_run':True,'phase':json.loads(self.journal.read_text())['phase'],'rollback_reads':'both migrated core.db files; no old DB restoration','root':str(self.root),'production_changes':False}
        records,units=self.inventory();make_plan(self.config,list(records.values()))
        if {n:r['Image'].removeprefix('sha256:') for n,r in records.items()}!=self.source_images:raise ValueError('Pinned source image mismatch')
        if any(v not in STOPPED for v in units.values()):raise ValueError('All native units must stop')
        if self.root.exists() or self.root.is_symlink():raise ValueError('Destination exists; never resnapshot')
        self.pinned_inputs();fallback_overlay(records,self.root);adapt_ingress((self.runtime/'Caddyfile').read_text())
        for name in UNITS:
            path=Path(self.manifest['candidate'])/'lib/systemd/user'/name
            if digest(path)!=self.manifest['units'][name]:raise ValueError('Pinned candidate unit changed')
            dest=self.units_dir/name
            if dest.exists() or dest.is_symlink() or (self.units_dir/(name+'.d')).exists():raise ValueError('Native registration collision')
        for mount in self.config['paths']['required_mounts']:
            self.run(['timeout','20','stat','--',mount+'/.']);self.run(['findmnt','-rn','-M',mount,'-t','noautofs'])
        return {'target':'nuc','dry_run':True,'candidate':self.manifest['candidate'],'root':str(self.root),'stop_applications':list(REPLACE),'retain_ingress':list(KEEP),'actions':['install fail-closed startup barrier','disable old application auto-restart; stop all five','offline double snapshot with metadata/CA','register guarded native units','adapt four Caddy upstreams and readonly socket bind','start and verify all native services','explicit rollback stops all eight units and opens both new core.db files'],'source_database_read':False,'production_changes':False}
    @contextmanager
    def operation(self):
        path=self.release/'operation.lock'
        if not path.exists():
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        with lock(path):yield
    def backup_runtime(self,records):
        self.saved.mkdir(mode=0o700);inputs=self.pinned_inputs()
        for path in inputs:atomic_file(self.saved/Path(path).name,Path(path).read_bytes())
        original=self.runtime/'compose-control'
        if original.is_symlink() or original.stat().st_uid!=os.getuid():raise ValueError('Owned original Compose script required')
        atomic_file(self.saved/'compose-control',original.read_bytes());atomic_file(self.saved/'inputs.json',json.dumps(inputs)+'\n')
        # Never retain Config.Env. Required command/mount data stays private outside served roots.
        minimal={n:{'Name':r['Name'],'Image':r['Image'],'Config':{'Cmd':r['Config']['Cmd'],'Labels':r['Config']['Labels']},'Mounts':r['Mounts'],'State':r['State'],'HostConfig':r['HostConfig']} for n,r in records.items()}
        atomic_file(self.saved/'inventory.json',json.dumps(minimal)+'\n')
    def install_barrier(self):
        hook=self.runtime/'native-nuc-control'
        atomic_file(hook,'#!/bin/sh\nset -eu\nexec '+shlex.join([self.python,str(self.release/'native_nuc_startup.py')])+' "$@"\n',0o700)
        # Preserve the original list privately, then publish the identical bytes as 600.
        atomic_file(self.runtime/'compose-files.txt',(self.runtime/'compose-files.txt').read_bytes())
        self.startup_config(self.base_files())
        atomic_file(self.runtime/'compose-control',hook_control((self.saved/'compose-control').read_text(),hook),0o700)
        for name in ['render.py','manage.py']:
            dest=self.management_dir/name
            if dest.is_symlink() or dest.stat().st_uid!=os.getuid():raise ValueError('Owned production management script required')
            atomic_file(self.saved/('management-'+name),dest.read_bytes())
            atomic_file(dest,(self.release/name).read_bytes(),dest.stat().st_mode&0o777)
        self.phase('startup-barrier-installed',native_may_have_written=False)
    def register(self):
        self.units_dir.mkdir(parents=True,exist_ok=True);source=Path(self.manifest['candidate'])/'lib/systemd/user'
        for name,text in unit_dropins([self.python,str(self.release/'native_nuc_startup.py')]).items():
            dest=self.units_dir/name
            if dest.exists() or dest.is_symlink():raise ValueError('Native registration collision')
            dest.symlink_to(source/name);folder=self.units_dir/(name+'.d');folder.mkdir(mode=0o700)
            atomic_file(folder/'native-startup.conf',text)
        self.run(['systemctl','--user','daemon-reload']);self.run(['systemctl','--user','enable','tag-native-nuc.target']);self.phase('native-registered')
    def caddy(self,original,desired,files):
        self.check_inputs();path=self.runtime/'Caddyfile'
        if path.read_bytes()!=original:raise ValueError('Caddy changed; refusing overwrite')
        bridge=(Path(self.manifest['candidate'])/'lib/systemd/user/tag-nuc-bridge.service').read_text()
        binary=shlex.split(next(line.split('=',1)[1] for line in bridge.splitlines() if line.startswith('ExecStart=')))[0]
        check=self.release/'Caddyfile-check';atomic_file(check,desired)
        self.run([binary,'adapt','--config',str(check),'--adapter','caddyfile'])
        atomic_file(path,desired);self.startup_config(files)
        self.run([*self.compose(files),'up','-d','--no-deps','--force-recreate','caddy'])
        records,_=self.inventory();item=records[PREFIX+'caddy_1']
        if item['Image'].removeprefix('sha256:')!=self.source_images[PREFIX+'caddy_1']:raise ValueError('Caddy image changed')
        expected={m['Destination']:(m['Source'],m['RW']) for m in json.loads((self.saved/'inventory.json').read_text())[PREFIX+'caddy_1']['Mounts']}
        actual={m['Destination']:(m['Source'],m['RW']) for m in item['Mounts']}
        for dest,value in expected.items():
            if actual.get(dest)!=value:raise ValueError('Original Caddy mount changed')
        if actual.get('/run/tag-native')!=(str(self.root/'sockets'),False):raise ValueError('Socket mount must be the private readonly bind')
    def activate(self):
        with self.operation():
            if self.journal.exists():raise ValueError('Transaction exists; never repeat snapshot or implicit rollback')
            self.plan();records,_=self.inventory();self.backup_runtime(records);self.phase('prepared',native_may_have_written=False);self.install_barrier()
            for s in REPLACE:self.run(['podman','stop','--time','60',PREFIX+s+'_1'])
            self.wait_stopped()
            # Updating a stopped container avoids an unrelated rootless cgroup resource update.
            for s in REPLACE:self.run(['podman','update','--restart=no',PREFIX+s+'_1'])
            self.verify_offline();self.phase('old-applications-stopped')
            paths=self.config['paths']
            roles={role:{'mounts':{m['Destination']:m['Source'] for m in records[PREFIX+service+'_1']['Mounts'] if m['Type']=='bind'}} for role,service in [('private','tag-server'),('readonly','tag-server-readonly')]}
            snapshot(self.root,roles,source_config=self.runtime/'tag-server.toml',discovery_args=records[PREFIX+'tag-peer-discovery_1']['Config']['Cmd'],environment_files=[Path(paths['secrets'])/'tag-server.env',Path(paths['secrets'])/'tag-peer-admin.env'],caddyfile=self.runtime/'Caddyfile',pki=Path(paths['caddy_data'])/'pki',whisper_package=self.manifest['whisper_package'],models=paths['whisper_models'],source_images=self.source_images,ensure_offline=self.verify_offline)
            atomic_file(self.root/'startup.lock','');atomic_file(self.root/'startup-mode','transition\n');self.phase('double-snapshot-ready');self.register()
            native=self.root/'config-native.json';fallback=self.root/'config-fallback.json'
            atomic_file(native,json.dumps(native_overlay(records,self.root))+'\n');atomic_file(fallback,json.dumps(fallback_overlay(records,self.root))+'\n')
            original=(self.root/'backup/Caddyfile').read_bytes();adapted=adapt_ingress(original.decode())[0].encode();files=[*self.base_files(),native]
            self.caddy(original,adapted,files);self.phase('native-ingress-ready')
            # Never hold startup exclusive lock while waiting for shared systemd prechecks.
            self.phase('native-starting',native_may_have_written=True);self.mode('native')
            self.run(['systemctl','--user','reset-failed',*[n for n in UNITS if n.endswith('.service')]],check=False)
            self.run(['systemctl','--user','start','tag-native-nuc.target'])
            records,units=self.inventory();validate('native',self.root,records,units,source_images=self.source_images)
            if any(v!='active' for v in units.values()):raise ValueError('All eight native units must be active')
            self.phase('native-active');return {'mode':'native','activated':True,'old_databases_restored':False,'all_native_units_active':True}
    def resume_migrated(self):
        """Re-enter native mode after reviewed fallback, using both current migrated DBs."""
        with self.operation():
            private_file(self.journal)
            if json.loads(self.journal.read_text())['phase']!='container-active':raise ValueError('Reviewed active new-state fallback required')
            self.check_inputs();records,units=self.inventory()
            validate('container',self.root,records,units,source_images=self.source_images)
            original=(self.root/'backup/Caddyfile').read_bytes()
            if (self.runtime/'Caddyfile').read_bytes()!=original:raise ValueError('Unexpected fallback ingress edits')
            for name in UNITS:
                if digest(Path(self.manifest['candidate'])/'lib/systemd/user'/name)!=self.manifest['units'][name]:raise ValueError('Candidate unit changed')
                if (self.units_dir/name).resolve()!=Path(self.manifest['candidate'])/'lib/systemd/user'/name:raise ValueError('Registered unit changed')
            self.mode('transition');self.phase('resuming-migrated')
            for service in REPLACE:self.run(['podman','stop','--time','60',PREFIX+service+'_1'])
            self.wait_stopped();self.verify_offline()
            for service in REPLACE:self.run(['podman','update','--restart=no',PREFIX+service+'_1'])
            hook=self.runtime/'native-nuc-control'
            atomic_file(hook,'#!/bin/sh\nset -eu\nexec '+shlex.join([self.python,str(self.release/'native_nuc_startup.py')])+' "$@"\n',0o700)
            for name,text in unit_dropins([self.python,str(self.release/'native_nuc_startup.py')]).items():
                dest=self.units_dir/(name+'.d')/'native-startup.conf';private_file(dest)
                atomic_file(self.saved/('previous-'+name+'.conf'),dest.read_bytes())
                atomic_file(dest,text)
            marker=self.root/'container-mode';private_file(marker)
            if marker.read_text()!='explicit-container-fallback\n':raise ValueError('Explicit migrated fallback marker required')
            marker.unlink()
            files=[*self.base_files(),self.root/'config-native.json']
            self.caddy(original,adapt_ingress(original.decode())[0].encode(),files)
            self.run(['systemctl','--user','daemon-reload']);self.run(['systemctl','--user','enable','tag-native-nuc.target'])
            self.phase('native-starting',native_may_have_written=True);self.mode('native')
            self.run(['systemctl','--user','reset-failed',*UNITS],check=False)
            self.run(['systemctl','--user','start','tag-native-nuc.target'])
            for attempt in range(60):
                records,units=self.inventory();validate('native',self.root,records,units,source_images=self.source_images)
                if all(value=='active' for value in units.values()):break
                time.sleep(1)
            else:raise ValueError('Native resume did not become active')
            self.phase('native-active');return {'mode':'native','activated':True,'both_existing_migrated_databases_reused':True,'source_resnapshot':False,'all_native_units_active':True}
    def rollback(self):
        with self.operation():
            private_file(self.journal)
            if json.loads(self.journal.read_text())['phase']=='container-active':raise ValueError('Container fallback already active; no actions needed')
            if not self.root.exists():raise ValueError('No complete migrated state; explicit pre-native recovery required')
            self.check_inputs();original=(self.root/'backup/Caddyfile').read_bytes();adapted=adapt_ingress(original.decode())[0].encode()
            if (self.runtime/'Caddyfile').read_bytes() not in [original,adapted]:raise ValueError('New Caddy edits require review before fallback')
            self.mode('transition');self.phase('fallback-stopping');self.run(['systemctl','--user','stop',*UNITS]);self.wait_stopped(native=True)
            self.run(['systemctl','--user','disable','tag-native-nuc.target']);records,units=self.inventory()
            if any(records[PREFIX+s+'_1']['State']['Running'] for s in REPLACE):raise ValueError('Old application running before fallback creation')
            for role in ['private','readonly']:
                database=self.root/role/'state/core.db'
                if database.is_symlink() or not database.is_file():raise ValueError('Both migrated databases required')
            files=[*self.base_files(),self.root/'config-native.json',self.root/'config-fallback.json']
            self.run([*self.compose(files),'up','--no-start','--no-deps','--force-recreate',*REPLACE])
            records,units=self.inventory();atomic_file(self.root/'container-mode','explicit-container-fallback\n');validate('container',self.root,records,units,source_images=self.source_images);self.phase('fallback-created')
            self.caddy((self.runtime/'Caddyfile').read_bytes(),original,files);self.mode('container')
            self.run([*self.compose(files),'start',*REPLACE]);records,units=self.inventory();validate('container',self.root,records,units,source_images=self.source_images)
            if any(not records[PREFIX+s+'_1']['State']['Running'] for s in REPLACE):raise ValueError('All fallback services must run')
            self.phase('container-active');return {'mode':'container','activated':True,'rollback_uses_both_new_databases':True,'old_databases_restored':False}


def load_release(release):
    release=Path(release);expected=Path('/home/liou/.local/share/tag-all/nuc-native-release')
    if release.parent!=expected or not __import__('re').fullmatch('[a-f0-9]{64}',release.name):raise ValueError('Fixed prepared release required')
    if socket.gethostname()!='nuc' or os.getuid()!=1000:raise ValueError('Wrong NUC host/user')
    if release.is_symlink() or release.stat().st_uid!=os.getuid() or release.stat().st_mode&0o777!=0o700:raise ValueError('Private release directory required')
    private_file(release/'manifest.json')
    if digest(release/'manifest.json')!=release.name:raise ValueError('Manifest identity mismatch')
    manifest=json.loads((release/'manifest.json').read_text())
    for name,sha in manifest['controls'].items():
        if Path(name).name!=name:raise ValueError('Invalid control filename')
        private_file(release/name)
        if digest(release/name)!=sha:raise ValueError('Pinned control changed')
    if digest(release/'home.toml')!=manifest['instance_sha256']:raise ValueError('Fixed instance changed')
    return manifest,tomllib.loads((release/'home.toml').read_text())


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('release',type=Path)
    action=parser.add_mutually_exclusive_group();action.add_argument('--activate',action='store_true');action.add_argument('--rollback',action='store_true');action.add_argument('--resume',action='store_true')
    parser.add_argument('--editors-closed',action='store_true',help='Explicit acknowledgement before interruption')
    args=parser.parse_args()
    def run(argv,check=True,capture_output=True):return subprocess.run(argv,check=check,capture_output=capture_output,text=True,timeout=300,env=host_environment(os.environ))
    try:
        manifest,config=load_release(args.release);controller=Controller(args.release,manifest,config,run)
        if args.activate or args.rollback or args.resume:
            if not args.editors_closed:raise ValueError('Save and close editors before activation or fallback')
            result=controller.activate() if args.activate else controller.resume_migrated() if args.resume else controller.rollback()
        else:result=controller.plan()
        print(json.dumps(result,indent=2));return 0
    except (ValueError,KeyError,OSError,subprocess.SubprocessError) as error:
        print('NUC switch stopped: '+(str(error) if isinstance(error,ValueError) else type(error).__name__)+'. Keep transaction and snapshots; no automatic old writer restart or DB restore.',file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
