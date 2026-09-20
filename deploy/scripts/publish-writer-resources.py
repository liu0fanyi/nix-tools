#!/usr/bin/env python3
"""Publish validated Focus Writer resources only. Preview by default, no deletion."""
import argparse, base64, hashlib, json, re, shlex, subprocess, urllib.request
from pathlib import Path
HOST='root@47.93.153.102'
BASE='https://wttliou.top/releases/focus-writer/resources/'
REMOTE=r'''
import base64,fcntl,hashlib,json,os,re,sys,tempfile
from pathlib import Path
ROOT=Path('/root/nix-tools/dufs_data/releases/focus-writer/resources')
def digest(b): return hashlib.sha256(b).hexdigest()
def safe(p):
 assert p==ROOT or ROOT in p.parents
 assert all(not q.is_symlink() for q in [p,*p.parents]), 'symlink rejected'
def allowed(p):
 return re.fullmatch(r'v[12]/(?:[a-f0-9]{64}\.wrp|[1-9][0-9]{0,9}/(?:manifest\.json|OFL\.txt|LICENSE\.txt)|manifest\.json)',p)
def atomic(p,b):
 safe(p);p.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
 fd,n=tempfile.mkstemp(prefix='.publishing-',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f: f.write(b);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),0o644)
  os.replace(n,p)
  fd=os.open(p.parent,os.O_DIRECTORY)
  try: os.fsync(fd)
  finally: os.close(fd)
 finally:
  if os.path.exists(n):os.unlink(n)
r=json.load(sys.stdin);safe(ROOT)
if r['op']=='inspect':
 result={}
 for name in r['paths']:
  assert allowed(name);p=ROOT/name;safe(p)
  result[name]=digest(p.read_bytes()) if p.exists() else None
 print(json.dumps(result))
else:
 assert r['op'] in ('assets','activate');ROOT.mkdir(parents=True,exist_ok=True,mode=0o755)
 lock=ROOT/'.publish.lock';safe(lock)
 with lock.open('a') as f:
  fcntl.flock(f,fcntl.LOCK_EX);items=[]
  for name,item in r['files'].items():
   assert allowed(name);p=ROOT/name;safe(p)
   b=base64.b64decode(item['data'],validate=True)
   assert len(b)<=8*1024*1024 and digest(b)==item['sha256']
   pointer=bool(re.fullmatch('v[12]/manifest.json',name))
   assert pointer==(r['op']=='activate')
   old=p.read_bytes() if p.exists() else None
   if pointer:
    assert (digest(old) if old is not None else None)==item['previous'], 'concurrent manifest change'
    m=json.loads(b);assert m['protocol']==int(name[1])
    if old:assert json.loads(old)['resource_version']<=m['resource_version'], 'downgrade'
    asset=ROOT/name[:3]/(m['sha256']+'.wrp');safe(asset)
    assert asset.stat().st_size==m['size'] and digest(asset.read_bytes())==m['sha256']
   else:assert old is None or old==b, 'immutable conflict'
   items.append((p,b))
  for p,b in items:atomic(p,b)
  print(json.dumps({'written':len(items)}))
'''
def digest(b):return hashlib.sha256(b).hexdigest()
def remote(request):
 r=subprocess.run(['ssh','-o','StrictHostKeyChecking=yes',HOST,'python3 -c '+shlex.quote(REMOTE)],input=json.dumps(request),text=True,capture_output=True,check=True)
 return json.loads(r.stdout)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise RuntimeError('redirect rejected')
def read_public(path,limit):
 with urllib.request.build_opener(NoRedirect()).open(BASE+path,timeout=90) as r:
  b=r.read(limit+1)
  assert len(b)<=limit
  return b

def collect(root):
 result={}
 assert not root.is_symlink()
 for protocol in (1,2):
  p=root/f'v{protocol}/manifest.json';m=json.loads(p.read_bytes())
  assert m['schema']==1 and m['protocol']==protocol
  assert type(m['resource_version']) is int and 0<m['resource_version']<2**31
  assert type(m['size']) is int and 128<=m['size']<=8*1024*1024
  assert re.fullmatch('[a-f0-9]{64}',m['sha256'])
  names=[f'v{protocol}/manifest.json',f'v{protocol}/{m["sha256"]}.wrp']
  names += [f'v{protocol}/{m["resource_version"]}/{n}' for n in ['manifest.json','OFL.txt','LICENSE.txt']]
  for name in names:
   p=root/name;assert all(not q.is_symlink() for q in [p,*p.parents]);result[name]=p.read_bytes()
  raw=result[names[1]]
  assert len(raw)==m['size'] and digest(raw)==m['sha256']
  assert raw[:4]==f'WRP{protocol}'.encode() and digest(raw[128:])==raw[64:96].hex()
  assert result[names[0]]==result[names[2]]
 return result

def publish(root,apply=False):
 files=collect(root);old=remote({'op':'inspect','paths':list(files)})
 for name,data in files.items():
  if not name.endswith('/manifest.json') or name.count('/')!=1:
   assert old[name] in (None,digest(data)), 'immutable conflict: '+name
 print(json.dumps({'destination':BASE,'apply':apply,'files':{n:{'size':len(b),'sha256':digest(b)} for n,b in files.items()}},indent=2))
 if not apply:return
 for pointers,op in [(False,'assets'),(True,'activate')]:
  selected={n:b for n,b in files.items() if (n.count('/')==1 and n.endswith('/manifest.json'))==pointers}
  remote({'op':op,'files':{n:{'data':base64.b64encode(b).decode(),'sha256':digest(b),'previous':old[n]} for n,b in selected.items()}})
  for name,b in selected.items():assert read_public(name,len(b))==b, 'public mismatch: '+name
 print('Public resources and active manifests verified; no old versions deleted.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--staged',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args();publish(a.staged,a.apply)
