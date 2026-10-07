/* Local clips and persistent manual frame selection. No vision model. */
(async function () {
 'use strict';
 const status=document.getElementById('media-status'), sections=[...document.querySelectorAll('.step-media')];
 if(!sections.length)return;
 const message=text=>{status.textContent=text;};
 const key=decodeURIComponent(location.pathname.split('/').slice(-2)[0]);
 const endpoint='/api/recipes/'+encodeURIComponent(key)+'/media';
 let state=globalThis.__recipeMediaState, busy=false;
 async function request(method,body){
  const response=await fetch(endpoint,{method,headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});
  const result=await response.json();if(!response.ok)throw new Error(result.error||'保存失败');return result;
 }
 function draw(){
  for(const section of sections){
   const value=state.steps[section.dataset.stepId], select=section.querySelector('.media-mode');select.value=value.mode;
   section.querySelector('.videos').hidden=value.mode==='images';
   const gallery=section.querySelector('.picked-images');gallery.hidden=value.mode==='video';gallery.replaceChildren();
   for(const [index,frame] of value.frames.entries()){
    const figure=document.createElement('figure'), image=document.createElement('img'),caption=document.createElement('figcaption'),remove=document.createElement('button');
    image.alt='手动选取的步骤画面';
    image.src='/api/recipes/'+encodeURIComponent(key)+'/frames/'+frame.clip_id+'/'+frame.time.toFixed(3)+'.jpg';
    const video=section.querySelector('video[data-clip-id="'+frame.clip_id+'"]');
    caption.textContent='手选画面 · 原视频 '+(Number(video.dataset.sourceStart)+frame.time).toFixed(2)+' 秒';remove.textContent='移除这张';remove.type='button';
    remove.onclick=()=>save(next=>{const step=next.steps[section.dataset.stepId];step.frames.splice(index,1);if(!step.frames.length&&step.mode==='images')step.mode='video';});
    figure.append(image,caption,remove);gallery.append(figure);
   }
   section.querySelector('.media-message').textContent=value.frames.length?'已保存 '+value.frames.length+' 张；可切换展示方式。':'未选图片，保留视频片段。';
  }
 }
 async function save(change){
  if(busy)return;busy=true;
  const next=structuredClone(state);change(next);message('正在保存…');
  try{state=await request('PUT',next);draw();message('已保存到本机，重新打开仍会保留。');}
  catch(error){draw();message(error.message);}
  finally{busy=false;}
 }
 if(location.protocol==='file:'){
  message('视频可直接播放。若要选图并保存，请通过本地菜谱服务打开此页面。');
  document.querySelectorAll('.capture,.media-mode,#export-media,#import-media').forEach(x=>x.disabled=true);return;
 }
 try{state=state||await request('GET');draw();message('选图记录已加载；未选图的步骤保留视频。');}
 catch(error){message('无法加载选图服务：'+error.message);document.querySelectorAll('.capture,.media-mode,#export-media,#import-media').forEach(x=>x.disabled=true);return;}
 for(const section of sections){
  section.querySelector('.media-mode').onchange=event=>save(next=>{next.steps[section.dataset.stepId].mode=event.target.value;});
  for(const player of section.querySelectorAll('.clip-player'))player.querySelector('.capture').onclick=()=>{
   const video=player.querySelector('video');
   if(video.readyState<2){message('先播放或拖动到想选的画面。');return;}
   video.pause();const frame={clip_id:video.dataset.clipId,time:Math.round(video.currentTime*1000)/1000};
   save(next=>{const step=next.steps[section.dataset.stepId];if(!step.frames.some(f=>f.clip_id===frame.clip_id&&f.time===frame.time))step.frames.push(frame);if(step.mode==='video')step.mode='both';});
  };
 }
 document.getElementById('export-media').onclick=()=>{
  const url=URL.createObjectURL(new Blob([JSON.stringify(state,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=key+'-选图.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
 document.getElementById('import-media').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  try{if(file.size>1024*1024)throw new Error('记录文件过大');const incoming=JSON.parse(await file.text());await save(next=>{for(const k of Object.keys(next))delete next[k];Object.assign(next,incoming);});}
  catch(error){message('导入失败：'+error.message);}event.target.value='';
 };
})();
