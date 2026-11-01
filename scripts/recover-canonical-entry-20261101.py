"""Finish the committed NUC receipt using a byte-identical CLI and fixed entry adapter.

Only an owned temporary read-only service bind is added. The original fourteen
configuration files and receipt are replayed by their original controller.
Remove this bind after the ordinary permanent program update succeeds.
"""
import sys,json,hashlib,os,socket,stat,subprocess
from pathlib import Path
assert socket.gethostname()=='nuc' and os.getuid()==1000
original=Path('/nix/store/fkz9idgp15689b62yqsrqfp503c1lbf1-tag-native-release-manager')
old=Path('/nix/store/9xslvb4s16mjwhas2vsdaj1ja483g8j6-tag-all-workspace-native-0.1.0')
new=Path('/nix/store/86rq1dm9pivnarz4n3ilqzz65174g14d-tag-all-workspace-native-0.1.0')
release=Path('/home/liou/.local/state/tag-workspace-namespace/nuc/c618556795fbc8ed765608d5ad6881a1d63fffbc8e809d116b02ff59b396eed1')
sys.path.insert(0,str(original/'libexec'))
from workspace_namespace_command import driver,controller,verify_inputs
from application_entry_transaction import private,atomic,digest,ConfigurationTransaction
product,_=driver(Path('/nix/store/r8cmw8qvr7wfdyzjhcak3hk0gl3ynmcl-tag-workspace-namespace-driver/libexec'))
cutover,_=controller('nuc',product);_,plan=cutover.load(release);verify_inputs(plan)
assert cutover.database_status(plan)=='applied-expected'
assert digest(old/'libexec/tag-server-workspace')==digest(new/'libexec/tag-server-workspace')=='952d05baf5c6360e43c5fc3b7c56e7102b429ce5f2e1b549d47e5e8dc679023b'
assert (new/'share/tag-all/workspace-namespace-entry').read_text()=='canonical-v2\n'
unit='tag-nuc-private-core.service';assert cutover.scope.units[0]==unit
runtime=Path('/run/user/1000/systemd/user')/(unit+'.d')
runtime.parent.mkdir(mode=0o700,exist_ok=True);assert runtime.parent.stat().st_uid==os.getuid() and not runtime.parent.is_symlink() and not runtime.parent.stat().st_mode&0o022
runtime.mkdir(mode=0o700,exist_ok=True)
assert runtime.is_dir() and not runtime.is_symlink() and runtime.stat().st_uid==os.getuid() and not runtime.stat().st_mode&0o022
bind=runtime/'95-canonical-entry-recovery.conf'
content='# Owned canonical entry forward recovery; remove after permanent upgrade.\n[Service]\nBindReadOnlyPaths='+str(new/'libexec/tag-entry-adapter')+':'+str(old/'libexec/tag-entry-adapter')+'\n'
if bind.exists() or bind.is_symlink():assert private(bind).read_text()==content
else:atomic(bind,content)
cutover.manager.run(['systemctl','--user','daemon-reload'])
transaction=ConfigurationTransaction(release/'transaction',cutover.scope.targets)
if transaction.load()['phase']=='activated':
 transaction.verify_after();result={'phase':'activated','namespace':str(cutover.scope.namespace),'database_restored':False}
else:result=cutover.apply(release,editors_saved=True)
cutover.manager.ready();assert cutover.manager.live_program(cutover.manager.properties(unit),new)
assert result['phase']=='activated' and cutover.database_status(plan)=='applied-expected'
receipt={'result':result,'original_release':str(release),'old_package':str(old),'fixed_package':str(new),'temporary_service_bind':str(bind),'bind_sha256':digest(bind),'same_tested_cli_sha256':digest(new/'libexec/tag-server-workspace'),'host_nix_store_modified':False,'database_restored':False}
atomic(release/'entry-recovery.json',json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
