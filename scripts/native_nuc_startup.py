"""Guarded startup adapter. Installation and mode changes belong to explicit cutover."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
from native_nuc_bundle import UNITS,digest
from native_nuc_guard import validate
from native_nuc_plan import PREFIX,REPLACE,KEEP
from native_pc_snapshot import private_file

ROOT=Path('/home/liou/.local/share/tag-all/nuc-native')
CONTROL=Path('/home/liou/.local/share/dufs-plus/runtime/home/native-nuc-control.json')
READ_ONLY={'ps','logs','config'}


def compose_action(mode,args):
    """No unrestricted arguments or implicit dependencies in managed native mode."""
    if not args:raise ValueError('Compose action required')
    if args[0] in READ_ONLY:
        if args not in [['ps'],['config'],['logs'],['logs','--follow']]:raise ValueError('Unsupported inspection options')
        return args
    if mode not in {'native','container'}:raise ValueError('Transition blocks startup and container changes')
    if mode=='container':
        # Boot resumes already-created new-state services; it never recreates old mounts.
        if args in [['up','-d'],['up','-d','--no-deps']]:return ['start',*REPLACE,*KEEP]
        if args==['down']:return ['stop',*REPLACE,*KEEP]
        if args[0] not in {'start','stop'} or any(a not in REPLACE+KEEP for a in args[1:]):
            raise ValueError('Fallback recreation requires explicit cutover controller')
        return args if len(args)>1 else [args[0],*REPLACE,*KEEP]
    action=args[0]
    options=[];services=[]
    for arg in args[1:]:
        if arg.startswith('-'):options.append(arg)
        else:services.append(arg)
    if len(services)!=len(set(services)) or any(s not in KEEP for s in services):raise ValueError('Native mode may control retained ingress containers only')
    services=services or list(KEEP)
    if action=='up':
        if '-d' not in options or len(options)!=len(set(options)) or any(o not in {'-d','--no-deps','--force-recreate'} for o in options):raise ValueError('Unsupported up options')
        return ['up','-d','--no-deps',*(['--force-recreate'] if '--force-recreate' in options else []),*services]
    if options:raise ValueError('Unsupported start/stop options')
    if action=='start':return ['start',*services]
    if action=='restart':
        # Compose restart may walk dependencies; scoped up is handled by controller.
        raise ValueError('Use guarded stop/start for retained ingress; restart refused')
    if action in {'stop','down'}:return ['stop',*services]
    raise ValueError('Unsupported container mutation in native mode')


def unit_dropins(guard_command):
    command=shlex.join([*guard_command,'native-check']).replace('%','%%')
    # Delegate each fresh check to the host user manager. '+' with writable BindPaths
    # cannot set up the namespace in a rootless user service. Keep service isolation.
    delegate='/run/current-system/sw/bin/env HOME=/home/liou XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus /run/current-system/sw/bin/systemd-run --user --wait --pipe --collect --quiet '
    result={name:'[Unit]\nRequires=dufs-plus-compose.service\nAfter=dufs-plus-compose.service\n[Service]\nExecStartPre='+delegate+command+'\n' for name in UNITS if name.endswith('.service')}
    result['tag-native-nuc.target']='[Unit]\nRequires=dufs-plus-compose.service\nAfter=dufs-plus-compose.service\n'
    return result


def read_inventory(run):
    names=[PREFIX+s+'_1' for s in REPLACE+KEEP]
    inspected=json.loads(run(['podman','inspect',*names]).stdout)
    records={item['Name'].lstrip('/'):item for item in inspected}
    if len(records)!=len(inspected):raise ValueError('Duplicate inventory')
    units={}
    for name in UNITS:
        result=run(['systemctl','--user','show',name,'--property=LoadState,ActiveState'],check=False)
        fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if fields.get('LoadState')=='not-found':units[name]='unknown'
        elif result.returncode==0 and fields.get('LoadState')=='loaded' and fields.get('ActiveState'):
            units[name]=fields['ActiveState']
        else:raise ValueError('Unable to read complete user unit status')
    return records,units


@contextmanager
def lock(path,*,shared=False):
    """Fail closed on a competing cutover; never create or truncate its lock here."""
    private_file(path)
    fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW)
    try:
        fcntl.flock(fd,(fcntl.LOCK_SH if shared else fcntl.LOCK_EX)|fcntl.LOCK_NB)
        yield
    finally:os.close(fd)


def read_mode(root):
    path=Path(root)/'startup-mode';private_file(path)
    value=path.read_text().strip()
    if value not in {'native','container','transition'}:raise ValueError('Invalid persistent startup mode')
    return value


def load_control(path=CONTROL):
    private_file(path);config=json.loads(path.read_text())
    if config['root']!=str(ROOT) or config['hostname']!='nuc' or config['uid']!=1000:
        raise ValueError('Only the fixed NUC installation is supported')
    if socket.gethostname()!='nuc' or os.getuid()!=1000:raise ValueError('Wrong runtime host/user')
    for name,sha in config['files'].items():
        private_file(name)
        if digest(name)!=sha:raise ValueError('Pinned startup input changed')
    argv=config['compose']
    if not argv or argv[:2]!=['podman','compose'] or '--env-file' not in argv or '-f' not in argv:
        raise ValueError('Fixed compose command required')
    # Every configuration path consumed by Compose must be hash bound.
    for index,arg in enumerate(argv):
        if arg in {'-f','--env-file'} and argv[index+1] not in config['files']:raise ValueError('Unbound compose input')
    return config


def dispatch(config,args,run):
    root=Path(config['root'])
    with lock(root/'startup.lock',shared=args==['native-check']):
        mode=read_mode(root)
        if args==['native-check']:
            if mode!='native':raise ValueError('Persistent mode blocks native startup')
            records,units=read_inventory(run)
            validate('native',root,records,units,source_images=config['source_images'])
            return 0
        if args[:1]!=['compose']:raise ValueError('Unsupported startup action')
        action=compose_action(mode,args[1:])
        if action[0] not in READ_ONLY:
            records,units=read_inventory(run)
            validate(mode,root,records,units,source_images=config['source_images'])
        return run([*config['compose'],*action],capture_output=False).returncode


def host_environment(environment):
    # Core HOME is the dedicated Git home; host inventory must use the real user store/bus.
    env=dict(environment)
    for key in ['CONTAINER_HOST','CONTAINER_CONNECTION','CONTAINERS_CONF','CONTAINERS_STORAGE_CONF','PODMAN_CONNECTIONS_CONF','DOCKER_HOST']:
        env.pop(key,None)
    env.update(PATH='/run/wrappers/bin:/home/liou/.nix-profile/bin:/nix/var/nix/profiles/default/bin:/etc/profiles/per-user/liou/bin:/run/current-system/sw/bin:/usr/bin:/bin',
        HOME='/home/liou',XDG_CONFIG_HOME='/home/liou/.config',
        XDG_DATA_HOME='/home/liou/.local/share',XDG_RUNTIME_DIR='/run/user/1000',
        DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
    return env


def main():
    def run(argv,check=True,capture_output=True):
        return subprocess.run(argv,check=check,capture_output=capture_output,text=True,timeout=180,env=host_environment(os.environ))
    try:return dispatch(load_control(),sys.argv[1:],run)
    except (ValueError,KeyError,OSError,subprocess.SubprocessError) as error:
        # Neither inspect/environment nor subprocess output can expose credentials.
        print('NUC startup refused: '+(str(error) if isinstance(error,ValueError) else type(error).__name__),file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
