#!/usr/bin/env python3
"""Generated screenshot script with own slurp/grim/editor mocks; no desktop capture."""
import base64,hashlib,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
script=Path(sys.argv[1]);body='\n'.join(line for line in script.read_text().splitlines() if not line.startswith('export PATH='))+'\n'
with tempfile.TemporaryDirectory(prefix='screenshot-workflow-')as directory:
 root=Path(directory);runtime=root/'runtime';runtime.mkdir(mode=0o700);bin_dir=root/'bin';bin_dir.mkdir();test=root/'workflow';test.write_text(body);test.chmod(0o755);source=root/'source.png';source.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZAAAAABJRU5ErkJggg=='));digest=hashlib.sha256(source.read_bytes()).hexdigest();calls=root/'calls.jsonl'
 programs={
 'slurp':'''import os,sys
mode=os.environ['CASE']
if mode=='cancel':sys.exit(1)
if mode!='empty':print('10,20 100x80')
''',
 'grim':'''import os,sys,shutil
if os.environ['CASE']=='grim-fail':sys.exit(2)
assert sys.argv[1:3]==['-g','10,20 100x80']
shutil.copyfile(os.environ['SYNTHETIC'],sys.argv[3])
''',
 'screen-mark':'''import os,sys,json,time,shutil
from pathlib import Path
image=Path(sys.argv[1]);output=Path(sys.argv[3]);assert sys.argv[2]=='--output';assert image.exists();assert output.is_relative_to(Path(os.environ['HOME'])/'Pictures/Screenshots')
with open(os.environ['CALLS'],'a')as stream:stream.write(json.dumps({'image':str(image),'output':str(output)})+'\\n')
if os.environ['CASE']=='busy':time.sleep(1)
if os.environ['CASE']=='editor-fail':sys.exit(7)
shutil.copyfile(image,output)
'''}
 for name,code in programs.items():p=bin_dir/name;p.write_text('#!'+sys.executable+'\n'+code);p.chmod(0o755)
 env={**os.environ,'HOME':directory,'XDG_RUNTIME_DIR':str(runtime),'TMPDIR':directory,'PATH':str(bin_dir)+os.pathsep+os.environ['PATH'],'SYNTHETIC':str(source),'CALLS':str(calls)}
 for key in ['WAYLAND_DISPLAY','DISPLAY','SWAYSOCK']:env.pop(key,None)
 for case in ['cancel','empty','grim-fail','success','editor-fail']:
  calls.unlink(missing_ok=True);result=subprocess.run([str(test)],env={**env,'CASE':case},capture_output=True,timeout=10)
  records=[json.loads(l)for l in calls.read_text().splitlines()]if calls.exists()else[]
  assert len(records)==(1 if case in ['success','editor-fail']else 0),(case,result.stderr,records)
  assert result.returncode==({'grim-fail':2,'editor-fail':7}.get(case,0)),(case,result.returncode)
  for record in records:assert not Path(record['image']).exists();assert Path(record['output']).exists()==(case=='success')
  assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
 calls.unlink(missing_ok=True);first=subprocess.Popen([str(test)],env={**env,'CASE':'busy'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 for _ in range(100):
  if calls.exists():break
  time.sleep(.02)
 assert calls.exists();second=subprocess.run([str(test)],env={**env,'CASE':'busy'},capture_output=True,timeout=5);first.wait(timeout=5);assert second.returncode==0 and len(calls.read_text().splitlines())==1
 assert not Path(json.loads(calls.read_text().splitlines()[0])['image']).exists()
 print('PASS 6 isolated screenshot workflows: cancel/empty/capture error/success/editor error/concurrent lock; original unchanged and temporary inputs cleaned')
