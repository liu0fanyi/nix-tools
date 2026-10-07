#!/usr/bin/env python3
"""Local step clips: exact source windows, independent media, no visual AI."""
import hashlib,json,math,subprocess
from pathlib import Path
from jsonschema import Draft202012Validator

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def windows(step,duration,padding,evidence=None):
 # Image-goal windows can be narrow; include every subtitle fact of this step.
 ids={eid for fact in step['facts'] for eid in fact['evidence_ids']}
 spans=list(step['evidence_windows'])+[e['interval'] for e in (evidence or []) if e['id'] in ids and e['kind']=='subtitle']
 expanded=sorted((max(0,w['start']-padding),min(duration,w['end']+padding)) for w in spans);result=[]
 for start,end in expanded:
  if result and start<=result[-1]['end']:result[-1]['end']=max(end,result[-1]['end'])
  else:result.append({'start':start,'end':end})
 return result
def probe(path):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],timeout=60))
def safe(folder,file):
 path=folder/file
 if not file.startswith('clips/') or not path.resolve().is_relative_to((folder/'clips').resolve()) or any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('unsafe clip path')
 return path

def build(video,video_sha,recipe,folder,padding=5,width=960):
 folder=Path(folder);(folder/'clips').mkdir();records=[]
 for step in recipe['steps']:
  for index,w in enumerate(windows(step,recipe['source']['duration_seconds'],padding,recipe['evidence'])):
   cid='clip_'+hashlib.sha256((step['id']+':'+str(index)).encode()).hexdigest()[:20];path=folder/'clips'/(cid+'.mp4');length=w['end']-w['start']
   subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',str(w['start']),'-i',str(video),'-t',str(length),'-map','0:v:0','-map','0:a:0?','-vf',f'scale={width}:-2,setpts=PTS-STARTPTS','-af','asetpts=PTS-STARTPTS','-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-movflags','+faststart','-y',str(path)],check=True,timeout=max(120,length*8))
   p=probe(path);stream=next(x for x in p['streams'] if x['codec_type']=='video')
   records.append({'id':cid,'step_id':step['id'],'window_index':index,**w,'file':'clips/'+path.name,'sha256':digest(path),'duration_seconds':float(p['format']['duration']),'width':stream['width'],'height':stream['height']})
 result={'version':'1.0.0','mode':'clips','source_video_sha256':video_sha,'padding_seconds':padding,'width':width,'clips':records}
 (folder/'step-clips.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');validate(folder,recipe)
 return result

def validate(folder,recipe):
 folder=Path(folder);m=json.loads((folder/'step-clips.json').read_text());Draft202012Validator(json.loads((Path(__file__).resolve().parents[1]/'specs/010-host-configuration/contracts/video-recipe-clips.schema.json').read_text())).validate(m);processing=json.loads((folder/'processing.json').read_text()) if (folder/'processing.json').exists() else None
 if m['version']!='1.0.0' or m['mode']!='clips' or not isinstance(m['padding_seconds'],(float,int)) or not math.isfinite(m['padding_seconds']) or not 0<=m['padding_seconds']<=60:raise ValueError('invalid clip manifest')
 if processing and m['source_video_sha256']!=processing['source_video_sha256']:raise ValueError('clip source mismatch')
 expected={(s['id'],i):w for s in recipe['steps'] for i,w in enumerate(windows(s,recipe['source']['duration_seconds'],m['padding_seconds'],recipe['evidence']))};seen=set();ids=set()
 for c in m['clips']:
  if any(not math.isfinite(c[k]) for k in ('start','end','duration_seconds','width','height')) or c['width']!=m['width']:raise ValueError('invalid numeric clip metadata')
  key=(c['step_id'],c['window_index'])
  if key not in expected or key in seen or c['id'] in ids:raise ValueError('clip coverage/id mismatch')
  seen.add(key);ids.add(c['id']);w=expected[key]
  if any(c[k]!=w[k] for k in ('start','end')):raise ValueError('clip window mismatch')
  path=safe(folder,c['file'])
  if not path.is_file() or digest(path)!=c['sha256']:raise ValueError('clip missing/changed')
  p=probe(path);v=[s for s in p['streams'] if s['codec_type']=='video'];a=[s for s in p['streams'] if s['codec_type']=='audio'];duration=float(p['format']['duration'])
  if len(v)!=1 or v[0]['codec_name']!='h264' or any(s['codec_name']!='aac' for s in a) or v[0]['width']!=c['width'] or v[0]['height']!=c['height'] or not math.isfinite(duration) or duration<=0 or abs(duration-c['duration_seconds'])>.01 or abs(duration-(c['end']-c['start']))>.4:raise ValueError('clip media mismatch')
 if seen!=set(expected):raise ValueError('missing step clip')
 return m
