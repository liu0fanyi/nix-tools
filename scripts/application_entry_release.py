"""Application-entry release/preflight helpers. No service control or production apply."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tomllib
from application_nuc_ingress import candidate_ingress, candidate_profile, candidate_readonly_transport

ROOTS={'pc':'/home/liou/.local/share/tag-all/pc-native','nuc':'/home/liou/.local/share/tag-all/nuc-native'}
KEEP={'caddy','authelia','readonly-gateway','ddns-go'}
REMOVED={'dufs','dufs-readonly','tag-server','tag-server-readonly','tag-peer-discovery'}
APP_NAMES={'devices','transcriptions','recorder-bean','bevy-game','bevy-sketch','project-planner','quick-note'}

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def store_path(path):
    path=Path(path)
    if not re.fullmatch(r'/nix/store/[a-z0-9]{32}-[A-Za-z0-9._+-]+',str(path)) or not path.is_dir():
        raise ValueError('Existing immutable store directory required')
    return path

def private_directory(path):
    path=Path(path);info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:
        raise ValueError('Owned private directory required')
    return path

def private_file(path):
    path=Path(path);info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
        raise ValueError('Owned private regular file required')
    return path

def prepare_synthetic_configuration(stage,templates,credentials):
    """Only owned temporary staging; never accept canonical/live roots or replace files."""
    stage=private_directory(stage)
    if stage.parent!=Path('/tmp') and not stage.parent.name=='.devenv':
        raise ValueError('Dry-run staging must be a fresh temporary directory')
    if not stage.name.startswith('entry-update-dry-run-'):
        raise ValueError('Explicit owned dry-run staging required')
    for role,template in templates.items():
        if role not in {'pc','private','readonly'}:raise ValueError('Unknown runtime role')
        parsed=tomllib.loads(template)
        if role!='pc':
            source=private_file(credentials[role]);text=source.read_text()
            if not text or any(not re.fullmatch(r'[A-Za-z0-9_.@-]+\s+\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}',line) for line in text.splitlines()):
                raise ValueError('Existing bcrypt format required')
        for app in parsed.get('applications',[]):
            if app['name'] not in APP_NAMES:raise ValueError('Unknown application binding')
        role_root=stage/role
        role_root.mkdir(mode=0o700) # Refuse reuse, never overwrite previous staging.
        config=role_root/'config';config.mkdir(mode=0o700)
        entry=config/'application-entry.toml'
        fd=os.open(entry,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:out.write(template)
        if role!='pc':
            auth=config/'basic.entries'
            fd=os.open(auth,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as out:out.write(text)
        if parsed.get('applications'):
            apps=role_root/'apps';apps.mkdir(mode=0o700)
            for app in parsed['applications']:(apps/app['name']).mkdir(mode=0o700)
    sockets=stage/'sockets';sockets.mkdir(mode=0o700)
    return {'configuration_mode':600,'parent_mode':700,'database_copy':False,'live_write':False}

def application_compose(merged,root=ROOTS['nuc']):
    """Transform the fully merged model, never rely on additive Compose list overrides."""
    if root!=ROOTS['nuc']:raise ValueError('Fixed NUC state root required')
    result=copy.deepcopy(merged);services=result['services']
    if set(services)!=KEEP|REMOVED:raise ValueError('Complete fixed nine-service input required')
    for name in REMOVED:del services[name]
    caddy=services['caddy']
    for name in KEEP:
        image=services[name]['image']
        if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):raise ValueError('Pinned current image required')
    caddy['entrypoint']=['caddy'];caddy['command']=['run','--config','/etc/caddy/Caddyfile','--adapter','caddyfile']
    dependencies=caddy.get('depends_on',{})
    if isinstance(dependencies,list):caddy['depends_on']=[name for name in dependencies if name not in REMOVED]
    elif isinstance(dependencies,dict):caddy['depends_on']={name:value for name,value in dependencies.items() if name not in REMOVED}
    else:raise ValueError('Unknown dependency structure')
    if set(caddy['depends_on'])!={'authelia'}:raise ValueError('Authelia dependency must remain')
    # Provider-normalized bind objects are required; ambiguous strings are rejected.
    original=caddy.get('volumes',[])
    if any(not isinstance(volume,dict) or volume.get('type')!='bind' for volume in original):raise ValueError('Normalized bind mounts required')
    destinations=[volume['target'] for volume in original]
    if len(set(destinations))!=len(destinations):raise ValueError('Duplicate mounted destination')
    volumes=[v for v in original if v['target'] not in {'/run/secrets/tag-peer-admin.env','/run/host-ttyd','/srv/dist','/run/tag-native'}]
    required={'/etc/caddy/Caddyfile','/data/caddy','/config/caddy'}
    if not required.issubset({v['target'] for v in volumes}):raise ValueError('TLS/state/configuration mounts missing')
    pki=next(v for v in volumes if v['target']=='/data/caddy')
    if pki.get('read_only',False):raise ValueError('Existing Caddy CA state must remain writable')
    # Readonly external credential file is runtime-only, independently from node API authorization.
    secret=next((v['source'] for v in original if v['target']=='/run/secrets/tag-peer-admin.env'),None)
    if secret is None:raise ValueError('Expected fixed legacy administrator mount for removal')
    volumes.extend([{'type':'bind','source':str(Path(secret).parent/'caddy_lan_basic_auth'),'target':'/run/secrets/caddy_lan_basic_auth','read_only':True},
                    {'type':'bind','source':root+'/sockets','target':'/run/tag-native','read_only':True}])
    if len({v['target'] for v in volumes})!=len(volumes):raise ValueError('Credential or socket mount repeated')
    caddy['volumes']=volumes
    environment=caddy.get('environment',{})
    if not isinstance(environment,dict):raise ValueError('Normalized environment required')
    caddy['environment']={name:value for name,value in environment.items() if name!='TAG_PEER_ADMIN_TOKEN'}
    if caddy.get('env_file'):raise ValueError('Unreviewed Caddy environment files')
    ports=caddy.get('ports',[])
    if any(not isinstance(p,dict) for p in ports):raise ValueError('Normalized published ports required')
    caddy['ports']=[p for p in ports if int(p['target'])!=5006]
    if {int(p['target']) for p in caddy['ports']}!={5009}:raise ValueError('Unexpected Caddy published listener')
    gateway=services['readonly-gateway']
    if {int(p['target']) for p in gateway['ports']}!={5008}:raise ValueError('Readonly public port changed')
    hosts=gateway.get('extra_hosts',{})
    if isinstance(hosts,list):hosts=dict(value.split(':',1) for value in hosts)
    if not isinstance(hosts,dict):raise ValueError('Unknown host gateway mapping')
    if 'host.containers.internal' in hosts and hosts['host.containers.internal']!='host-gateway':raise ValueError('Untrusted gateway mapping')
    gateway['extra_hosts']={**hosts,'host.containers.internal':'host-gateway'}
    if gateway.get('depends_on')!=merged['services']['readonly-gateway'].get('depends_on'):raise ValueError('Readonly TLS dependency changed')
    for name in {'authelia','ddns-go'}:
        if services[name]!=merged['services'][name]:raise ValueError('Unowned service changed')
    return result

def manifest(pc,nuc,rollback_pc,rollback_nuc,product_proof):
    packages={}
    for name,path in [('pc',pc['package']),('nuc',nuc['package'])]:
        package=store_path(path)
        sha=digest(package/'libexec/tag-server-workspace')
        if sha!=product_proof['binary_sha256']:raise ValueError('Final frozen application binary differs')
        packages[name]={'path':str(package),'binary_sha256':sha}
    pc_home=store_path(pc['home']);pc_system=store_path(pc['toplevel']);nuc_root=store_path(nuc['candidate'])
    unit_root=nuc_root/'lib/systemd/user'
    names={f'tag-nuc-{role}-{kind}.service' for role in ['private','readonly'] for kind in ['core','tools','files']}|{'tag-native-nuc.target'}
    if {p.name for p in unit_root.iterdir()}!=names:raise ValueError('NUC application unit inventory changed')
    return {'schema_version':1,'stage':'E3.d','target_roots':ROOTS,'application_packages':packages,
            'pc':{'system':str(pc_system),'home':str(pc_home),'rollback_system':str(store_path(rollback_pc))},
            'nuc':{'candidate':str(nuc_root),'rollback_candidate':str(store_path(rollback_nuc)),
                   'units':{p.name:digest(p) for p in unit_root.iterdir()},
                   'templates':{role:digest(nuc_root/(role+'-entry.toml')) for role in ['private','readonly']}},
            'state_policy':'reuse-current-database-metadata-ca-and-identity-no-restore',
            'writers':'one-per-role-stop-before-configuration-handover','activated':False,'e4_required':True}

def handover_plan(release,target,direction,*,units_stopped,ports_released):
    if target not in ROOTS or direction not in {'update','rollback'}:raise ValueError('Explicit target and direction required')
    if release.get('target_roots')!=ROOTS or release.get('state_policy')!='reuse-current-database-metadata-ca-and-identity-no-restore':raise ValueError('Frozen state policy required')
    if units_stopped is not True or ports_released is not True:raise ValueError('All old writers and replaced listeners must stop before handover')
    required=['confirm-editors-saved','freeze-current-inputs-and-private-offline-backup','stop-writers-and-conflicting-listeners','verify-exclusive-state-and-released-ports','install-reviewed-config-and-units','start-files-and-tools-before-core','verify-new-state-and-identity']
    return {'target':target,'direction':direction,'steps':required,'database':ROOTS[target]+('/data/core.db' if target=='pc' else '/{private,readonly}/state/core.db'),
            'restore_old_database':False,'restore_old_metadata_or_ca':False,'pc_system_switch_by_user':target=='pc','production_apply':False}

RUNTIME='/home/liou/.local/share/dufs-plus/runtime/home'

def rebind_startup_control(previous, reviewed, *, model_path=RUNTIME+'/application-compose.json'):
    """Prepare hash-bound native startup input; caller writes nothing in dry-run."""
    if previous.get('root')!=ROOTS['nuc'] or previous.get('hostname')!='nuc' or previous.get('uid')!=1000:
        raise ValueError('Fixed NUC startup control required')
    if model_path!=RUNTIME+'/application-compose.json':raise ValueError('Fixed reviewed Compose model required')
    images=previous.get('source_images',{})
    expected={'dufs-plus_'+name+'_1' for name in KEEP|REMOVED}
    if set(images)!=expected or any(not re.fullmatch('(sha256:)?[0-9a-f]{64}',value) for value in images.values()):
        raise ValueError('Full pinned original NUC image inventory required')
    original=previous.get('compose',[])
    if original[:2]!=['podman','compose'] or '--env-file' not in original:raise ValueError('Existing native Compose control required')
    env=original[original.index('--env-file')+1]
    if env!=RUNTIME+'/compose.env' or env not in previous.get('files',{}):raise ValueError('Pinned existing Compose environment required')
    if model_path not in reviewed or RUNTIME+'/Caddyfile' not in reviewed:raise ValueError('Reviewed application model and Caddyfile required')
    for path,sha in reviewed.items():
        fixed_runtime=Path(path).parent==Path(RUNTIME)
        fixed_entry=path in {ROOTS['nuc']+'/'+role+'/config/'+name for role in ['private','readonly'] for name in ['application-entry.toml','basic.entries']}
        if not (fixed_runtime or fixed_entry) or not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError('Unexpected reviewed startup input')
    result=copy.deepcopy(previous)
    result['files'].update(reviewed)
    result['compose']=['podman','compose','--env-file',env,'-f',model_path]
    return result

def inventory_fingerprint(records):
    """Discard inspect command/environment; return only verified ownership and image IDs."""
    expected={'dufs-plus_'+name+'_1' for name in KEEP|REMOVED}
    by_name={record['Name'].lstrip('/'):record for record in records}
    if len(by_name)!=len(records) or set(by_name)!=expected:raise ValueError('Full unique NUC inventory required')
    images={}
    for name,record in by_name.items():
        if record['Config']['Labels'].get('io.podman.compose.project')!='dufs-plus':raise ValueError('Unexpected container owner')
        service=name.removeprefix('dufs-plus_').removesuffix('_1')
        if service in REMOVED:
            if record['State']['Running'] is not False or record['HostConfig']['RestartPolicy']['Name']!='no':raise ValueError('Original business container may still write or auto-restart')
        elif record['State']['Running'] is not True:raise ValueError('Retained ingress service unavailable')
        if not re.fullmatch('(sha256:)?[0-9a-f]{64}',record['Image']):raise ValueError('Pinned full image ID required')
        images[name]=record['Image']
    return images,{name:images['dufs-plus_'+name+'_1'] for name in KEEP}
