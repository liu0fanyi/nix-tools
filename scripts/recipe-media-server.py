#!/usr/bin/env python3
"""Loopback-only media picker; writable overlays never mutate accepted publications."""
from pathlib import Path
import os,hashlib,importlib.util,json,math,re,subprocess,threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,unquote
from jsonschema.exceptions import ValidationError
s=importlib.util.spec_from_file_location('media_flow',Path(__file__).with_name('recipe-flow.py'));flow=importlib.util.module_from_spec(s);s.loader.exec_module(flow)

class Store:
 def __init__(self,root):self.root=flow.safe(root,root);self.library=self.root/'library';self.lock=threading.Lock()
 def context(self,key):
  if not re.fullmatch(r'[A-Za-z0-9_-]+',key):raise ValueError('invalid recipe key')
  folder=flow.safe(self.library/'recipes'/key,self.library)
  recipe=flow.batch.load(folder/'recipe.internal.json')
  if flow.batch.load(folder/'processing.json').get('media_mode')!='clips':raise ValueError('this recipe does not use step clips')
  manifest=flow.batch.library_module().clips_module().validate(folder,recipe)
  binding={'recipe_sha256':flow.batch.digest(folder/'recipe.internal.json'),'clips_sha256':flow.batch.digest(folder/'step-clips.json')}
  return folder,recipe,manifest,binding
 def path(self,key):return flow.safe(self.root/'user-media'/key,self.root)
 def get(self,key):
  folder,recipe,manifest,binding=self.context(key);path=self.path(key)/'selections.json'
  if path.exists():
   state=flow.batch.load(path)
   if any(state[k]!=v for k,v in binding.items()):raise ValueError('saved selections belong to another recipe revision')
   self.validate(state,recipe,manifest,binding)
  else:state={'version':'1.0.0',**binding,'steps':{s['id']:{'mode':'video','frames':[]} for s in recipe['steps']}}
  return state
 def validate(self,state,recipe,manifest,binding):
  if not isinstance(state,dict) or set(state)!={'version','recipe_sha256','clips_sha256','steps'} or state['version']!='1.0.0' or any(state.get(k)!=v for k,v in binding.items()):raise ValueError('invalid or stale selection binding')
  if not isinstance(state['steps'],dict) or set(state['steps'])!={s['id'] for s in recipe['steps']}:raise ValueError('selection must cover exactly this recipe steps')
  clips={c['id']:c for c in manifest['clips']}
  for sid,step in state['steps'].items():
   if not isinstance(step,dict) or set(step)!={'mode','frames'} or step['mode'] not in ('video','images','both') or not isinstance(step['frames'],list) or len(step['frames'])>32:raise ValueError('invalid display mode/frames')
   if step['mode']=='images' and not step['frames']:raise ValueError('select at least one image before choosing images only')
   seen=set()
   for frame in step['frames']:
    if not isinstance(frame,dict) or set(frame)!={'clip_id','time'}:raise ValueError('invalid frame selection')
    c=clips.get(frame['clip_id']);t=frame['time']
    if c is None or c['step_id']!=sid or type(t) not in (int,float) or not math.isfinite(t) or abs(t-round(t,3))>1e-9 or not 0<=t<min(c['duration_seconds'],c['end']-c['start']):raise ValueError('frame outside step clip')
    k=(frame['clip_id'],t)
    if k in seen:raise ValueError('duplicate frame selection')
    seen.add(k)
 def image_name(self,frame):return hashlib.sha256((frame['clip_id']+':'+format(frame['time'],'.3f')).encode()).hexdigest()+'.jpg'
 def put(self,key,state):
  with self.lock:
   folder,recipe,manifest,binding=self.context(key);self.validate(state,recipe,manifest,binding);clips={c['id']:c for c in manifest['clips']};target=self.path(key);flow.durable_mkdir(target)
   for step in state['steps'].values():
    for frame in step['frames']:
     destination=flow.safe(target/self.image_name(frame),target)
     if destination.exists():continue
     c=clips[frame['clip_id']]
     import tempfile
     with tempfile.TemporaryDirectory(prefix='.frame-',dir=target) as tmp:
      image=Path(tmp)/'frame.jpg'
      subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',str(frame['time']),'-i',str(flow.safe(folder/c['file'],folder/'clips')),'-frames:v','1','-q:v','2','-y',str(image)],check=True,timeout=60)
      if not image.is_file():raise ValueError('no decodable image at this time; choose an earlier frame')
      image.chmod(0o644)
      with image.open('rb') as stream: os.fsync(stream.fileno())
      image.replace(destination);flow.sync_dir(target)
   flow.atomic(target/'selections.json',state);return state

