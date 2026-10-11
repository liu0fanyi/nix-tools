from pathlib import Path
import copy,json,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from application_entry_transaction import ConfigurationTransaction,atomic,digest
from application_entry_provider import compatible,materialize,verify,materialize_transport_mode,verify_transport_mode,materialize_source,compatible_readonly_source
from application_nuc_ingress import candidate_readonly_transport
class Provider(unittest.TestCase):
 def test_only_equivalent_host_representation_changes(self):
  model={'services':{'readonly-gateway':{'extra_hosts':{'host.containers.internal':'host-gateway'}},'caddy':{'ports':['5009']},'authelia':{'untouched':True},'ddns-go':{'untouched':True}}}
  result=compatible(model);self.assertEqual(result['services']['readonly-gateway']['extra_hosts'],['host.containers.internal:host-gateway'])
  result['services']['readonly-gateway']['extra_hosts']=model['services']['readonly-gateway']['extra_hosts'];self.assertEqual(result,model)
  wrong=copy.deepcopy(model);wrong['services']['readonly-gateway']['extra_hosts']['unreviewed']='outside'
  with self.assertRaises(ValueError):compatible(wrong)
 def test_durable_correction_and_semantic_drift_refusal(self):
  with tempfile.TemporaryDirectory(prefix='entry-provider-test-') as temp:
   root=Path(temp);release=root/'release';release.mkdir(mode=0o700);(release/'p2').mkdir(mode=0o700);runtime=root/'runtime';runtime.mkdir(mode=0o700)
   model={'services':{'readonly-gateway':{'extra_hosts':{'host.containers.internal':'host-gateway'}},'caddy':{'ports':['5009']}}}
   atomic(release/'application-compose.json',json.dumps(model));control={'files':{str(runtime/'application-compose.json'):digest(release/'application-compose.json')}};atomic(release/'native-nuc-control.json',json.dumps(control))
   desired={runtime/n:{'kind':'file','source':str(release/n),'sha256':digest(release/n)} for n in ['application-compose.json','native-nuc-control.json']}
   for p in desired:atomic(p,'original')
   primary=ConfigurationTransaction(release/'p2/primary',desired);primary.create(desired);primary.install();overrides=materialize(release,runtime,primary);primary.verify_after(overrides)
   self.assertEqual(json.loads((runtime/'application-compose.json').read_text())['services']['readonly-gateway']['extra_hosts'],['host.containers.internal:host-gateway'])
   self.assertEqual(json.loads((release/'application-compose.json').read_text()),model)
   source=release/'p2/provider-input/application-compose.json';modified=json.loads(source.read_text());modified['services']['caddy']['ports']=['5006'];atomic(source,json.dumps(modified))
   correction=ConfigurationTransaction(release/'p2/provider-transaction',desired);journal=correction.load();journal['records'][str(runtime/'application-compose.json')]['after']['sha256']=digest(source);correction.save(journal);correction.install()
   with self.assertRaises(ValueError):verify(release,runtime,primary)
 def test_transport_mount_permission_is_only_nonsecret_exception(self):
  with tempfile.TemporaryDirectory(prefix='entry-transport-mode-test-') as temp:
   root=Path(temp);release=root/'release';release.mkdir(mode=0o700);(release/'p2').mkdir(mode=0o700);runtime=root/'runtime';runtime.mkdir(mode=0o700)
   name='haproxy.readonly.cfg';source=release/name;path=runtime/name
   transport=candidate_readonly_transport((Path(__file__).resolve().parents[1]/'haproxy.readonly.cfg').read_text())
   atomic(source,transport);atomic(path,'old nonsecret routing',0o644)
   desired={path:{'kind':'file','source':str(source),'sha256':digest(source)}}
   primary=ConfigurationTransaction(release/'p2/primary',desired);primary.create(desired);primary.install()
   override=materialize_transport_mode(release,runtime,primary);primary.verify_after(override)
   self.assertEqual(path.stat().st_mode&0o777,0o644);self.assertEqual(source.stat().st_mode&0o777,0o600);self.assertEqual(path.read_bytes(),source.read_bytes())
   path.chmod(0o666)
   with self.assertRaises(ValueError):verify_transport_mode(release,runtime,primary)
   path.chmod(0o644);primary.install(rollback=True);self.assertEqual(path.read_text(),'old nonsecret routing');self.assertEqual(path.stat().st_mode&0o777,0o644)
 def test_transport_refuses_unreviewed_secret_bytes(self):
  with tempfile.TemporaryDirectory(prefix='entry-transport-reject-test-') as temp:
   root=Path(temp);release=root/'release';release.mkdir(mode=0o700);(release/'p2').mkdir(mode=0o700);runtime=root/'runtime';runtime.mkdir(mode=0o700)
   source=release/'haproxy.readonly.cfg';path=runtime/source.name;atomic(source,'password synthetic-only');atomic(path,source.read_bytes())
   desired={path:{'kind':'file','source':str(source),'sha256':digest(source)}};primary=ConfigurationTransaction(release/'p2/primary',desired);primary.create(desired)
   with self.assertRaises(ValueError):materialize_transport_mode(release,runtime,primary)
   self.assertEqual(path.stat().st_mode&0o777,0o600)
 def test_rootless_source_is_host_only_and_other_fields_preserved(self):
  text='allowed_sources = ["10.89.50.0/24", "127.0.0.0/8", "::1/128"]\nauthorities = ["192.168.1.12:5008"]\nlan = true\npeer_on_lan = false\n'
  import tomllib
  before=tomllib.loads(text);after=tomllib.loads(compatible_readonly_source(text));self.assertEqual(after.pop('allowed_sources'),before.pop('allowed_sources')+['192.168.1.12/32']);self.assertEqual(after,before)
  with self.assertRaises(ValueError):compatible_readonly_source(text.replace('10.89.50.0/24','0.0.0.0/0'))
 def test_source_and_compose_corrections_chain_without_losing_guard(self):
  with tempfile.TemporaryDirectory(prefix='entry-source-chain-test-') as temp:
   root=Path(temp);release=root/'release';release.mkdir(mode=0o700);(release/'p2').mkdir(mode=0o700);runtime=root/'runtime';runtime.mkdir(mode=0o700)
   entry=runtime/'readonly-entry.toml';control=runtime/'native-nuc-control.json'
   text='allowed_sources = ["10.89.50.0/24", "127.0.0.0/8", "::1/128"]\nauthorities = ["192.168.1.12:5008"]\nlan = true\n'
   atomic(release/entry.name,text);atomic(release/'application-compose.json',json.dumps({'services':{'readonly-gateway':{'extra_hosts':{'host.containers.internal':'host-gateway'}}}}))
   atomic(release/control.name,json.dumps({'files':{str(runtime/'application-compose.json'):digest(release/'application-compose.json'),str(entry):digest(release/entry.name)}}))
   desired={runtime/n:{'kind':'file','source':str(release/n),'sha256':digest(release/n)} for n in ['application-compose.json',control.name,entry.name]}
   for path in desired:atomic(path,'old')
   primary=ConfigurationTransaction(release/'p2/primary',desired);primary.create(desired);primary.install()
   with patch('application_entry_provider.source_paths',return_value=[entry,control]):
    materialize(release,runtime,primary);overrides=materialize_source(release,runtime,primary);primary.verify_after(overrides)
    self.assertEqual(entry.stat().st_mode&0o777,0o600);self.assertIn('192.168.1.12/32',entry.read_text())
    hashes=json.loads(control.read_text())['files'];self.assertEqual(hashes[str(entry)],digest(entry));self.assertEqual(hashes[str(runtime/'application-compose.json')],digest(runtime/'application-compose.json'))
    source=release/'p2/source-input/readonly-entry.toml';atomic(source,source.read_text().replace('192.168.1.12/32','192.168.1.0/24'))
    correction=ConfigurationTransaction(release/'p2/source-transaction',{entry,control});journal=correction.load();journal['records'][str(entry)]['after']['sha256']=digest(source);correction.save(journal);correction.install()
    with self.assertRaises(ValueError):verify(release,runtime,primary)
 def test_startup_compatibility_keeps_secret_permissions(self):
  import application_entry_startup as compat
  with tempfile.TemporaryDirectory(prefix='entry-startup-mode-test-') as temp:
   path=Path(temp)/'haproxy.readonly.cfg';other=Path(temp)/'basic.entries'
   with patch.object(compat,'TRANSPORT_PATH',path):
    atomic(path,compat.KNOWN_TRANSPORTS[1],0o644);self.assertEqual(compat.runtime_file(path),path)
    atomic(path,'synthetic secret bytes',0o644)
    with self.assertRaises(ValueError):compat.runtime_file(path)
    atomic(other,'synthetic secret bytes',0o644)
    with self.assertRaises(ValueError):compat.runtime_file(other)
    path.chmod(0o600);self.assertIsNone(compat.runtime_file(path))
if __name__=='__main__':unittest.main()
