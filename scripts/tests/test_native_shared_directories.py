import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path('/home/liou/nix-tools')
s=importlib.util.spec_from_file_location('nuc_directories',ROOT/'scripts/native_shared_directories.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n)
s=importlib.util.spec_from_file_location('app_directories',Path('/data/project/tag-browser/scripts/tag-browser-workspaces.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class NucDirectoryScope(unittest.TestCase):
    def test_implicit_location_matches_server_default_without_rewriting_config(self):
        node={'node':{'id':'nuc'}};self.assertEqual(n.local_location(node,n.WORKSPACE),{'id':'default'});self.assertNotIn('locations',node)
        node['locations']=[{'id':'explicit','path':str(n.WORKSPACE)}];self.assertEqual(n.local_location(node,n.WORKSPACE)['id'],'explicit')
        node['locations']=[{'id':'other','path':'/wrong'}]
        with self.assertRaises(StopIteration):n.local_location(node,n.WORKSPACE)
    def rows(self):return [dict(enabled=True,prefix='media/'+name,path='/media/liou/'+name) for name in ['Art','project']]
    def test_old_prefixes_and_physical_disk_sources_cannot_be_reassigned(self):
        rows=self.rows();self.assertEqual(n.checked_rows(rows),rows)
        for bad in [rows[:1],[rows[0],dict(rows[1],path='/media/other')],[rows[0],dict(rows[1],prefix='media/new')],rows+[dict(enabled=True,prefix='other',path='/home/liou/private')]]:
            with self.assertRaises(ValueError):n.checked_rows(bad)
    def test_immutable_helper_required_before_import(self):
        with tempfile.TemporaryDirectory() as raw:
            p=Path(raw)/'helper';p.write_text('raise AssertionError("must not import")')
            with self.assertRaises(ValueError):n.load_helper(p,hashlib.sha256(p.read_bytes()).hexdigest())
    def test_restart_reuses_app_guards_and_orders_files_before_core(self):
        m.UNITS=n.UNITS;calls=[];a=n.Adapter(m,run=lambda args:calls.append(args) or '')
        request=[m.SYSTEMCTL,'--user','restart',*n.UNITS,'tag-native-workspace.service']
        a.idle_only=True
        with self.assertRaises(n.IdleVerified):a.run(request)
        self.assertEqual(calls,[])
        a.idle_only=False;a.run(request)
        self.assertEqual(calls,[[m.SYSTEMCTL,'--user','restart',n.UNITS[1]],[m.SYSTEMCTL,'--user','restart',n.UNITS[0]]])
    def fixture(self,raw):
        root=Path(raw);state=root/'state';state.mkdir(mode=0o700);entry=root/'entry.toml';m.atomic(entry,'old configuration')
        calls=[];a=n.Adapter(m,run=lambda args:calls.append(args) or '');a.d.state=state;a.d.units=root/'units';a.control=root/'native-control.json';i={'entry':entry};a.d.installation=lambda:i
        before=a.snapshot(i)
        for p in a.paths(i):m.atomic(p,'new configuration')
        after=a.snapshot(i);receipt=state/'release-test.json';m.atomic(receipt,json.dumps(dict(schema=1,before=before,after=after,directories=[])))
        return a,i,entry,receipt,calls
    def test_rollback_rejects_external_edits_before_mutation(self):
        with tempfile.TemporaryDirectory() as raw:
            a,i,entry,receipt,calls=self.fixture(raw);m.atomic(entry,'external edit')
            with self.assertRaises(ValueError):a.restore(receipt)
            self.assertEqual(entry.read_text(),'external edit');self.assertEqual(calls,[])
    def test_configuration_rollback_retains_data_and_unrelated_units(self):
        with tempfile.TemporaryDirectory() as raw:
            a,i,entry,receipt,calls=self.fixture(raw);database=Path(raw)/'database';database.write_bytes(b'latest writes');other=a.d.units/'unrelated.service';m.atomic(other,'leave alone')
            self.assertEqual(a.restore(receipt)['phase'],'rolled-back');self.assertEqual(entry.read_text(),'old configuration')
            self.assertEqual(database.read_bytes(),b'latest writes');self.assertEqual(other.read_text(),'leave alone')
            self.assertFalse((a.d.state/'directories.json').exists());self.assertFalse((a.d.units/(n.UNITS[1]+'.d')/m.MANAGED).exists())
            self.assertEqual(calls[-2:],[ [m.SYSTEMCTL,'--user','restart',n.UNITS[1]],[m.SYSTEMCTL,'--user','restart',n.UNITS[0]]])
    def test_startup_binding_updates_only_reviewed_entry(self):
        with tempfile.TemporaryDirectory() as raw:
            a,i,entry,receipt,calls=self.fixture(raw)
            value={'root':str(n.ROOT),'hostname':'nuc','uid':1000,'files':{str(entry):'old','/unrelated':'keep'},'other':'keep'}
            m.atomic(a.control,json.dumps(value));a.bind_entry_hash(i);actual=json.loads(a.control.read_text())
            self.assertEqual(actual['files'][str(entry)],hashlib.sha256(entry.read_bytes()).hexdigest());self.assertEqual(actual['files']['/unrelated'],'keep');self.assertEqual(actual['other'],'keep')
            value['root']='/wrong';m.atomic(a.control,json.dumps(value))
            with self.assertRaises(ValueError):a.bind_entry_hash(i)
    def test_startup_binding_rejects_concurrent_or_unbound_entry(self):
        with tempfile.TemporaryDirectory() as raw:
            a,i,entry,receipt,calls=self.fixture(raw)
            value={'root':str(n.ROOT),'hostname':'nuc','uid':1000,'files':{str(entry):'unbound'}}
            m.atomic(a.control,json.dumps(value));before=a.control.read_text()
            with self.assertRaises(ValueError):a.bind_entry_hash(i,before+'changed')
            with self.assertRaises(ValueError):a.bind_entry_hash(i,before,'previous entry')
            self.assertEqual(a.control.read_text(),before);self.assertEqual(calls,[])
    def test_pre_restart_refusal_restores_configuration_without_interrupting_tasks(self):
        with tempfile.TemporaryDirectory() as raw:
            a,i,entry,receipt,calls=self.fixture(raw);a.restore(receipt,restart=False)
            self.assertEqual(entry.read_text(),'old configuration');self.assertEqual(calls,[[m.SYSTEMCTL,'--user','daemon-reload']])
    def test_backup_cannot_expand_configuration_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            a,i,entry,receipt,calls=self.fixture(raw);value=json.loads(receipt.read_text());value['before']['/unrelated']='forbidden';m.atomic(receipt,json.dumps(value))
            with self.assertRaises(ValueError):a.restore(receipt)
            self.assertEqual(entry.read_text(),'new configuration');self.assertEqual(calls,[])

if __name__=='__main__':unittest.main()
