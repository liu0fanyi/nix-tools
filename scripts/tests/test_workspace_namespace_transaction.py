from contextlib import contextmanager, closing
import json
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]))
from application_entry_transaction import digest,atomic,create_lock
from workspace_namespace_transaction import Scope,Cutover
from native_application_release import Manager,namespace_package


class FakeManager:
    def __init__(self,scope):
        self.scope=SimpleNamespace(units=scope.units,states=(scope.state,))
        self.commands=[];self.active=True;self.inhibited=False
    def tasks_idle(self):pass
    def run(self,args):
        self.commands.append(args)
        if 'stop' in args:self.active=False
        if 'start' in args:self.active=True
    def stopped(self):
        if self.active:raise ValueError('writers still active')
    def ready(self):
        if not self.active:raise ValueError('service not active')
    @contextmanager
    def suspend_upholding(self,plan,*,restore_on_error=True):
        self.inhibited=True
        try:yield
        except BaseException:
            if restore_on_error:self.inhibited=False
            raise
        else:self.inhibited=False


class CutoverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.state=root/'state';self.state.mkdir(mode=0o700)
        create_lock(self.state/'instance.lock')
        self.db=self.state/'core.db'
        with closing(sqlite3.connect(self.db)) as db, db:
            db.executescript('CREATE TABLE namespace(version TEXT); CREATE TABLE notes(body TEXT); INSERT INTO notes VALUES("original");')
        self.db.chmod(0o600)
        self.a=root/'a.conf';atomic(self.a,'old-a')
        self.b=root/'b.conf'
        self.scope=Scope('pc',root/'transactions',self.state,root/'exports/pc',('core.service','files.service'),frozenset([self.a,self.b]))
        self.manager=FakeManager(self.scope)
        self.fail=None
        def status(plan):
            with closing(sqlite3.connect(self.db)) as db, db:row=db.execute('SELECT version FROM namespace').fetchone()
            return 'applied-expected' if row==('canonical-v2',) else 'legacy' if row is None else 'other'
        def apply(plan):
            self.manager.stopped()
            if status(plan)=='applied-expected':return
            if self.fail=='before':raise RuntimeError('synthetic before commit')
            with closing(sqlite3.connect(self.db)) as db, db:db.execute('INSERT INTO namespace VALUES("canonical-v2")')
            if self.fail=='after':raise SystemExit('synthetic after commit')
        self.cutover=Cutover(self.scope,self.manager,apply,status)
        self.plan={'schema':1,'scope':'pc','namespace':str(self.scope.namespace),'roots':['dufs','project','home'],
                   'state_policy':'never-restore-database','files':{
                       str(self.a):{'before_sha256':digest(self.a),'after':'new-a'},
                       str(self.b):{'before_sha256':None,'after':'new-b'}}}
        self.release=self.cutover.prepare(self.plan)
    def browser_record(self, previous=None):
        from dataclasses import replace
        old=self.b;self.b=old.with_name('namespace-migration.json')
        if previous is not None:atomic(self.b,previous)
        self.scope=replace(self.scope,targets=frozenset([self.a,self.b]))
        self.cutover.scope=self.scope
        self.plan['files'][str(self.b)]=self.plan['files'].pop(str(old))
        self.plan['files'][str(self.b)]['before_sha256']=digest(self.b) if previous is not None else None
        self.release=self.cutover.prepare(self.plan)

    def test_browser_record_is_not_visible_until_database_receipt_commits(self):
        self.browser_record()
        original=self.cutover.apply_database
        def apply(plan):
            self.assertFalse(self.b.exists(),'App must not migrate before the DB commits')
            original(plan)
        self.cutover.apply_database=apply
        self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.b.read_text(),'new-b')
        self.assertEqual(self.cutover.database_status(self.plan),'applied-expected')

    def test_browser_record_preserves_old_receipt_on_failure_then_recovers_forward(self):
        self.browser_record('previous-browser-record')
        self.fail='before'
        with self.assertRaises(RuntimeError):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.b.read_text(),'previous-browser-record')
        self.fail='after'
        with self.assertRaises(SystemExit):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.cutover.database_status(self.plan),'applied-expected')
        self.assertEqual(self.b.read_text(),'previous-browser-record')
        with closing(sqlite3.connect(self.db)) as db, db:db.execute('INSERT INTO notes VALUES("after receipt")')
        self.fail=None;self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.b.read_text(),'new-b')
        with closing(sqlite3.connect(self.db)) as db, db:self.assertEqual(db.execute('SELECT body FROM notes').fetchall(),[('original',),('after receipt',)])

    def test_preparation_retry_completes_missing_stage_files_and_never_accepts_changed_bytes(self):
        staged=self.release/'file-0';staged.unlink()
        self.assertEqual(self.cutover.prepare(self.plan),self.release)
        self.assertEqual(staged.read_text(),'new-a')
        atomic(staged,'external edit')
        with self.assertRaisesRegex(ValueError,'Prepared namespace bytes changed'):self.cutover.prepare(self.plan)
        self.assertEqual(staged.read_text(),'external edit')

    def test_frozen_input_gc_roots_are_created_once_and_verified(self):
        output='/nix/store/'+'a'*32+'-synthetic-driver'
        plan=json.loads(json.dumps(self.plan));plan['input_sha256']={output+'/libexec/driver.py':'a'*64,output+'/libexec/store.py':'b'*64}
        original=self.manager.run
        def run(args):
            if args[:2]==['nix-store','--add-root']:Path(args[2]).symlink_to(args[-1])
            return original(args)
        self.manager.run=run
        release=self.cutover.prepare(plan)
        self.assertEqual((release/'input-0').readlink(),Path(output))
        self.assertEqual(self.cutover.prepare(plan),release)
        self.assertEqual(sum(command[:2]==['nix-store','--add-root'] for command in self.manager.commands),1)
        (release/'input-0').unlink();(release/'input-0').symlink_to('/tmp/unreviewed')
        with self.assertRaisesRegex(ValueError,'GC root changed'):self.cutover.prepare(plan)

    def test_apply_requires_saved_editor_confirmation_before_stopping_services(self):
        with self.assertRaises(ValueError):self.cutover.apply(self.release)
        self.assertEqual(self.manager.commands,[]);self.assertEqual(self.a.read_text(),'old-a')
    def test_success_uses_current_db_and_preserves_identity_and_original_backup(self):
        inode=self.db.stat().st_ino
        self.assertEqual(self.cutover.apply(self.release,editors_saved=True)['phase'],'activated')
        self.assertEqual(self.db.stat().st_ino,inode)
        self.assertEqual(self.a.read_text(),'new-a');self.assertEqual(self.b.read_text(),'new-b')
        self.assertFalse(self.manager.inhibited);self.assertTrue(self.manager.active)
        self.assertTrue((self.release/'backup/core.db').is_file())
    def test_before_commit_failure_restores_config_and_leaves_no_new_database_state(self):
        self.fail='before'
        with self.assertRaises(RuntimeError):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.a.read_text(),'old-a');self.assertFalse(self.b.exists())
        self.assertTrue(self.manager.inhibited);self.assertFalse(self.manager.active)
        with closing(sqlite3.connect(self.db)) as db, db:self.assertEqual(db.execute('SELECT * FROM namespace').fetchall(),[])
    def test_commit_then_interruption_recovers_forward_and_keeps_new_writes(self):
        self.fail='after'
        with self.assertRaises(SystemExit):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.a.read_text(),'new-a');self.assertEqual(self.b.read_text(),'new-b')
        self.assertTrue(self.manager.inhibited)
        with closing(sqlite3.connect(self.db)) as db, db:db.execute('INSERT INTO notes VALUES("new after cutover")')
        self.fail=None
        self.cutover.apply(self.release,editors_saved=True)
        with closing(sqlite3.connect(self.db)) as db, db:self.assertEqual(db.execute('SELECT body FROM notes').fetchall(),[('original',),('new after cutover',)])
        self.assertFalse(self.manager.inhibited)
    def test_external_configuration_edit_refuses_forward_recovery(self):
        self.fail='after'
        with self.assertRaises(SystemExit):self.cutover.apply(self.release,editors_saved=True)
        atomic(self.a,'external user edit')
        with self.assertRaises(ValueError):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.a.read_text(),'external user edit')
    def test_cancel_before_commit_restores_old_services_and_never_restores_database(self):
        self.fail='before'
        with self.assertRaises(RuntimeError):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.cutover.cancel_before_commit(self.release,editors_saved=True)['phase'],'cancelled')
        self.assertTrue(self.manager.active);self.assertFalse(self.manager.inhibited)
        self.assertEqual(self.a.read_text(),'old-a');self.assertFalse(self.b.exists())
        self.fail=None;self.cutover.apply(self.release,editors_saved=True)
        with self.assertRaisesRegex(ValueError,'forward recovery'):self.cutover.cancel_before_commit(self.release,editors_saved=True)

    def test_pending_executor_or_move_journal_blocks_database_commit(self):
        from dataclasses import replace
        directory=self.scope.root.parent/'executor';directory.mkdir(mode=0o700)
        create_lock(directory/'lock');atomic(directory/'owner.json','{}');atomic(directory/'pending.json','{}')
        self.cutover.scope=replace(self.scope,journals=(directory,))
        with self.assertRaisesRegex(ValueError,'Pending processing'):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual(self.a.read_text(),'old-a');self.assertEqual(self.cutover.database_status(self.plan),'legacy')

    def test_nuc_control_accepts_only_reviewed_before_after_and_refuses_other_input_drift(self):
        from dataclasses import replace
        import hashlib
        control=self.scope.root.parent/'native-nuc-control.json'
        env=self.scope.root.parent/'service.env';atomic(env,'synthetic input')
        after=hashlib.sha256(b'new-a').hexdigest()
        plan=json.loads(json.dumps(self.plan))
        plan['files'][str(control)]={'before_sha256':None,'after':json.dumps({'files':{str(self.a):after,str(env):digest(env)}})}
        self.cutover.scope=replace(self.scope,name='nuc',targets=self.scope.targets|{control})
        self.cutover.startup_inputs(plan)
        atomic(self.a,'new-a');self.cutover.startup_inputs(plan)
        atomic(env,'rotated outside the reviewed transaction')
        with self.assertRaisesRegex(ValueError,'startup input changed'):self.cutover.startup_inputs(plan)
        self.assertEqual(self.manager.commands,[])

    def test_unknown_target_and_nonempty_namespace_are_never_removed(self):
        bad=json.loads(json.dumps(self.plan));bad['files'][str(self.scope.root/'unrelated')]={'before_sha256':None,'after':'x'}
        with self.assertRaises(ValueError):self.cutover.prepare(bad)
        self.scope.namespace.mkdir(parents=True,mode=0o700)
        atomic(self.scope.namespace/'user-file','keep')
        with self.assertRaises(ValueError):self.cutover.apply(self.release,editors_saved=True)
        self.assertEqual((self.scope.namespace/'user-file').read_text(),'keep')


