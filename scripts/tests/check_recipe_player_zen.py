from pathlib import Path
import argparse,json,threading,subprocess,time,shutil
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();root=args.output.absolute();root.mkdir(parents=True,exist_ok=True);
if list(root.glob('bilibili-*.png')):raise ValueError('Use a fresh output directory; old screenshot found')
profile=root/'profile';profile.mkdir(exist_ok=True)
(profile/'user.js').write_text('user_pref("media.autoplay.default",0);\nuser_pref("media.autoplay.blocking_policy",0);\nuser_pref("browser.download.folderList",2);\nuser_pref("browser.download.dir",'+json.dumps(str(root))+');\nuser_pref("browser.download.useDownloadDir",true);\nuser_pref("browser.download.alwaysOpenPanel",false);\n')
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=25:duration=8','-an','-c:v','libx264','-pix_fmt','yuv420p',str(root/'test.mp4')],check=True)
shutil.copyfile(str(Path(__file__).resolve().parents[1]/'bilibili-recipe-controls.user.js'),root/'controls.js')
(root/'index.html').write_text('''<head><meta charset="utf-8"><script src="controls.js"></script></head><body><video src="test.mp4" muted style="width:640px;height:360px"></video><textarea></textarea><script>
const delay=ms=>new Promise(r=>setTimeout(r,ms)),video=document.querySelector('video');
const down=(code,target=window)=>target.dispatchEvent(new KeyboardEvent('keydown',{code,bubbles:true,cancelable:true}));
const up=code=>window.dispatchEvent(new KeyboardEvent('keyup',{code,bubbles:true,cancelable:true}));
(async()=>{const checks={};try{
 await new Promise((resolve,reject)=>{if(video.readyState>=2)return resolve();video.addEventListener('loadeddata',resolve,{once:true});setTimeout(()=>reject(Error('load timeout')),8000)});
 await delay(150);checks.defaultPaused=video.paused;checks.nativeNext=typeof video.seekToNextFrame;
 const start=video.currentTime;down('Space');await delay(600);checks.holdAdvances=video.currentTime>start+0.3;up('Space');await delay(100);const stopped=video.currentTime;await delay(400);checks.releasePauses=video.paused && Math.abs(video.currentTime-stopped)<0.02;
 const selector=document.querySelector('select');selector.value='0.25';selector.dispatchEvent(new Event('change'));const before=video.currentTime;down('Space');await delay(800);up('Space');const advance=video.currentTime-before;checks.quarterSpeed=video.playbackRate===0.25&&advance>0.08&&advance<0.4;
 down('Space');await delay(150);window.dispatchEvent(new Event('blur'));await delay(50);checks.blurPauses=video.paused;
 const textbox=document.querySelector('textarea');textbox.focus();down('Space',textbox);await delay(100);checks.inputIgnored=video.paused;up('Space');textbox.blur();
 const prior=video.currentTime;down('ArrowRight');await delay(100);checks.noFakeNext=checks.nativeNext!=='undefined'||Math.abs(video.currentTime-prior)<0.02;
 down('ArrowLeft');await delay(100);checks.noFakePrevious=Math.abs(video.currentTime-prior)<0.02;
 down('KeyS');await delay(300);checks.screenshotRequested=document.querySelector('[data-status]').textContent.includes('已请求');
 const toggle=document.querySelector('input');toggle.checked=false;toggle.dispatchEvent(new Event('change'));await video.play();window.dispatchEvent(new Event('blur'));await delay(100);checks.disabledLeavesNative= !video.paused;video.pause();
 toggle.checked=true;toggle.dispatchEvent(new Event('change'));
 const cross=new URL('test.mp4',location.href);cross.hostname='localhost';video.src=cross.href;
 await new Promise((resolve,reject)=>{video.addEventListener('loadeddata',resolve,{once:true});setTimeout(()=>reject(Error('cross-origin video timeout')),8000)});
 await delay(150);down('KeyS');await delay(300);checks.corsFailureReported=document.querySelector('[data-status]').textContent.includes('跨域策略禁止截图');
 }catch(error){checks.error=error.message}await fetch('/result',{method:'POST',body:JSON.stringify(checks)});})();
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
  if not event.wait(30):raise RuntimeError('No browser report; see '+str(root/'zen.log'))
  time.sleep(1);result['pngSaved']=bool(list(root.glob('bilibili-*.png')));print(json.dumps(result,indent=2));(root/'report.json').write_text(json.dumps(result,indent=2))
  if any(value is not True for key,value in result.items() if key!='nativeNext'):raise RuntimeError('browser check failed')
 finally:
  process.terminate();process.wait(timeout=10);server.shutdown()
