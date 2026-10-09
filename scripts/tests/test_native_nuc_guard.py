import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]))
from native_nuc_guard import validate
from native_nuc_bundle import UNITS
from native_nuc_plan import PREFIX,REPLACE,KEEP

class Guard(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.records={}
        for service in REPLACE+KEEP:
            role='readonly' if service=='tag-server-readonly' else 'private'
            name=PREFIX+service+'_1'
            self.records[name]={'Name':name,'Image':'a'*64,'Config':{'Labels':{'io.podman.compose.project':'dufs-plus'},'Cmd':['--database','/data/core.db']},'State':{'Running':service in KEEP},
                'Mounts':[{'Type':'bind','Destination':'/data','Source':str(self.root/role/'state')}]}
        self.units=dict.fromkeys(UNITS,'inactive')
        (self.root/'ready').write_text('offline-double-snapshot-complete\n');(self.root/'ready').chmod(0o600)
        (self.root/'backup').mkdir(mode=0o700)
        p=self.root/'backup/source-images.json';p.write_text(json.dumps({name:'a'*64 for name in self.records}));p.chmod(0o600)
    def test_each_old_writer_blocks_snapshot_and_native(self):
        for mode in ['snapshot','native']:
            validate(mode,self.root,self.records,self.units)
            for service in REPLACE:
                records=copy.deepcopy(self.records);records[PREFIX+service+'_1']['State']['Running']=True
                with self.assertRaises(ValueError):validate(mode,self.root,records,self.units)
    def test_each_native_unit_blocks_snapshot_and_container(self):
        (self.root/'container-mode').write_text('explicit-container-fallback\n');(self.root/'container-mode').chmod(0o600)
        for mode in ['snapshot','container']:
            validate(mode,self.root,self.records,self.units)
            for name in UNITS:
                units=dict(self.units);units[name]='activating'
                with self.assertRaises(ValueError):validate(mode,self.root,self.records,units)
    def test_stale_database_fallback_refused(self):
        (self.root/'container-mode').write_text('explicit-container-fallback\n');(self.root/'container-mode').chmod(0o600)
        records=copy.deepcopy(self.records);records[PREFIX+'tag-server-readonly_1']['Mounts'][0]['Source']='/old/db'
        with self.assertRaises(ValueError):validate('container',self.root,records,self.units)
    def test_unknown_ownership_missing_inventory_and_mode_marker_refused(self):
        records=copy.deepcopy(self.records);records.pop(PREFIX+'ddns-go_1')
        with self.assertRaises(ValueError):validate('native',self.root,records,self.units)
        records=copy.deepcopy(self.records);records[PREFIX+'tag-server_1']['Config']['Labels']['io.podman.compose.project']='other'
        with self.assertRaises(ValueError):validate('native',self.root,records,self.units)
        (self.root/'container-mode').write_text('explicit-container-fallback\n');(self.root/'container-mode').chmod(0o600)
        with self.assertRaises(ValueError):validate('native',self.root,self.records,self.units)
    def test_changed_retained_or_application_image_refused(self):
        for name in self.records:
            records=copy.deepcopy(self.records);records[name]['Image']='b'*64
            with self.assertRaises(ValueError):validate('native',self.root,records,self.units)
    def test_public_marker_or_symlink_refused(self):
        (self.root/'ready').chmod(0o644)
        with self.assertRaises(ValueError):validate('native',self.root,self.records,self.units)
        (self.root/'ready').chmod(0o600)
        (self.root/'container-mode').symlink_to(self.root/'ready')
        with self.assertRaises(ValueError):validate('native',self.root,self.records,self.units)
if __name__=='__main__':unittest.main()