class NamespaceProgramTests(unittest.TestCase):
    def test_cutover_requires_supporting_program_even_before_namespace_table_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);database=root/'core.db'
            with closing(sqlite3.connect(database)) as db, db:db.execute('CREATE TABLE notes(body TEXT)')
            database.chmod(0o600);package=root/'package';package.mkdir()
            namespace_package(root,package)
            with self.assertRaisesRegex(ValueError,'before migration'):namespace_package(root,package,required=True)
            marker=package/'share/tag-all/workspace-namespace';marker.parent.mkdir(parents=True);marker.write_text('canonical-v2\n')
            namespace_package(root,package,required=True)
            with closing(sqlite3.connect(database)) as db, db:self.assertFalse(db.execute("SELECT 1 FROM sqlite_schema WHERE name='workspace_namespace_state'").fetchone())

    def test_legacy_program_is_refused_after_path_commit_and_new_program_keeps_current_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);database=root/'core.db'
            with closing(sqlite3.connect(database)) as db, db:db.execute('CREATE TABLE workspace_namespace_state(singleton INTEGER PRIMARY KEY,version TEXT)')
            database.chmod(0o600);package=root/'package';package.mkdir()
            namespace_package(root,package)
            with closing(sqlite3.connect(database)) as db, db:db.execute("INSERT INTO workspace_namespace_state VALUES(1,'canonical-v2')")
            with self.assertRaisesRegex(ValueError,'forward recovery'):namespace_package(root,package)
            marker=package/'share/tag-all/workspace-namespace';marker.parent.mkdir(parents=True);marker.write_text('canonical-v2\n')
            namespace_package(root,package)
            with closing(sqlite3.connect(database)) as db, db:self.assertEqual(db.execute('SELECT version FROM workspace_namespace_state').fetchone(),('canonical-v2',))


