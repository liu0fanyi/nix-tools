// ==UserScript==
// @name         菜谱原视频键盘浏览（实验版）
// @namespace    nix-tools.recipe
// @version      0.2.0
// @description  按住播放松开停；从正常缓冲分片读取真实帧时间，实现邻帧浏览和截图。
// @match        https://www.bilibili.com/video/*
// @grant        none
// @run-at       document-start
// @inject-into  page
// ==/UserScript==
(() => {
  'use strict';
  // Only moov/moof metadata is retained. mdat payload is skipped without copying.
  class FrameIndex {
    constructor() { this.reset(); }
    reset() { this.tracks=new Map();this.defaults=new Map();this.segments=[];this.header=new Uint8Array();this.box=null;this.error=null;this.revision=(this.revision||0)+1; }
    fail(message) { this.reset();this.error=message; }
    static u64(view,p,signed=false) {
      const n=signed?view.getBigInt64(p):view.getBigUint64(p);
      if (n>BigInt(Number.MAX_SAFE_INTEGER)||n<BigInt(Number.MIN_SAFE_INTEGER)) throw Error('时间值超出安全范围');
      return Number(n);
    }
    static boxes(view,start,end) {
      const result=[];
      for(let p=start;p<end;) {
        if(end-p<8) throw Error('不完整 MP4 box');
        let size=view.getUint32(p),header=8;
        const type=String.fromCharCode(...new Uint8Array(view.buffer,view.byteOffset+p+4,4));
        if(size===1) { if(end-p<16) throw Error('不完整扩展 box');size=FrameIndex.u64(view,p+8);header=16; }
        if(size===0) size=end-p;
        if(size<header||size>end-p) throw Error('无效 MP4 box 长度');
        result.push({type,p:p+header,end:p+size});p+=size;
      }
      return result;
    }
    push(data,options={}) {
      if(this.error) return;
      const context={offset:options.offset??0,mode:options.mode??'segments',start:options.start??0,end:options.end??Infinity};
      if(context.mode!=='segments'||context.start!==0||context.end!==Infinity||!Number.isFinite(context.offset)) throw Error('不支持 sequence／裁剪缓冲时间轴');
      let bytes=ArrayBuffer.isView(data)?new Uint8Array(data.buffer,data.byteOffset,data.byteLength):new Uint8Array(data),p=0;
      while(p<bytes.length) {
        if(!this.box) {
          let need=this.header.length>=8&&new DataView(this.header.buffer).getUint32(0)===1?16:8;
          const count=Math.min(need-this.header.length,bytes.length-p),joined=new Uint8Array(this.header.length+count);
          joined.set(this.header);joined.set(bytes.subarray(p,p+count),this.header.length);this.header=joined;p+=count;
          if(this.header.length<8) continue;
          if(new DataView(this.header.buffer).getUint32(0)===1&&this.header.length<16) continue;
          const view=new DataView(this.header.buffer),size=view.getUint32(0)===1?FrameIndex.u64(view,8):view.getUint32(0),header=this.header.length;
          const type=String.fromCharCode(...this.header.subarray(4,8)),wanted=type==='moov'||type==='moof';
          if(size<header) throw Error('不支持无界或无效 MP4 box');
          if(wanted&&size>2*1024*1024) throw Error('分片索引元数据超过 2 MiB');
          this.box={type,remaining:size-header,parts:[],length:0,wanted,context};this.header=new Uint8Array();
        }
        const b=this.box,count=Math.min(b.remaining,bytes.length-p);
        if(b.context.offset!==context.offset) throw Error('分片中途改变时间偏移');
        if(b.wanted&&count) { b.parts.push(bytes.slice(p,p+count));b.length+=count; }
        b.remaining-=count;p+=count;
        if(b.remaining===0) {
          this.box=null;
          if(b.wanted) {
            const payload=new Uint8Array(b.length);let at=0;for(const part of b.parts){payload.set(part,at);at+=part.length;}
            const view=new DataView(payload.buffer);
            if(b.type==='moov')this.init(view);else this.fragment(view,b.context);
          }
        }
      }
    }
    static need(box,bytes) {if(box.end-box.p<bytes)throw Error('截断 MP4 轨道字段');}
    init(view) {
      const children=FrameIndex.boxes(view,0,view.byteLength),tracks=new Map(),defaults=new Map();
      if(!children.some(b=>b.type==='mvex')) throw Error('不是分片 MP4 初始化段');
      const find=(list,type)=>list.find(b=>b.type===type);
      for(const trak of children.filter(b=>b.type==='trak')) {
        const fields=FrameIndex.boxes(view,trak.p,trak.end),tkhd=find(fields,'tkhd'),mdia=find(fields,'mdia');
        if(!tkhd||!mdia) throw Error('缺少轨道元数据');
        const media=FrameIndex.boxes(view,mdia.p,mdia.end),handler=find(media,'hdlr'),mdhd=find(media,'mdhd');
        if(!handler||!mdhd) throw Error('缺少轨道时间元数据');
        FrameIndex.need(handler,12);FrameIndex.need(mdhd,view.getUint8(mdhd.p)===1?24:16);FrameIndex.need(tkhd,view.getUint8(tkhd.p)===1?24:16);
        const kind=String.fromCharCode(...new Uint8Array(view.buffer,handler.p+8,4));
        if(kind!=='vide')continue;
        const id=view.getUint32(tkhd.p+(view.getUint8(tkhd.p)===1?20:12)),scale=view.getUint32(mdhd.p+(view.getUint8(mdhd.p)===1?20:12));
        if(!scale||tracks.has(id)) throw Error('无效视频轨道');
        let edit=0;const edts=find(fields,'edts');
        if(edts) {
          const elst=find(FrameIndex.boxes(view,edts.p,edts.end),'elst');
          if(elst) {
            FrameIndex.need(elst,8);const version=view.getUint8(elst.p);if(view.getUint32(elst.p+4)!==1||version>1)throw Error('不支持复杂编辑时间表');
            FrameIndex.need(elst,version===1?28:20);const at=elst.p+8;edit=version===1?FrameIndex.u64(view,at+8,true):view.getInt32(at+4);
            const rateAt=at+(version===1?16:8);
            if(edit<0||view.getInt16(rateAt)!==1||view.getInt16(rateAt+2)!==0)throw Error('不支持空编辑或变速编辑时间表');
          }
        }
        tracks.set(id,{scale,edit});
      }
      if(tracks.size!==1) throw Error('需要唯一视频轨道');
      for(const mvex of children.filter(b=>b.type==='mvex')) for(const trex of FrameIndex.boxes(view,mvex.p,mvex.end).filter(b=>b.type==='trex')) {FrameIndex.need(trex,24);defaults.set(view.getUint32(trex.p+4),view.getUint32(trex.p+12));}
      this.tracks=tracks;this.defaults=defaults;this.segments=[];this.revision++;
    }
    fragment(view,context) {
      if(!this.tracks.size)throw Error('未捕获初始化段，请刷新视频页');
      for(const traf of FrameIndex.boxes(view,0,view.byteLength).filter(b=>b.type==='traf')) {
        const fields=FrameIndex.boxes(view,traf.p,traf.end),tfhd=fields.find(b=>b.type==='tfhd'),tfdt=fields.find(b=>b.type==='tfdt');
        if(!tfhd)throw Error('分片缺少轨道声明');
        FrameIndex.need(tfhd,8);const id=view.getUint32(tfhd.p+4),track=this.tracks.get(id);if(!track)continue;
        if(!tfdt)throw Error('分片缺少解码时间');
        const flags=view.getUint32(tfhd.p)&0xffffff;let cursor=tfhd.p+8,duration=this.defaults.get(id)||0;
        if(flags&1)cursor+=8;if(flags&2)cursor+=4;if(flags&8){duration=view.getUint32(cursor);cursor+=4;}
        if(flags&16)cursor+=4;if(flags&32)cursor+=4;if(cursor>tfhd.end)throw Error('截断 tfhd');
        FrameIndex.need(tfdt,view.getUint8(tfdt.p)===1?12:8);const version=view.getUint8(tfdt.p);if(version>1)throw Error('未知 tfdt 版本');
        const start=version===1?FrameIndex.u64(view,tfdt.p+4):view.getUint32(tfdt.p+4);let decode=start;const frames=[];
        for(const trun of fields.filter(b=>b.type==='trun')) {
          FrameIndex.need(trun,8);const v=view.getUint8(trun.p),f=view.getUint32(trun.p)&0xffffff,count=view.getUint32(trun.p+4);let at=trun.p+8;
          if(v>1||count>120000||frames.length+count>120000)throw Error('不支持的分片样本数／版本');
          if(f&1)at+=4;if(f&4)at+=4;
          const fieldsPerSample=((f&0x100)?4:0)+((f&0x200)?4:0)+((f&0x400)?4:0)+((f&0x800)?4:0);
          if(at+count*fieldsPerSample!==trun.end)throw Error('截断或未知样本字段');
          for(let n=0;n<count;n++) {
            const d=f&0x100?view.getUint32(at):duration;if(f&0x100)at+=4;
            if(f&0x200)at+=4;if(f&0x400)at+=4;
            const c=f&0x800?(v===1?view.getInt32(at):view.getUint32(at)):0;if(f&0x800)at+=4;
            if(!d||at>trun.end||!Number.isSafeInteger(decode+d)||!Number.isSafeInteger(decode+c-track.edit))throw Error('无效或截断样本时间');
            frames.push({pts:(decode+c-track.edit)/track.scale+context.offset,duration:d/track.scale});decode+=d;
          }
          if(at!==trun.end)throw Error('未知样本字段');
        }
        if(!frames.length)continue;
        const key=`${id}:${track.scale}:${track.edit}:${context.offset}`;
        this.segments=this.segments.filter(s=>s.key===key&&(s.end<=start||s.start>=decode));
        this.segments.push({key,start,end:decode,frames});this.segments.sort((a,b)=>a.start-b.start);
        let retained=this.segments.reduce((n,s)=>n+s.frames.length,0);
        while(retained>120000&&this.segments.length>1)retained-=this.segments.shift().frames.length;
        this.revision++;
      }
    }
    groups() {
      if(this.cache?.revision===this.revision)return this.cache.groups;
      const groups=[];
      for(const segment of this.segments) {
        let group=groups.at(-1);
        if(!group||group.end!==segment.start||group.key!==segment.key){group={key:segment.key,end:segment.end,frames:[]};groups.push(group);}
        group.end=segment.end;for(const frame of segment.frames)group.frames.push(frame);
      }
      for(const g of groups){g.frames.sort((a,b)=>a.pts-b.pts);for(let n=1;n<g.frames.length;n++)if(g.frames[n].pts<=g.frames[n-1].pts)throw Error('非唯一呈现时间，拒绝逐帧');}
      this.cache={revision:this.revision,groups};return groups;
    }
    locate(time,direction=0) {
      if(this.error)throw Error(this.error);
      for(const group of this.groups()) {
        const frames=group.frames;let low=0,high=frames.length;
        while(low<high){const mid=(low+high)>>1;if(frames[mid].pts<=time+1e-8)low=mid+1;else high=mid;}
        const n=low-1;if(n<0)continue;
        if(n===frames.length-1&&time>=frames[n].pts+frames[n].duration-1e-8)continue;
        const target=n+direction;
        if(target<0||target>=frames.length)throw Error('相邻帧尚未完整缓冲，等待缓冲后重试');
        const frame=frames[target],end=frames[target+1]?.pts??frame.pts+frame.duration;
        if(end<=frame.pts)throw Error('无效呈现区间');
        return {pts:frame.pts,time:(frame.pts+end)/2,start:frame.pts,end,count:frames.length};
      }
      throw Error('当前位置没有完整帧时间表，请先等待原播放器缓冲');
    }
  }
  if(typeof window==='undefined'&&typeof module==='object'&&module.exports){module.exports={FrameIndex};return;}
  if (window.top !== window.self) return;

  const bufferRecords=new WeakMap(),sourceRecords=new WeakMap(),urlSources=new Map();
  let notify=()=>{};
  function recordFor(v) {
    const source=urlSources.get(v.currentSrc||v.src),records=source&&sourceRecords.get(source);
    if(!records)return null;
    const candidates=[...records.values()].filter(r=>r.index.tracks.size||r.index.error);
    return candidates.length===1?candidates[0]:null;
  }
  try {
    if(typeof MediaSource!=='undefined'&&typeof SourceBuffer!=='undefined') {
      const add=MediaSource.prototype.addSourceBuffer;
      MediaSource.prototype.addSourceBuffer=function(...args) {
        const sb=Reflect.apply(add,this,args);
        if(/^video\/mp4(?:;|$)/i.test(args[0])) {
          const record={index:new FrameIndex(),ready:true,sb};
          let records=sourceRecords.get(this);if(!records){records=new Map();sourceRecords.set(this,records);}records.set(sb,record);bufferRecords.set(sb,record);
          sb.addEventListener('updateend',()=>{record.ready=true;notify();});
          sb.addEventListener('error',()=>{record.index.fail('播放器缓冲失败，帧索引已停用');notify();});
          sb.addEventListener('abort',()=>{record.index.header=new Uint8Array();record.index.box=null;record.index.segments=[];record.index.revision++;record.ready=true;notify();});
        }
        return sb;
      };
      const remove=MediaSource.prototype.removeSourceBuffer;
      MediaSource.prototype.removeSourceBuffer=function(...args) {const value=Reflect.apply(remove,this,args);sourceRecords.get(this)?.delete(args[0]);bufferRecords.delete(args[0]);notify();return value;};
      const append=SourceBuffer.prototype.appendBuffer;
      SourceBuffer.prototype.appendBuffer=function(...args) {
        const value=Reflect.apply(append,this,args),record=bufferRecords.get(this);
        if(record) {
          record.ready=false;
          try{record.index.push(args[0],{offset:this.timestampOffset,mode:this.mode,start:this.appendWindowStart,end:this.appendWindowEnd});}
          catch(error){record.index.fail(error.message);}
        }
        return value;
      };
      if(SourceBuffer.prototype.changeType) {
        const change=SourceBuffer.prototype.changeType;
        SourceBuffer.prototype.changeType=function(...args){const value=Reflect.apply(change,this,args);bufferRecords.get(this)?.index.reset();notify();return value;};
      }
      const create=URL.createObjectURL;
      URL.createObjectURL=function(...args) {
        const url=Reflect.apply(create,this,args);
        if(args[0] instanceof MediaSource){urlSources.set(url,args[0]);while(urlSources.size>8)urlSources.delete(urlSources.keys().next().value);}
        return url;
      };
    }
  }catch(error){/* Unsupported instrumentation never blocks the site's player. */}
  function boot() {
  const rates = [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4];
  let video, enabled = true, held = false, rate = 1, busy = false, originalRate = 1;
  let generation = 0, initialSeekPending = false, cancellation = null;
  const panel = document.createElement('div');
  panel.style.cssText = 'position:fixed;right:16px;bottom:28px;z-index:2147483647;background:#202820ee;color:white;border-radius:9px;padding:12px;font:14px/1.6 system-ui;max-width:360px';
  panel.innerHTML = '<label><input type="checkbox" checked> 键盘浏览</label> <select aria-label="播放速度"></select> <button type="button">截图 S</button><div>按住空格播放，松开停止；− / + 调速</div><div data-status role="status"></div>';
  const toggle = panel.querySelector('input'), speed = panel.querySelector('select'), status = panel.querySelector('[data-status]');
  for (const r of rates) speed.add(new Option(`${r}×`, String(r), false, r === 1));
  const tell = message => { status.textContent = message; };
  function stop() { held = false; if (video) video.pause(); }
  function edit(target) { return target instanceof Element && !!target.closest('input,textarea,select,[contenteditable]:not([contenteditable="false"]),[role="textbox"]'); }
  function setRate(r) { rate = r; speed.value = String(r); if (enabled && video) video.playbackRate = rate; }
  function capabilities() {
    if (!video) return '等待原视频加载…';
    const record=recordFor(video);
    if(!record)return '未捕获分片帧索引；请用 page 注入并刷新。非 MP4／Worker 流暂不支持';
    if(record.index.error)return '逐帧不可用：'+record.index.error;
    try {const frame=record.index.locate(video.currentTime);return `← / → 真实邻帧 · 已索引 ${frame.count} 帧`;}
    catch(error){return error.message;}
  }
  function enforcePause() { if (enabled && !held && video) video.pause(); }
  function enforceRate() { if (enabled && video && video.playbackRate !== rate) video.playbackRate = rate; }
  function initialSeek() {
    if (!initialSeekPending || !video || video.readyState < 1) return;
    const match = location.hash.match(/^#recipe-time=(\d+(?:\.\d+)?)$/);
    if (match) video.currentTime = Math.max(0, Math.min(Number(match[1]), video.duration || Infinity));
    initialSeekPending = false;
    enforcePause();
  }
  function bind(v) {
    if (video === v) return;
    cancellation?.();stop(); generation++;
    if (video) {
      for (const [event, fn] of [['play', enforcePause], ['ratechange', enforceRate], ['loadedmetadata', initialSeek]]) video.removeEventListener(event, fn);
      video.playbackRate = originalRate;
    }
    video = v;
    if (!video) { tell(capabilities()); return; }
    originalRate = video.playbackRate; initialSeekPending = true;
    video.addEventListener('play', enforcePause); video.addEventListener('ratechange', enforceRate); video.addEventListener('loadedmetadata', initialSeek);
    if (enabled) { video.pause(); video.playbackRate = rate; }
    initialSeek();tell(capabilities());
  }
  function discover() {
    const candidates = [...document.querySelectorAll('video')].filter(v => v.getBoundingClientRect().width > 0);
    candidates.sort((a, b) => b.getBoundingClientRect().width * b.getBoundingClientRect().height - a.getBoundingClientRect().width * a.getBoundingClientRect().height);
    bind(candidates[0]);
  }
  function pauseAndSettle() {
    const playing=video&&!video.paused;stop();
    const record=video&&recordFor(video);
    if(playing&&enabled&&!busy&&!document.hidden&&record?.ready&&!record.index.error)return stepFrame(0,true);
  }
  async function stepFrame(direction,settle=false) {
    stop();
    if(busy||!video)return;
    const v=video,g=generation,src=v.currentSrc,record=recordFor(v);
    if(!record||!record.ready||v.seeking||v.readyState<2){tell(record?'等待缓冲／定位完成后重试':capabilities());return;}
    let target;
    try {
      target=record.index.locate(v.currentTime,direction);
      if(settle) {
        try {const next=record.index.locate(v.currentTime,1);
          if(Math.abs(next.pts-v.currentTime)+1e-8<Math.abs(target.pts-v.currentTime))target=next;
        }catch(error){/* End of indexed run: keep its current known frame. */}
      }
      let buffered=false;
      for(let n=0;n<v.buffered.length;n++)if(target.time>=v.buffered.start(n)&&target.time<v.buffered.end(n))buffered=true;
      if(!buffered)throw Error('相邻帧尚未缓冲，等待原播放器缓冲后重试');
    }catch(error){tell(error.message);return;}
    if(typeof v.requestVideoFrameCallback!=='function'){tell('浏览器缺少画面呈现回调，准确逐帧不可用');return;}
    busy=true;tell(settle?'正在稳定暂停画面…':'正在定位相邻帧…');const previous=v.currentTime;
    try {
      await new Promise((resolve,reject)=>{
        let sought=false,painted=false,callback=null,cancelLocal=null;
        const timeout=setTimeout(()=>{cleanup();reject(Error('帧定位超时'));},4000);
        const cleanup=()=>{clearTimeout(timeout);v.removeEventListener('seeked',done);v.removeEventListener('error',failed);if(callback!==null)v.cancelVideoFrameCallback(callback);if(cancellation===cancelLocal)cancellation=null;};
        const finish=()=>{if(sought&&painted){cleanup();resolve();}};
        const failed=()=>{cleanup();reject(Error('视频解码失败'));};
        const done=()=>{sought=true;finish();};
        cancelLocal=()=>{cleanup();const error=Error('操作已取消');error.name='AbortError';reject(error);};cancellation=cancelLocal;
        v.addEventListener('seeked',done);v.addEventListener('error',failed);
        callback=v.requestVideoFrameCallback(()=>{painted=true;finish();});
        try{v.currentTime=target.time;}catch(error){cleanup();reject(error);}
      });
      if(g!==generation||src!==v.currentSrc||!enabled)throw Error('视频或模式已改变');
      if(v.seeking||v.currentTime<target.start||v.currentTime>=target.end)throw Error(`播放器未停在目标帧区间（${v.currentTime.toFixed(6)} / ${target.start.toFixed(6)}–${target.end.toFixed(6)}）`);
      const actual=record.index.locate(v.currentTime);
      if(Math.abs(actual.pts-target.pts)>1e-7)throw Error('帧索引发生变化，请重试');
      tell(`${settle?'已暂停':(direction<0?'上一帧':'下一帧')} · ${target.pts.toFixed(6)} s`);
    }catch(error){
      if(g===generation&&src===v.currentSrc&&enabled){v.pause();if(error.name!=='AbortError')v.currentTime=previous;tell(error.name==='AbortError'?'已暂停':('逐帧失败：'+error.message));}
    }finally{busy=false;if(g===generation&&src===v.currentSrc&&enabled)v.pause();}
  }
  function screenshotTime(v) {
    try{const frame=recordFor(v)?.index.locate(v.currentTime);return frame?{time:frame.pts,kind:'frame'}:{time:v.currentTime,kind:'position'};}
    catch(error){return {time:v.currentTime,kind:'position'};}
  }
  async function screenshot() {
    if(video&&!video.paused&&!busy)await pauseAndSettle();else stop();
    if (!video || busy || video.seeking || video.readyState < 2 || !video.videoWidth) { tell('画面尚未就绪；请等待缓冲／定位后重试'); return; }
    const v = video, g = generation;
    busy = true;
    try {
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (g !== generation || v.seeking) throw new Error('视频或位置已改变，请重试');
      const canvas = document.createElement('canvas'); canvas.width = v.videoWidth; canvas.height = v.videoHeight;
      canvas.getContext('2d').drawImage(v, 0, 0);
      const capturedSource=v.currentSrc,capturedTime=screenshotTime(v),capturedID=location.pathname.match(/BV[A-Za-z0-9]+/)?.[0]||'bilibili';
      const blob = await new Promise((resolve, reject) => { canvas.toBlob(b => b ? resolve(b) : reject(new Error('无法编码图片')), 'image/png'); });
      if(g!==generation||capturedSource!==v.currentSrc)throw Error('截图期间视频已改变，请重试');
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      const id=capturedID;
      link.href = url; link.download = `${id}-${capturedTime.kind}-${capturedTime.time.toFixed(6)}s.png`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000); tell('已请求浏览器保存截图');
    } catch (error) { tell(error.name === 'SecurityError' ? '站点视频跨域策略禁止截图；可使用系统截图' : '截图失败：' + error.message); }
    finally { busy = false; }
  }
  window.addEventListener('keydown', event => {
    if (!enabled || !video || edit(event.target) || event.ctrlKey || event.altKey || event.metaKey) return;
    if (!['Space','ArrowLeft','ArrowRight','Minus','Equal','KeyS'].includes(event.code)) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (event.code === 'Space') {
      if (event.repeat || busy) return;
      held = true; video.playbackRate = rate;
      const v = video, g = generation;
      v.play().then(() => { if (!held || g !== generation || !enabled) v.pause(); }).catch(error => { stop(); tell('无法播放：' + error.message); });
    } else if (event.code === 'ArrowRight') { stepFrame(1); }
    else if (event.code === 'ArrowLeft') { stepFrame(-1); }
    else if (event.code === 'KeyS') { if (!event.repeat) screenshot(); }
    else { const n = rates.indexOf(rate); setRate(rates[Math.max(0, Math.min(rates.length-1, n + (event.code === 'Minus' ? -1 : 1)))]); }
  }, true);
  window.addEventListener('keyup', event => { if (event.code === 'Space' && held) { event.preventDefault(); event.stopImmediatePropagation(); pauseAndSettle(); } }, true);
  const stopWhenActive = () => { if (enabled || held) { cancellation?.();pauseAndSettle(); } };
  window.addEventListener('blur', stopWhenActive); window.addEventListener('pagehide', stopWhenActive);
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopWhenActive(); });
  toggle.addEventListener('change', () => { cancellation?.();stop(); enabled = toggle.checked; if (video) video.playbackRate = enabled ? rate : originalRate; tell(enabled ? capabilities() : '已恢复站点原有键盘操作'); });
  speed.addEventListener('change', () => setRate(Number(speed.value)));
  panel.querySelector('button').addEventListener('click', screenshot);
  function positionPanel() { const parent = document.fullscreenElement; (parent && parent.tagName !== 'VIDEO' ? parent : document.body).append(panel); }
  document.addEventListener('fullscreenchange', positionPanel);
  notify=()=>{if(!busy&&enabled)tell(capabilities());};
  positionPanel(); discover();
  new MutationObserver(discover).observe(document.body, {childList:true,subtree:true});
  }
  if(document.body)boot();else document.addEventListener('DOMContentLoaded',boot,{once:true});
})();
