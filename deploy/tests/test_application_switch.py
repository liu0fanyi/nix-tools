"""Exercise the controller with actual private files/SQLite and simulated service transitions."""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
spec=importlib.util.spec_from_file_location('entryswitch',Path(__file__).resolve().parents[2]/'scripts/activate-application-entry.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from application_entry_transaction import atomic,digest

class Controller(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='entry-switch-test-');self.base=Path(self.temp.name)
  self.root=self.base/'state-root';self.root.mkdir(mode=0o700);atomic(self.root/'startup.lock','');atomic(self.root/'startup-mode','native\n')
  self.units=self.base/'units';self.units.mkdir(mode=0o700)
  self.runtime=self.base/'runtime';self.runtime.mkdir(mode=0o700)
  self.release=self.base/'release';self.release.mkdir(mode=0o700)
  self.candidate=self.base/'candidate';(self.candidate/'lib/systemd/user').mkdir(parents=True)
  self.status={n:'active' for n in m.UNITS};self.ingress=True;self.fail_gateway=False;self.commands=[]
  self.entries={}
  for name in ['Caddyfile','haproxy.readonly.cfg','application-compose.json','native-nuc-control.json']:
   target=self.runtime/name;atomic(target,'old-'+name);atomic(self.release/name,'new-'+name);self.entries[name]=target
  for role in ['private','readonly']:
   role_root=self.root/role;role_root.mkdir(mode=0o700);(role_root/'config').mkdir(mode=0o700);state=role_root/'state';state.mkdir(mode=0o700)
   atomic(state/'instance.lock','');(state/'metadata').mkdir(mode=0o700);atomic(state/'metadata/key','identity-'+role)
   with closing(sqlite3.connect(state/'core.db')) as db,db:db.execute('CREATE TABLE events(value TEXT)')
   (state/'core.db').chmod(0o600)
   for name in ['application-entry.toml','basic.entries']:
    target=role_root/'config'/name;atomic(self.release/(role+'-'+name),'new-'+role+'-'+name);self.entries[role+'-'+name]=target
  self.pki=self.base/'pki';self.pki.mkdir(mode=0o700);atomic(self.pki/'root.key','same-ca')
  for name in m.UNITS:(self.units/name).symlink_to('/nix/store/old/'+name)
  for name in m.NEW_UNITS:atomic(self.candidate/'lib/systemd/user'/name,'candidate-'+name)
  self.manifest={'candidate':str(self.candidate),'files':{n:digest(self.release/n) for n in self.entries}}
  self.patches=[patch.object(m,'ROOT',self.root),patch.object(m,'UNIT_DIR',self.units),patch.object(m,'ENTRIES',self.entries),patch.object(m,'PKI',[self.pki]),patch.object(m,'run',self.command),patch.object(m,'stopped',self.stopped),patch.object(m,'read_inventory',self.inventory),patch.object(m,'load_control',lambda:{'compose':['podman','compose','-f',str(self.runtime/'model')],'source_images':{}}),patch.object(m,'validate',lambda *args,**kwargs:None),patch.object(m,'container',lambda *args,**kwargs:{'State':{'Running':self.ingress}})]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def inventory(self,run):
  records={'dufs-plus_'+name+'_1':{'State':{'Running':self.ingress if name in {'caddy','readonly-gateway'} else True}} for name in ['caddy','readonly-gateway','authelia','ddns-go']}
  return records,dict(self.status)
 def stopped(self):
  if any(v=='active' for v in self.status.values()) or self.ingress:raise ValueError('not stopped')
 def command(self,args,**kwargs):
  self.commands.append(args)
  if args[:3]==['systemctl','--user','stop']:
   for n in args[3:]:self.status[n]='inactive'
  elif args[:3]==['systemctl','--user','start']:
   for n in (m.UNITS if (self.units/'tag-nuc-bridge.service').is_symlink() else m.NEW_UNITS):self.status[n]='active'
  elif args[:2]==['podman','stop']:self.ingress=False
  elif 'up' in args:
   if self.fail_gateway:
    # A new native writer committed a row before gateway recreation failed.
    with closing(sqlite3.connect(self.root/'private/state/core.db')) as db,db:db.execute("INSERT INTO events VALUES ('new-write')")
    self.fail_gateway=False;raise RuntimeError('gateway recreate failed')
   self.ingress=True
  return SimpleNamespace(stdout='',returncode=0)
 def test_complete_handover_order_and_backups(self):
  m.execute(self.release,self.manifest)
  self.assertEqual((self.root/'startup-mode').read_text(),'native\n')
  self.assertFalse((self.units/'tag-nuc-bridge.service').is_symlink())
  self.assertEqual((self.pki/'root.key').read_text(),'same-ca')
  self.assertTrue((self.release/'p2/caddy-state.tar').is_file())
  stop_index=next(i for i,a in enumerate(self.commands) if a[:2]==['podman','stop'])
  start_index=next(i for i,a in enumerate(self.commands) if a[:3]==['systemctl','--user','start'])
  up_index=next(i for i,a in enumerate(self.commands) if 'up' in a)
  self.assertLess(stop_index,start_index);self.assertLess(start_index,up_index)
  self.assertEqual(self.commands[0],['systemctl','--user','stop','tag-native-nuc.target'])
  self.assertFalse(any('authelia' in a or 'ddns-go' in a for a in self.commands))
 def test_failed_gateway_then_rollback_retains_new_state(self):
  self.fail_gateway=True
  with self.assertRaises(RuntimeError):m.execute(self.release,self.manifest)
  self.assertEqual((self.root/'startup-mode').read_text(),'transition\n');self.stopped()
  m.execute(self.release,self.manifest,rollback=True)
  with closing(sqlite3.connect(self.root/'private/state/core.db')) as db:self.assertEqual(db.execute('SELECT value FROM events').fetchall(),[('new-write',)])
  self.assertEqual((self.root/'private/state/metadata/key').read_text(),'identity-private')
  self.assertEqual((self.pki/'root.key').read_text(),'same-ca')
  self.assertEqual((self.runtime/'Caddyfile').read_text(),'old-Caddyfile')
  self.assertEqual(os.readlink(self.units/'tag-nuc-bridge.service'),'/nix/store/old/tag-nuc-bridge.service')
  self.assertFalse((self.entries['private-application-entry.toml']).exists())
 def test_input_recheck_refuses_before_production_barrier(self):
  def drift():raise ValueError('input changed')
  with self.assertRaises(ValueError):m.execute(self.release,self.manifest,verify_inputs=drift)
  self.assertEqual((self.root/'startup-mode').read_text(),'native\n')
  self.assertEqual(self.commands,[])
 def test_legacy_transport_modes_and_symlink_refusal(self):
  path=self.runtime/'haproxy.readonly.cfg';path.chmod(0o644)
  self.assertEqual(m.legacy_transport(path),'old-haproxy.readonly.cfg')
  path.chmod(0o664)
  with self.assertRaises(ValueError):m.legacy_transport(path)
  path.unlink();path.symlink_to(self.release/'haproxy.readonly.cfg')
  with self.assertRaises(ValueError):m.legacy_transport(path)
 def test_pc_confirmation_gate_and_default_do_not_activate(self):
  spec=importlib.util.spec_from_file_location('pcswitch',Path(__file__).resolve().parents[2]/'scripts/activate-application-entry-pc.py')
  pc=importlib.util.module_from_spec(spec);spec.loader.exec_module(pc)
  with patch.object(sys,'argv',['script','--apply']),patch.object(pc,'preflight') as probe:
   with self.assertRaises(ValueError):pc.main()
   probe.assert_not_called()
  with patch.object(sys,'argv',['script']),patch.object(pc,'preflight',return_value=({},self.runtime/'entry')),patch.object(pc,'execute') as apply,patch('builtins.print'):
   pc.main();apply.assert_not_called()
 def test_saved_editor_confirmation_precedes_preflight(self):
  with patch.object(sys,'argv',['script','/not-a-release','--manifest-sha256','0'*64,'--apply']),patch.object(m,'preflight') as probe:
   with self.assertRaises(ValueError):m.main()
   probe.assert_not_called()

if __name__=='__main__':unittest.main()
