import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tomllib
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]));sys.path.insert(0,str(Path(__file__).parent))
from test_native_nuc_snapshot import DoubleSnapshot
from native_nuc_switch import Controller,atomic_file,fallback_overlay,hook_control
from native_nuc_bundle import UNITS,digest
from native_nuc_startup import dispatch
from native_nuc_plan import PREFIX,REPLACE,KEEP
from native_nuc_snapshot import tree_hashes
sys.path.insert(0,str(Path(__file__).parents[2]/'deploy/scripts'))
import render

class Switch(unittest.TestCase):
    def setUp(self):
        DoubleSnapshot.setUp(self)
        self.runtime=self.root/'runtime';self.runtime.mkdir(mode=0o700)
        self.release=self.root/'release';self.release.mkdir(mode=0o700)
        self.management=self.root/'management';self.management.mkdir(mode=0o700)
        self.config_data=tomllib.loads((Path(__file__).parents[2]/'deploy/instances/home.toml').read_text())
        paths=self.config_data['paths'];paths.update(workspace=self.roles['private']['mounts']['/workspace'],tag_data=self.roles['private']['mounts']['/data'],readonly=self.roles['readonly']['mounts']['/workspace'],readonly_tag_data=self.roles['readonly']['mounts']['/data'],media=str(self.root/'media'),whisper_models=str(self.root/'models'),dist=str(self.root/'dist'),caddy_data=str(self.root/'caddy-data'),secrets=str(self.root/'secrets'),required_mounts=[])
        for name in ['media','models','dist','caddy-data','secrets']:(self.root/name).mkdir(mode=0o700)
        self.pki.rename(self.root/'caddy-data/pki');self.pki=self.root/'caddy-data/pki'
        self.original_caddy=render.render_caddy(self.config_data,('fixture','$2a$14$synthetic-test-only'))
        for name,value in {'Caddyfile':self.original_caddy,'tag-server.toml':self.config.read_text(),'compose.env':'COMPOSE_PROJECT_NAME=dufs-plus\n','compose.yaml':'services: {}\n','compose-files.txt':str(self.runtime/'compose.yaml')+'\n','compose-control':'#!/bin/sh\nset -eu\n# preserve data disk checks\nexec podman compose "$@"\n'}.items():atomic_file(self.runtime/name,value,0o700 if name=='compose-control' else 0o600)
        atomic_file(self.root/'secrets/tag-server.env','EXAMPLE=fixture\n');atomic_file(self.root/'secrets/tag-peer-admin.env',"TAG_PEER_ADMIN_TOKEN='synthetic-only-token-123456789012345678'\n")
        for name in ['manage.py','render.py']:
            atomic_file(self.management/name,'# old fixture control\n');atomic_file(self.release/name,'# guarded fixture control\n')
        atomic_file(self.release/'native_nuc_startup.py','# fixture shim; no execution\n')
        self.records={};self.statuses=dict.fromkeys(UNITS,'unknown');self.calls=[];self.fail=None
        mappings={'tag-server':[(paths['tag_data'],'/data',True),(paths['workspace'],'/workspace',True),(paths['media'],'/workspace/media',True),(paths['whisper_models'],'/models',False)],'tag-server-readonly':[(paths['readonly_tag_data'],'/data',True),(paths['readonly'],'/workspace',False)],'dufs':[(paths['workspace'],'/data',True),(paths['media'],'/data/media',True)],'dufs-readonly':[(paths['readonly'],'/data',False)],'tag-peer-discovery':[(paths['tag_data'],'/data',True)],'caddy':[(paths['caddy_data'],'/data/caddy',True),(paths['dist'],'/srv/dist',False),(str(self.runtime/'Caddyfile'),'/etc/caddy/Caddyfile',False)]}
        for s in REPLACE+KEEP:
            name=PREFIX+s+'_1';command=['/bin/sh','-ec','exec /app/tag-server --database /data/tag_all.db'] if s.startswith('tag-server') else self.args if s=='tag-peer-discovery' else ['fixture']
            self.records[name]={'Name':name,'Image':'a'*64,'State':{'Running':True},'Config':{'Cmd':command,'Labels':{'io.podman.compose.project':'dufs-plus'}},'HostConfig':{'RestartPolicy':{'Name':'unless-stopped'}},'Mounts':[{'Type':'bind','Source':src,'Destination':dest,'RW':rw} for src,dest,rw in mappings.get(s,[])]}
        self.candidate=Path('/nix/store/49gihkvq010kiscjjvcgzmbll7yklvps-tag-all-native-nuc-candidate')
        self.manifest={'candidate':str(self.candidate),'source_images':{n:'a'*64 for n in self.records},'units':{n:digest(self.candidate/'lib/systemd/user'/n) for n in UNITS},'whisper_package':'/nix/store/fixture-whisper'}
        self.controller=Controller(self.release,self.manifest,self.config_data,self.invoke,root=self.dest,runtime=self.runtime,units_dir=self.root/'units',management_dir=self.management)
    def invoke(self,argv,check=True,capture_output=True):
        self.calls.append(list(argv))
        if self.fail and self.fail(argv):raise subprocess.CalledProcessError(1,argv)
        if argv[:2]==['podman','inspect']:return subprocess.CompletedProcess(argv,0,json.dumps(list(self.records.values())),'')
        if argv[:3]==['systemctl','--user','show']:
            state=self.statuses[argv[3]]
            return subprocess.CompletedProcess(argv,0,'LoadState='+('not-found' if state=='unknown' else 'loaded')+'\nActiveState='+state+'\n','')
        if argv[:2]==['podman','update']:self.records[argv[-1]]['HostConfig']['RestartPolicy']['Name']='no'
        elif argv[:2]==['podman','stop']:
            for n in argv[4:]:self.records[n]['State']['Running']=False
        elif argv[:3]==['systemctl','--user','start']:
            control=json.loads((self.runtime/'native-nuc-control.json').read_text())
            for n in UNITS:
                if n.endswith('.service'):dispatch(control,['native-check'],self.invoke)
            self.statuses=dict.fromkeys(UNITS,'active')
            assert json.loads(self.controller.journal.read_text())['native_may_have_written']
            for role in ['private','readonly']:
                with closing(sqlite3.connect(self.dest/role/'state/core.db')) as db,db:db.execute("INSERT INTO fixture VALUES ('native-new-write')")
        elif argv[:3]==['systemctl','--user','stop']:
            self.assertEqual(set(argv[3:]),set(UNITS));self.statuses=dict.fromkeys(UNITS,'inactive')
        elif argv[:2]==['podman','compose']:
            files=[Path(argv[i+1]) for i,a in enumerate(argv) if a=='-f']
            overlays={}
            for p in files:
                if p.suffix=='.json':
                    for s,item in json.loads(p.read_text())['services'].items():overlays.setdefault(s,{}).update(item)
            if argv[-1]=='caddy':
                for value in overlays['caddy']['volumes']:
                    source,target,mode=value.split(':');m={'source':source,'target':target,'read_only':mode=='ro'}
                    mounts=self.records[PREFIX+'caddy_1']['Mounts'];mounts[:]=[p for p in mounts if p['Destination']!=m['target']]
                    mounts.append({'Type':'bind','Source':m['source'],'Destination':m['target'],'RW':not m['read_only']})
            if '--no-start' in argv:
                self.assertTrue(all(v=='inactive' for v in self.statuses.values()))
                for s in REPLACE:
                    item=self.records[PREFIX+s+'_1'];overlay=overlays[s]
                    if 'command' in overlay:item['Config']['Cmd']=overlay['command']
                    for value in overlay.get('volumes',[]):
                        source,target,mode=value.split(':');m={'source':source,'target':target,'read_only':mode=='ro'}
                        item['Mounts']=[p for p in item['Mounts'] if p['Destination']!=m['target']]+[{'Type':'bind','Source':m['source'],'Destination':m['target'],'RW':not m['read_only']}]
            elif 'start' in argv:
                for s in REPLACE:
                    item=self.records[PREFIX+s+'_1'];item['State']['Running']=True
                    if s.startswith('tag-server'):
                        data=next(m['Source'] for m in item['Mounts'] if m['Destination']=='/data')
                        with closing(sqlite3.connect(Path(data)/'core.db')) as db:self.assertIn(('native-new-write',),db.execute('SELECT name FROM fixture').fetchall())
        return subprocess.CompletedProcess(argv,0,'','')
    def test_local_entry_is_readonly_and_requires_explicit_editor_acknowledgement(self):
        import importlib.util
        file=Path(__file__).parents[1]/'native-nuc-switch.py'
        spec=importlib.util.spec_from_file_location('local_nuc_switch',file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        receipt={'prepared_release':'/home/liou/.local/share/tag-all/nuc-native-release/'+'a'*64,'manifest_sha256':'a'*64}
        argv=module.command(receipt)
        self.assertNotIn('--activate',argv[-1]);self.assertNotIn('--rollback',argv[-1])
        with self.assertRaisesRegex(ValueError,'Save and close'):module.command(receipt,activate=True)
        bad=dict(receipt,prepared_release='/tmp/elsewhere')
        with self.assertRaises(ValueError):module.command(bad)
        self.assertIn('--activate --editors-closed',module.command(receipt,activate=True,editors_closed=True)[-1])

    def test_dry_run_has_no_filesystem_or_service_mutation(self):
        (self.runtime/'compose-files.txt').chmod(0o664)
        before=tree_hashes(self.root);plan=self.controller.plan()
        self.assertFalse(plan['source_database_read']);self.assertEqual(tree_hashes(self.root),before)
        self.assertTrue(all(a[:2]==['podman','inspect'] or a[:3]==['systemctl','--user','show'] for a in self.calls))
    def test_full_double_snapshot_native_write_fallback_preserves_new_data(self):
        original={r:(Path(v['mounts']['/data'])/'tag_all.db').read_bytes() for r,v in self.roles.items()}
        (self.runtime/'compose-files.txt').chmod(0o664)
        result=self.controller.activate();self.assertTrue(result['all_native_units_active'])
        self.assertEqual((self.runtime/'compose-files.txt').stat().st_mode&0o777,0o600)
        self.assertIn('unix//run/tag-native/private-api.sock',(self.runtime/'Caddyfile').read_text())
        self.assertEqual((self.dest/'startup-mode').read_text(),'native\n')
        self.assertTrue(self.controller.rollback()['rollback_uses_both_new_databases'])
        self.assertEqual((self.runtime/'Caddyfile').read_text(),self.original_caddy)
        self.assertEqual((self.dest/'startup-mode').read_text(),'container\n')
        for r,v in self.roles.items():
            self.assertEqual((Path(v['mounts']['/data'])/'tag_all.db').read_bytes(),original[r])
            self.assertEqual((self.dest/r/'state/metadata/identity').read_text(),r+'-identity')
        self.assertEqual((self.dest/'backup/pki/root.key').read_text(),'synthetic-ca')
        self.assertEqual(json.loads(self.controller.journal.read_text())['phase'],'container-active')
    def test_failure_after_possible_native_writes_never_reopens_source(self):
        self.fail=lambda a:a[:3]==['systemctl','--user','start']
        with self.assertRaises(subprocess.CalledProcessError):self.controller.activate()
        self.assertTrue(json.loads(self.controller.journal.read_text())['native_may_have_written'])
        self.assertTrue(all(not self.records[PREFIX+s+'_1']['State']['Running'] for s in REPLACE))
        self.assertFalse(any(a[:2]==['podman','compose'] and 'start' in a for a in self.calls))
    def test_corrupt_second_database_blocks_publish_and_old_restart(self):
        (Path(self.roles['readonly']['mounts']['/data'])/'tag_all.db').write_bytes(b'corrupt')
        with self.assertRaises(sqlite3.DatabaseError):self.controller.activate()
        self.assertFalse(self.dest.exists())
        self.assertTrue(all(not self.records[PREFIX+s+'_1']['State']['Running'] for s in REPLACE))
        self.assertTrue((self.runtime/'native-nuc-control').exists())
    def test_new_caddy_edit_refused_without_stopping_any_service(self):
        self.controller.activate();atomic_file(self.runtime/'Caddyfile',(self.runtime/'Caddyfile').read_text()+'# new user edit\n')
        self.calls=[]
        with self.assertRaisesRegex(ValueError,'New Caddy'):self.controller.rollback()
        self.assertEqual(self.calls,[])
    def test_changed_runtime_input_refuses_fallback(self):
        self.controller.activate();atomic_file(self.runtime/'compose.env','changed=true\n')
        with self.assertRaisesRegex(ValueError,'Original runtime'):self.controller.rollback()
    def test_native_unit_incomplete_stop_prevents_fallback_creation(self):
        self.controller.activate();original=self.invoke
        def slow(argv,**kwargs):
            result=original(argv,**kwargs)
            if argv[:3]==['systemctl','--user','stop']:self.statuses[UNITS[0]]='deactivating'
            return result
        self.controller.run=slow;self.calls=[]
        with patch('native_nuc_switch.time.sleep'),self.assertRaisesRegex(ValueError,'Complete stop'):self.controller.rollback()
        self.assertFalse(any('--no-start' in a for a in self.calls))
    def test_bad_database_shape_or_collision_refused_before_stop(self):
        self.records[PREFIX+'tag-server_1']['Config']['Cmd']=['fixture-other-db']
        with self.assertRaisesRegex(ValueError,'fixed original'):self.controller.activate()
        self.assertFalse(self.controller.journal.exists())
    def test_operation_lock_competing_call_and_symlink_rejected(self):
        import fcntl
        atomic_file(self.release/'operation.lock','')
        with (self.release/'operation.lock').open('r+') as file:
            fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.controller.activate()
        target=self.root/'unexpected';target.symlink_to(self.env)
        with self.assertRaises(ValueError):atomic_file(target,'unsafe')
        self.assertNotEqual(self.env.read_text(),'unsafe')
if __name__=='__main__':unittest.main()
