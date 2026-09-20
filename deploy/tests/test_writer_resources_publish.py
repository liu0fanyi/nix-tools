import base64,importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]/'scripts/publish-writer-resources.py'
s=importlib.util.spec_from_file_location('publisher',SOURCE);p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
class ResourcePublish(unittest.TestCase):
 def test_transaction_boundaries(self):
  with tempfile.TemporaryDirectory() as d:
   code=p.REMOTE.replace('/root/nix-tools/dufs_data/releases/focus-writer/resources',d+'/resources')
   def call(r,ok=True):
    out=subprocess.run(['python3','-c',code],input=json.dumps(r),text=True,capture_output=True)
    self.assertEqual(out.returncode==0,ok,out.stderr)
    return json.loads(out.stdout) if ok else None
   data=b'public test resource';name='v2/'+p.digest(data)+'.wrp'
   manifest=json.dumps({'protocol':2,'resource_version':5,'sha256':p.digest(data),'size':len(data)}).encode()
   def item(b):return {'data':base64.b64encode(b).decode(),'sha256':p.digest(b),'previous':None}
   assets={'op':'assets','files':{name:item(data)}}
   pointer={'op':'activate','files':{'v2/manifest.json':item(manifest)}}
   call(pointer,False);call(assets);call(assets);call(pointer);call(pointer,False)
   call({'op':'assets','files':{name:item(b'conflict')}},False)
   call({'op':'inspect','paths':['../other-product']},False)
   link=Path(d)/'resources/v1';link.symlink_to(Path(d));call({'op':'inspect','paths':['v1/manifest.json']},False)
   self.assertEqual(call({'op':'inspect','paths':[name]})[name],p.digest(data))
if __name__=='__main__':unittest.main()
