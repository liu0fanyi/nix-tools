from pathlib import Path
import argparse,json,threading,subprocess,time,shutil,base64,io
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from PIL import Image,ImageChops,ImageStat
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();root=args.output.absolute();root.mkdir(parents=True,exist_ok=False)
profile=root/'profile';profile.mkdir();(profile/'user.js').write_text('user_pref("media.autoplay.default",0);user_pref("media.autoplay.blocking_policy",0);')
fixtures={}
for kind,rate,select,flags in [('cfr',25,None,''),('offset',25,None,''),('vfr',30,"select='if(lt(n,45),not(mod(n,2)),not(mod(n,3)))'",''),('signed',30,"select='if(lt(n,45),not(mod(n,2)),not(mod(n,3)))'",'+negative_cts_offsets')]:
 command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'testsrc2=size=320x180:rate={rate}:duration=4']
 if select:command+=['-vf',select,'-fps_mode','vfr']
 command+=['-an','-c:v','libx264','-g','20','-pix_fmt','yuv420p','-movflags','empty_moov+frag_keyframe+default_base_moof'+flags,str(root/(kind+'.mp4'))];subprocess.run(command,check=True)
 reference=root/(kind+'-reference');reference.mkdir();subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(root/(kind+'.mp4')),'-fps_mode','passthrough',str(reference/'%04d.png')],check=True)
 script="const {FrameIndex}=require(process.argv[1]),fs=require('fs');let i=new FrameIndex();i.push(fs.readFileSync(process.argv[2]));console.log(JSON.stringify(i.groups().flatMap(g=>g.frames)));"
 frames=json.loads(subprocess.check_output(['node','-e',script,str(Path(__file__).resolve().parents[1]/'bilibili-recipe-controls.user.js'),str(root/(kind+'.mp4'))],text=True));
 if kind=='offset':
  for frame in frames:frame['pts']+=1.25
 fixtures[kind]=frames
(root/'fixtures.json').write_text(json.dumps(fixtures));shutil.copyfile(str(Path(__file__).resolve().parents[1]/'bilibili-recipe-controls.user.js'),root/'controls.js')
(root/'index.html').write_text('''<head><meta charset="utf-8"><script src="controls.js"></script></head><body><video muted style="width:640px;height:360px"></video><script>
const video=document.querySelector('video'),delay=ms=>new Promise(r=>setTimeout(r,ms));
let lastPresentation=null;function observe(){video.requestVideoFrameCallback((_,m)=>{lastPresentation={pts:m.mediaTime,time:video.currentTime,paused:video.paused};observe();})}observe();
const key=code=>window.dispatchEvent(new KeyboardEvent('keydown',{code,bubbles:true,cancelable:true}));
const shot=()=>{const c=document.createElement('canvas');c.width=video.videoWidth;c.height=video.videoHeight;c.getContext('2d').drawImage(video,0,0);return c.toDataURL('image/png')};
async function seek(t){await new Promise(r=>{video.addEventListener('seeked',r,{once:true});video.currentTime=t});await delay(100)}
async function step(code){key(code);for(let i=0;i<150;i++){await delay(20);let s=document.querySelector('[data-status]').textContent;if(s.startsWith('上一帧 ·')||s.startsWith('下一帧 ·'))return s;if(s.startsWith('逐帧失败'))throw Error(s)}throw Error('step timeout: '+document.querySelector('[data-status]').textContent)}
(async()=>{const results={};try{const fixtures=await fetch('fixtures.json').then(r=>r.json());
for(const [kind,frames]of Object.entries(fixtures)){
 const ms=new MediaSource();video.src=URL.createObjectURL(ms);await new Promise(r=>ms.addEventListener('sourceopen',r,{once:true}));
 const sb=ms.addSourceBuffer('video/mp4; codecs="avc1.64001E"');if(kind==='offset')sb.timestampOffset=1.25;const data=await fetch(kind+'.mp4').then(r=>r.arrayBuffer());
 await new Promise((resolve,reject)=>{sb.addEventListener('updateend',resolve,{once:true});sb.addEventListener('error',()=>reject(Error('append failed')),{once:true});sb.appendBuffer(data)});ms.endOfStream();
 await delay(150);const shots=[];results[kind]={shots,buffered:[video.buffered.start(0),video.buffered.end(0)]};
 for(const n of [8,18,21,28]){
  const t=(frames[n].pts+frames[n+1].pts)/2;await seek(t);shots.push({expected:n,png:shot(),label:'seek'});
  const forward=await step('ArrowRight');shots.push({expected:n+1,png:shot(),label:forward,currentTime:video.currentTime});
  const backward=await step('ArrowLeft');shots.push({expected:n,png:shot(),label:backward,currentTime:video.currentTime});
 }
 const selector=document.querySelector('select');selector.value='2';selector.dispatchEvent(new Event('change'));key('Space');await delay(137);window.dispatchEvent(new KeyboardEvent('keyup',{code:'Space',bubbles:true,cancelable:true}));await delay(100);
 shots.push({expected:'held-origin',png:shot(),label:'held-paused',currentTime:video.currentTime,presentation:lastPresentation});
 const heldForward=await step('ArrowRight');shots.push({expected:'held-next',png:shot(),label:heldForward,currentTime:video.currentTime,presentation:lastPresentation});
 const heldBack=await step('ArrowLeft');shots.push({expected:'held-back',png:shot(),label:heldBack,currentTime:video.currentTime,presentation:lastPresentation});
 results[kind]={shots,buffered:[video.buffered.start(0),video.buffered.end(0)]};
 video.removeAttribute('src');video.load();
} }catch(error){results.error=error.message}await fetch('/result',{method:'POST',body:JSON.stringify(results)});})();
</script>''')
result={};event=threading.Event()
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(root),**kwargs)
 def log_message(self,*args):pass
 def do_POST(self):
  result.update(json.loads(self.rfile.read(int(self.headers['Content-Length']))));self.send_response(200);self.end_headers();event.set()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