def handler(store):
 class Handler(SimpleHTTPRequestHandler):
  def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(store.library),**kwargs)
  def allowed(self,write=False):
   port=self.server.server_address[1];host=self.headers.get('Host');allowed={f'127.0.0.1:{port}',f'localhost:{port}'}
   if host not in allowed or self.headers.get('Sec-Fetch-Site')=='cross-site':raise ValueError('only same-origin loopback requests are allowed')
   if write and self.headers.get('Origin')!='http://'+host:raise ValueError('cross-origin write rejected')
  def send_json(self,value,status=200):
   raw=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def api_key(self):
   match=re.fullmatch(r'/api/recipes/([A-Za-z0-9_-]+)/media',urlparse(self.path).path);return match[1] if match else None
  def do_GET(self):
   try:
    self.allowed();path=urlparse(self.path).path;key=self.api_key()
    if key:return self.send_json(store.get(key))
    page=re.fullmatch(r'/recipes/([A-Za-z0-9_-]+)/recipe.html',path)
    if page:
     file=flow.safe(store.library/'recipes'/page[1]/'recipe.html',store.library)
     if flow.batch.load(file.parent/'processing.json').get('media_mode')=='clips':
      state=store.get(page[1]);payload=json.dumps(state,ensure_ascii=False).replace('<','\\u003c')
      text=file.read_text().replace('<head>','<head><script>window.__recipeMediaState='+payload+';</script>',1)
      script=Path(__file__).with_name('recipe-media-picker.js').read_text();text=re.sub(r'<script>/\* Local clips.*?</script>',lambda match:'<script>'+script+'</script>',text,flags=re.S);raw=text.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
    selected=re.fullmatch(r'/api/recipes/([A-Za-z0-9_-]+)/frames/(clip_[0-9a-f]{20})/([0-9]+(?:\.[0-9]{1,3})?)\.jpg',path)
    if selected:
     state=store.get(selected[1]);frame=next((f for step in state['steps'].values() for f in step['frames'] if f['clip_id']==selected[2] and f['time']==float(selected[3])),None)
     if frame is None:raise ValueError('frame is not selected')
     image=flow.safe(store.path(selected[1])/store.image_name(frame),store.root);raw=image.read_bytes();self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
    match=re.fullmatch(r'/api/recipes/([A-Za-z0-9_-]+)/images/([0-9a-f]{64}\.jpg)',path)
    if match:
     state=store.get(match[1]);names={store.image_name(f) for s in state['steps'].values() for f in s['frames']}
     if match[2] not in names:raise ValueError('image is not selected')
     image=flow.safe(store.path(match[1])/match[2],store.root);raw=image.read_bytes();self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
    flow.safe(store.library/unquote(path).lstrip('/'),store.library);super().do_GET()
   except (ValueError,KeyError,OSError,ValidationError) as exc:self.send_json({'error':str(exc)},400)
  def do_PUT(self):
   try:
    self.allowed(True);key=self.api_key()
    if key is None:raise ValueError('unknown write endpoint')
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=1024*1024:raise ValueError('selection body too large/empty')
    state=json.loads(self.rfile.read(size));self.send_json(store.put(key,state))
   except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError,ValidationError) as exc:self.send_json({'error':str(exc)},400)
  def do_HEAD(self):
   try:
    self.allowed();flow.safe(store.library/unquote(urlparse(self.path).path).lstrip('/'),store.library);super().do_HEAD()
   except (ValueError,OSError) as exc:self.send_json({'error':str(exc)},400)
  def do_POST(self):self.send_json({'error':'only the selection PUT endpoint permits writes'},405)
 return Handler

def serve(root,port=8765):
 if not 1<=port<=65535:raise ValueError('invalid port')
 store=Store(root);server=ThreadingHTTPServer(('127.0.0.1',port),handler(store));print(f'菜谱目录：http://127.0.0.1:{port}/index.html（Ctrl+C 停止）',flush=True)
 try:server.serve_forever()
 finally:server.server_close()
