import importlib.util,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
spec=importlib.util.spec_from_file_location('entryprep',str(Path(__file__).resolve().parents[2]/'scripts/prepare-application-entry.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Prepare(unittest.TestCase):
 def test_runtime_relative_only(self):
  value=m.normalize({'services':{'a':{'volumes':['./haproxy.readonly.cfg:/cfg:ro']}}})
  self.assertEqual(value['services']['a']['volumes'][0]['source'],m.RUNTIME+'/haproxy.readonly.cfg')
  self.assertTrue(value['services']['a']['volumes'][0]['read_only'])
 def test_escape_named_volume_and_unknown_policy_refused(self):
  for value in ['../outside:/cfg:ro','named-volume:/cfg','./../outside:/cfg:ro','/tmp/owned:/cfg:Z']:
   with self.subTest(value=value),self.assertRaises(ValueError):m.normalize({'services':{'a':{'volumes':[value]}}})
 def test_unknown_ports_refused(self):
  for value in ['5006:5006','127.0.0.1:5006:5006','0.0.0.0:abc:5006']:
   with self.assertRaises(ValueError):m.normalize({'services':{'a':{'ports':[value]}}})
if __name__=='__main__':unittest.main()
