#!/usr/bin/env python3
"""Enable approved native peers' signatures using the existing offline config transaction."""
import argparse,dataclasses,hashlib,importlib.machinery,importlib.util,json,os,re,sys,tomllib
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--scope',choices=['pc','nuc'],required=True);P.add_argument('--apply',action='store_true');P.add_argument('--editors-saved',action='store_true');a=P.parse_args()
MANAGER=Path('/nix/store/fkz9idgp15689b62yqsrqfp503c1lbf1-tag-native-release-manager')
PROGRAM=Path('/nix/store/9xslvb4s16mjwhas2vsdaj1ja483g8j6-tag-all-workspace-native-0.1.0')
sys.path.insert(0,str(MANAGER/'libexec'))
from native_application_release import Manager,fixed_scope
from application_entry_transaction import ConfigurationTransaction,atomic,private,digest,create_lock,exclusive,offline_states

def load(name,path):
 l=importlib.machinery.SourceFileLoader(name,str(path));s=importlib.util.spec_from_loader(l.name,l);m=importlib.util.module_from_spec(s);l.exec_module(m);return m
m=load('strict_signatures_helper','/nix/store/r5hddb079z8wairfr09l2nmizakihr0c-tag-browser-workspaces.py')
scope=fixed_scope(a.scope)
if a.scope=='nuc':
 adapter=load('strict_signatures_adapter','/nix/store/lm5h05zqpnvpbifg4wjqmbjaa91qyxfp-tag-native-shared-directories.py');m.UNITS=adapter.UNITS;directories=adapter.Adapter(m).d
 scope=dataclasses.replace(scope,units=scope.units[:1],states=scope.states[:1],connections=scope.connections[:1],probes=scope.probes[:1])
else:directories=m.Directories()
i=directories.installation();assert i['nodeId']==a.scope
config=private(i['config']);text=config.read_text();old=tomllib.loads(text)
trusted=private(i['metadata']/'paired-peers.json');peers=json.loads(trusted.read_text());remote={'pc':'nuc','nuc':'pc'}[a.scope]
assert old.get('pairing',{}).get('enabled') is True and old.get('sync',{}).get('enabled') is not False
assert len(peers)==1 and peers[0]['identity']['node_id']==remote
configured={u.rstrip('/') for u in [*old['sync'].get('peers',[]),*old['sync'].get('peer_nodes',{}).values()]}
assert configured=={peers[0]['url'].rstrip('/')}
manager=Manager(scope);manager.tasks_idle();manager.ready(PROGRAM)
root=Path('/home/liou/.local/share/tag-all/strict-signature-releases')
if not root.exists():root.mkdir(mode=0o700)
private(root,True);release=root/('canonical-roots-20261101-'+a.scope)
if release.exists():
 private(release,True);transaction=ConfigurationTransaction(release/'transaction',{config});plan=json.loads(private(release/'plan.json').read_text())
 assert plan['config']==str(config) and plan['peer_sha256']==digest(trusted) and plan['scope']==a.scope
 if transaction.load()['phase']=='activated':
  transaction.verify_after();assert old['sync']['require_signatures'] is True
  print(json.dumps({'scope':a.scope,'strict_signatures':True,'already_applied':True,'database_restored':False}));sys.exit(0)
 transaction.verify_before()
else:
 assert old['sync']['require_signatures'] is False
 newtext,count=re.subn(r'((?:"require_signatures"|require_signatures)\s*=\s*)false\b',r'\g<1>true',text);assert count==1
 new=tomllib.loads(newtext);expected=json.loads(json.dumps(old));expected['sync']['require_signatures']=True;assert new==expected
 release.mkdir(mode=0o700);atomic(release/'after.toml',newtext)
 plan={'scope':a.scope,'config':str(config),'before_sha256':digest(config),'after_sha256':digest(release/'after.toml'),'peer_sha256':digest(trusted),'units':list(scope.units),'upholding':manager.uphold_binding()}
 atomic(release/'plan.json',json.dumps(plan,indent=2)+'\n')
 transaction=ConfigurationTransaction(release/'transaction',{config});transaction.create({config:{'kind':'file','source':str(release/'after.toml'),'sha256':plan['after_sha256']}})
if not a.apply:
 print(json.dumps({'scope':a.scope,'prepared':str(release),'changed_fields':['sync.require_signatures'],'peer_addresses_and_identities_unchanged':True,'activated':False}));sys.exit(0)
if not a.editors_saved:raise ValueError('Explicit saved-editor cutover authorization required')
lock=scope.release_root/'update.lock';create_lock(lock)
with exclusive(lock):
 transaction.verify_before();assert digest(trusted)==plan['peer_sha256'];manager.tasks_idle()
 inodes=[(state/'core.db').stat().st_ino for state in scope.states]
 with manager.suspend_upholding(plan):
  manager.run(['systemctl','--user','stop',*scope.units])
  try:
   with offline_states(scope.states,manager.stopped):
    manager.tasks_idle();transaction.verify_before();assert digest(trusted)==plan['peer_sha256'];transaction.install();transaction.verify_after()
   manager.run(['systemctl','--user','start',*scope.units]);manager.ready(PROGRAM)
   assert tomllib.loads(config.read_text())['sync']['require_signatures'] is True and digest(trusted)==plan['peer_sha256']
   assert inodes==[(state/'core.db').stat().st_ino for state in scope.states]
   transaction.phase('activated')
  except Exception:
   manager.run(['systemctl','--user','stop',*scope.units])
   with offline_states(scope.states,manager.stopped):transaction.install(rollback=True);transaction.verify_before()
   manager.run(['systemctl','--user','start',*scope.units]);manager.ready(PROGRAM);transaction.phase('failed-original-config-restored');raise
print(json.dumps({'scope':a.scope,'strict_signatures':True,'changed_fields':['sync.require_signatures'],'peer_addresses_and_identities_unchanged':True,'database_inode_preserved':True,'database_restored':False,'configuration_backup':str(release/'transaction/before')}))