with (root/'zen.log').open('w') as log:
 process=subprocess.Popen(['zen','--headless','--no-remote','--profile',str(profile),'http://127.0.0.1:'+str(server.server_port)+'/index.html'],stdout=log,stderr=log)
 try:
  if not event.wait(50):raise RuntimeError('No browser report')
  (root/'raw-result.json').write_text(json.dumps(result));
  if result.get('error'):raise RuntimeError(result['error'])
  report={}
  for kind,value in result.items():
   references=[Image.open(p).convert('RGB') for p in sorted((root/(kind+'-reference')).glob('*.png'))];checks=[]
   origin=None
   for n,shot in enumerate(value['shots']):
    png=base64.b64decode(shot.pop('png').split(',',1)[1]);(root/f'{kind}-shot-{n}.png').write_bytes(png);actual=Image.open(io.BytesIO(png)).convert('RGB')
    errors=[sum(ImageStat.Stat(ImageChops.difference(actual,r)).mean)/3 for r in references];winner=min(range(len(errors)),key=errors.__getitem__)
    if shot['expected']=='held-origin':origin=winner;shot['expected']=winner
    elif shot['expected']=='held-next':shot['expected']=origin+1
    elif shot['expected']=='held-back':shot['expected']=origin
    runnerup=min(error for index,error in enumerate(errors) if index!=winner)
    checks.append({**shot,'actual_decoded_frame':winner,'mean_rgb_error':round(errors[winner],4),'runnerup_gap':round(runnerup-errors[winner],4),'pass':winner==shot['expected'] and runnerup-errors[winner]>0.0001})
   report[kind]={'buffered':value['buffered'],'checks':checks}
  (root/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({kind:{'checks':len(value['checks']),'passed':sum(s['pass'] for s in value['checks']),'min_runnerup_gap':min(s['runnerup_gap'] for s in value['checks'])} for kind,value in report.items()},indent=2))
  assert all(s['pass'] for r in report.values() for s in r['checks']), 'Wrong displayed frame'
 finally:process.terminate();process.wait(timeout=10);server.shutdown()