class UpholdTests(unittest.TestCase):
    def test_failed_namespace_change_keeps_owned_inhibition_and_resumes_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);root.chmod(0o700)
            fragment=root/'target.source';atomic(fragment,'[Unit]\nUpholds=core.service files.service readonly.service\n')
            override=root/'user.control'/'target'
            scope=SimpleNamespace(units=('core.service','files.service'),uphold_target='target')
            class ScopedManager(Manager):
                def uphold_path(self):return override
                def uphold_binding(self):
                    active=override if override.exists() else fragment
                    units=next(line.partition('=')[2].split() for line in active.read_text().splitlines() if line.startswith('Upholds='))
                    return {'target':'target','fragment':str(active),'sources':{} if override.exists() else {str(fragment):digest(fragment)},'units':sorted(units)}
            manager=ScopedManager(scope,run=lambda args:'')
            plan={'upholding':manager.uphold_binding()}
            with self.assertRaises(RuntimeError):
                with manager.suspend_upholding(plan,restore_on_error=False):raise RuntimeError('stop after DB commit')
            self.assertTrue(override.is_file());self.assertEqual(manager.uphold_binding()['units'],['readonly.service'])
            with manager.suspend_upholding(plan,restore_on_error=False):pass
            self.assertFalse(override.exists());self.assertEqual(manager.uphold_binding(),plan['upholding'])


if __name__=='__main__':unittest.main()
