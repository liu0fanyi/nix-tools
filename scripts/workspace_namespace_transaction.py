"""Infrastructure-owned offline namespace cutover. No production action on import.

The caller must supply the frozen product migration driver, reviewed per-host
plan and the existing native Manager's scoped service/lock ports. A committed
DB is recovered forward; configuration rollback never restores a database.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
import hashlib
import json
import os
import re
from pathlib import Path
import socket
import stat

from application_entry_transaction import ConfigurationTransaction, atomic, backup_state, create_lock, digest, exclusive, offline_states, private


@dataclass(frozen=True)
class Scope:
    name: str
    root: Path
    state: Path
    namespace: Path
    units: tuple
    targets: frozenset
    journals: tuple = ()


def fixed_scope(name):
    if name not in ('pc','nuc') or socket.gethostname() != {'pc':'liu-bigpc','nuc':'nuc'}[name] or os.getuid()!=1000:
        raise ValueError('Fixed host and liou user required')
    home=Path('/home/liou')
    root=home/'.local/share/tag-all'/('pc-native' if name=='pc' else 'nuc-native/private')
    core='tag-all-core.service' if name=='pc' else 'tag-nuc-private-core.service'
    files='tag-native-files.service' if name=='pc' else 'tag-nuc-private-files.service'
    units=home/'.config/systemd/user'
    registry=home/('.local/state/tag-browser-workspaces' if name=='pc' else '.local/state/tag-workspace-directories/nuc-private')
    targets={root/'config/application-entry.toml',root/'config/node.toml',registry/'directories.json',
             units/(core+'.d')/'40-tag-browser-directories.conf',
             units/(files+'.d')/'40-tag-browser-directories.conf',
             units/(core+'.d')/'80-tag-version.conf',
             units/(files+'.d')/'50-tag-workspace-namespace.conf'}
    targets.add(registry/'namespace-migration.json' if name=='pc' else home/'.local/share/dufs-plus/runtime/home/native-nuc-control.json')
    journals=tuple(root/'executors'/path for path in ['pdf','archive','epub','audioVideo/workspace','audioVideo/publication','pdf-comic-publication'])
    targets.update(path/'owner.json' for path in journals)
    return Scope(name,home/'.local/state/tag-workspace-namespace'/name,root/('data' if name=='pc' else 'state'),
                 home/'tag-workspaces'/name,(core,files),frozenset(targets),journals)


def encode(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))


class Cutover:
    def __init__(self,scope,manager,apply_database,database_status):
        self.scope,self.manager,self.apply_database,self.database_status=scope,manager,apply_database,database_status
        if set(manager.scope.units)!=set(scope.units) or tuple(manager.scope.states)!=(scope.state,):
            raise ValueError('Only this host private core/files and its one state may be stopped')

    def prepare(self,plan):
        if plan.get('schema')!=1 or plan.get('scope')!=self.scope.name or plan.get('namespace')!=str(self.scope.namespace):
            raise ValueError('Namespace plan scope changed')
        if set(map(Path,plan['files']))!=self.scope.targets or plan.get('state_policy')!='never-restore-database':
            raise ValueError('Namespace file allowlist changed')
        if set(plan.get('roots',[])) != ({'dufs','project','home'} if self.scope.name=='pc' else {'dufs','art','project'}):
            raise ValueError('Explicit registered root names required')
        self.startup_inputs(plan)
        self.scope.root.mkdir(mode=0o700,parents=True,exist_ok=True);private(self.scope.root,True)
        identity=hashlib.sha256(encode(plan).encode()).hexdigest()
        release=self.scope.root/identity
        if release.exists():
            private(release,True)
            if private(release/'manifest.json').read_text()!=encode(plan):raise ValueError('Prepared namespace manifest changed')
        for name,row in plan['files'].items():
            target=Path(name)
            actual=digest(private(target)) if target.exists() or target.is_symlink() else None
            if actual!=row['before_sha256']:raise ValueError('Namespace input changed after planning')
        release.mkdir(mode=0o700,exist_ok=True)
        if not (release/'manifest.json').exists():atomic(release/'manifest.json',encode(plan))
        for index,(name,row) in enumerate(sorted(plan['files'].items())):
            file=release/('file-'+str(index))
            if file.exists() or file.is_symlink():
                if private(file).read_text()!=row['after']:raise ValueError('Prepared namespace bytes changed')
            else:atomic(file,row['after'])
        outputs=set()
        for source in plan.get('input_sha256',{}):
            match=re.fullmatch(r'(/nix/store/[a-z0-9]{32}-[^/]+)(?:/.*)?',source)
            if not match:raise ValueError('Immutable namespace input required')
            outputs.add(match[1])
        for index,output in enumerate(sorted(outputs)):
            link=release/('input-'+str(index))
            if link.exists() or link.is_symlink():
                if not link.is_symlink() or link.lstat().st_uid!=os.getuid() or link.resolve()!=Path(output):
                    raise ValueError('Namespace input GC root changed')
            else:self.manager.run(['nix-store','--add-root',str(link),'--indirect','--realise',output])
            if not link.is_symlink() or link.lstat().st_uid!=os.getuid() or link.resolve()!=Path(output):
                raise ValueError('Namespace input GC root was not created')
        return release

    def load(self,release):
        release=Path(release)
        if release.parent!=self.scope.root or len(release.name)!=64 or any(c not in '0123456789abcdef' for c in release.name):
            raise ValueError('Fixed prepared namespace directory required')
        private(release,True);text=private(release/'manifest.json').read_text()
        if hashlib.sha256(text.encode()).hexdigest()!=release.name:raise ValueError('Namespace manifest changed')
        plan=json.loads(text)
        if (plan.get('schema')!=1 or plan['scope']!=self.scope.name or plan['namespace']!=str(self.scope.namespace)
            or set(map(Path,plan['files']))!=self.scope.targets or plan.get('state_policy')!='never-restore-database'
            or len(plan.get('roots',[]))!=3 or set(plan['roots'])!=({'dufs','project','home'} if self.scope.name=='pc' else {'dufs','art','project'})):
            raise ValueError('Namespace recovery scope changed')
        self.startup_inputs(plan)
        return release,plan

    def startup_inputs(self,plan):
        if self.scope.name!='nuc':return
        controls=[path for path in self.scope.targets if path.name=='native-nuc-control.json']
        if len(controls)!=1:raise ValueError('Fixed NUC startup control required')
        control=json.loads(plan['files'][str(controls[0])]['after'])
        for name,expected in control['files'].items():
            path=Path(name)
            current=digest(private(path))
            if name in plan['files']:
                row=plan['files'][name];after=hashlib.sha256(row['after'].encode()).hexdigest()
                if expected!=after or current not in (row['before_sha256'],after):
                    raise ValueError('NUC startup input changed')
            elif current!=expected:raise ValueError('NUC startup input changed')

    def replacements(self,release,plan):
        result={}
        for index,(name,row) in enumerate(sorted(plan['files'].items())):
            source=private(release/('file-'+str(index)))
            if source.read_text()!=row['after']:raise ValueError('Prepared namespace bytes changed')
            result[Path(name)]={'kind':'file','source':str(source),'sha256':digest(source)}
        return result

    def owned(self,transaction,plan,replacements):
        journal=transaction.load()
        for name,row in journal['records'].items():
            before,after=row['before'],row['after']
            expected=plan['files'][name]['before_sha256']
            if before['kind']=='absent':
                if expected is not None:raise ValueError('Missing namespace original binding')
            elif before['kind']=='file':
                if before['sha256']!=expected or before['mode']!=0o600:raise ValueError('Namespace original changed')
                if digest(private(transaction.directory/'before'/before['saved']))!=expected:raise ValueError('Namespace original backup changed')
            else:raise ValueError('Namespace config cannot replace a symlink')
            if after!=replacements[Path(name)]:raise ValueError('Namespace replacement changed')
            target=Path(name)
            actual=digest(private(target)) if target.exists() or target.is_symlink() else None
            if actual not in (expected,after['sha256']):raise ValueError('External namespace edit; recovery stopped')

    def directories(self,roots):
        parent=self.scope.namespace.parent
        parent.mkdir(mode=0o700,parents=True,exist_ok=True);private(parent,True)
        self.scope.namespace.mkdir(mode=0o700,exist_ok=True);private(self.scope.namespace,True)
        for existing in self.scope.namespace.iterdir():
            if existing.name not in roots or existing.is_symlink() or not existing.is_dir() or any(existing.iterdir()):
                raise ValueError('Namespace contains user data or an unknown entry')
        for name in roots:
            directory=self.scope.namespace/name
            directory.mkdir(mode=0o700,exist_ok=True);private(directory,True)

    @contextmanager
    def journal_guards(self):
        with ExitStack() as stack:
            for directory in self.scope.journals:
                private(directory,True)
                if {entry.name for entry in directory.iterdir()} != {'lock','owner.json'}:
                    raise ValueError('Pending processing must be recovered in the original namespace first')
                stack.enter_context(exclusive(directory/'lock'))
            move=self.scope.state/'metadata/move-journal'
            if move.exists():
                private(move,True)
                if any(move.iterdir()):raise ValueError('Pending move intent must be recovered before namespace cutover')
            yield

    def cancel_before_commit(self,release,*,editors_saved=False):
        if not editors_saved:raise ValueError('Fresh saved-editor confirmation required')
        release,plan=self.load(release)
        create_lock(self.scope.root/'namespace.lock')
        with exclusive(self.scope.root/'namespace.lock'):
            if self.database_status(plan)!='legacy':raise ValueError('Database already migrated; forward recovery required')
            transaction=ConfigurationTransaction(release/'transaction',self.scope.targets)
            self.owned(transaction,plan,self.replacements(release,plan))
            with self.manager.suspend_upholding(plan,restore_on_error=True):
                self.manager.run(['systemctl','--user','stop',*self.scope.units])
                with offline_states((self.scope.state,),self.manager.stopped):
                    if self.database_status(plan)!='legacy':raise ValueError('Namespace database changed')
                    transaction.install(rollback=True);transaction.verify_before()
                self.manager.run(['systemctl','--user','daemon-reload'])
                self.manager.run(['systemctl','--user','start',*self.scope.units])
                self.manager.ready();transaction.phase('cancelled-before-database-commit')
            return {'phase':'cancelled','database_restored':False}

    def apply(self,release,*,editors_saved=False):
        if not editors_saved:raise ValueError('Fresh saved-editor confirmation required')
        release,plan=self.load(release)
        create_lock(self.scope.root/'namespace.lock')
        with exclusive(self.scope.root/'namespace.lock'):
            transaction=ConfigurationTransaction(release/'transaction',self.scope.targets)
            replacements=self.replacements(release,plan)
            if transaction.journal.exists():
                self.owned(transaction,plan,replacements)
            else:
                for target in self.scope.targets:
                    actual=digest(private(target)) if target.exists() or target.is_symlink() else None
                    if actual!=plan['files'][str(target)]['before_sha256']:raise ValueError('Namespace input changed after planning')
                for target in self.scope.targets:
                    if not target.parent.exists():target.parent.mkdir(mode=0o700,parents=True)
                    if target.parent.is_symlink() or target.parent.stat().st_uid!=os.getuid() or target.parent.stat().st_mode&0o022:
                        raise ValueError('Unsafe namespace config parent')
                transaction.create(replacements);transaction.verify_before()
            self.manager.tasks_idle()
            # Unlike ordinary binary updates, do not revive old configuration
            # after a durable path commit. The owned uphold inhibition remains
            # on failure and is verified/reused on the next forward recovery.
            with self.manager.suspend_upholding(plan,restore_on_error=False):
                self.manager.run(['systemctl','--user','stop',*self.scope.units])
                with offline_states((self.scope.state,),self.manager.stopped), self.journal_guards():
                    self.manager.tasks_idle();self.owned(transaction,plan,replacements)
                    status=self.database_status(plan)
                    if status not in ('legacy','applied-expected'):raise ValueError('Database belongs to another namespace transaction')
                    if status=='legacy' and not (release/'backup').exists():
                        result=backup_state(self.scope.state,release/'backup')
                        atomic(release/'backup-results.json',encode(result))
                    self.directories(plan['roots'])
                    try:
                        transaction.install();transaction.verify_after()
                        self.startup_inputs(plan)
                        self.apply_database(plan)
                        if self.database_status(plan)!='applied-expected':raise ValueError('Namespace database receipt missing')
                        transaction.phase('database-migrated')
                    except BaseException:
                        # Inspect the receipt, including a crash after SQLite
                        # committed but before the outer journal advanced.
                        if self.database_status(plan)=='legacy':
                            transaction.install(rollback=True);transaction.verify_before()
                            transaction.phase('failed-before-database-commit')
                        else:
                            transaction.phase('forward-recovery-required')
                        raise
                self.manager.run(['systemctl','--user','daemon-reload'])
                self.manager.run(['systemctl','--user','start',*self.scope.units])
                self.manager.ready()
                transaction.verify_after();transaction.phase('activated')
                return {'phase':'activated','namespace':str(self.scope.namespace),'database_restored':False}
