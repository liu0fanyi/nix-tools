import copy
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]))
from native_nuc_startup import compose_action,unit_dropins,dispatch,read_inventory,host_environment
sys.path.insert(0,str(Path(__file__).parent))
from test_native_nuc_guard import Guard
from native_nuc_bundle import UNITS
from native_nuc_plan import PREFIX,REPLACE,KEEP

class Startup(Guard):
    def setUp(self):
        super().setUp()
        self.config={'root':str(self.root),'source_images':{name:'a'*64 for name in self.records},'compose':['podman','compose','-f','fixture.yaml']}
        for name,value in [('startup.lock',''),('startup-mode','native\n')]:
            (self.root/name).write_text(value);(self.root/name).chmod(0o600)
        self.calls=[]
    def invoke(self,argv,check=True,capture_output=True):
        import json
        self.calls.append(argv)
        if argv[:2]==['podman','inspect']:return subprocess.CompletedProcess(argv,0,json.dumps(list(self.records.values())), '')
        if argv[:3]==['systemctl','--user','show']:
            return subprocess.CompletedProcess(argv,0,'LoadState=loaded\nActiveState='+self.units[argv[3]]+'\n','')
        return subprocess.CompletedProcess(argv,0,'','')
    def test_inventory_uses_host_store_and_bus_despite_core_git_home(self):
        env=host_environment({'HOME':'/private/git-home','CONTAINER_HOST':'unix:///tools/runtime.sock','CONTAINERS_STORAGE_CONF':'/private/storage.conf'})
        self.assertEqual(env['HOME'],'/home/liou')
        self.assertEqual(env['XDG_DATA_HOME'],'/home/liou/.local/share')
        self.assertEqual(env['DBUS_SESSION_BUS_ADDRESS'],'unix:path=/run/user/1000/bus')
        self.assertNotIn('CONTAINER_HOST',env);self.assertNotIn('CONTAINERS_STORAGE_CONF',env)
    def test_all_seven_services_have_additive_prechecks(self):
        drops=unit_dropins(['/runtime/python3','/private/startup.py'])
        self.assertEqual(set(drops),set(UNITS))
        for name,text in drops.items():
            if name.endswith('.service'):
                self.assertIn('ExecStartPre=',text);self.assertIn('native-check',text)
                self.assertNotIn('ExecStartPre=\n',text)
        self.assertIn('Requires=dufs-plus-compose.service',drops['tag-native-nuc.target'])
    def test_native_boot_starts_only_four_keepers_without_dependencies(self):
        dispatch(self.config,['compose','up','-d'],self.invoke)
        self.assertEqual(self.calls[-1],self.config['compose']+['up','-d','--no-deps',*KEEP])
    def test_old_writer_refuses_before_any_compose_or_service_start(self):
        for service in REPLACE:
            self.records[PREFIX+service+'_1']['State']['Running']=True
            for args in [['native-check'],['compose','up','-d']]:
                self.calls=[]
                with self.assertRaises(ValueError):dispatch(self.config,args,self.invoke)
                self.assertFalse(any(a[:2]==['podman','compose'] for a in self.calls))
            self.records[PREFIX+service+'_1']['State']['Running']=False
    def test_transition_and_competing_cutover_block_mutations(self):
        (self.root/'startup-mode').write_text('transition\n')
        for args in [['native-check'],['compose','up','-d'],['compose','down']]:
            with self.assertRaises(ValueError):dispatch(self.config,args,self.invoke)
        (self.root/'startup-mode').write_text('native\n')
        with (self.root/'startup.lock').open('r+') as file:
            fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):dispatch(self.config,['native-check'],self.invoke)
    def test_fallback_refuses_native_active_old_database_and_recreation(self):
        (self.root/'startup-mode').write_text('container\n')
        (self.root/'container-mode').write_text('explicit-container-fallback\n');(self.root/'container-mode').chmod(0o600)
        dispatch(self.config,['compose','start'],self.invoke)
        for unit in UNITS:
            self.units[unit]='active'
            with self.assertRaises(ValueError):dispatch(self.config,['compose','start'],self.invoke)
            self.units[unit]='inactive'
        self.records[PREFIX+'tag-server_1']['Mounts'][0]['Source']='/old/db'
        with self.assertRaises(ValueError):dispatch(self.config,['compose','start'],self.invoke)
        with self.assertRaises(ValueError):dispatch(self.config,['compose','up','-d'],self.invoke)
    def test_native_down_preserves_containers_and_forbidden_actions_rejected(self):
        self.assertEqual(compose_action('native',['down']),['stop',*KEEP])
        for args in [['up','-d','tag-server'],['up','-d','--remove-orphans'],['run','caddy'],['restart'],['up','-d','-d'],['start','caddy','caddy']]:
            with self.assertRaises(ValueError):compose_action('native',args)
        self.assertEqual(compose_action('native',['up','-d','--force-recreate','caddy']),['up','-d','--no-deps','--force-recreate','caddy'])
    def test_missing_status_and_bus_failure_fail_closed(self):
        def bad(argv,**kwargs):
            if argv[0]=='systemctl':return subprocess.CompletedProcess(argv,1,'','bus failure')
            return self.invoke(argv,**kwargs)
        with self.assertRaises(ValueError):read_inventory(bad)
if __name__=='__main__':unittest.main()
