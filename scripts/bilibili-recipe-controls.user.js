// ==UserScript==
// @name         菜谱原视频键盘浏览（实验版）
// @namespace    nix-tools.recipe
// @version      0.1.0
// @description  按住空格播放，松开暂停；调速和暂停截图。精确逐帧须浏览器支持。
// @match        https://www.bilibili.com/video/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==
(() => {
  'use strict';
  if (window.top !== window.self) return;
  const rates = [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4];
  let video, enabled = true, held = false, rate = 1, busy = false, originalRate = 1;
  let frameTime = null, callbackId = null, generation = 0, initialSeekPending = false;
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
    return typeof video.seekToNextFrame === 'function' ? '→ 原生下一帧；← 暂未支持' : '当前浏览器无原生逐帧接口；← / → 不会跳秒';
  }
  function enforcePause() { if (enabled && !held && video) video.pause(); }
  function invalidateFrame() { frameTime = null; }
  function enforceRate() { if (enabled && video && video.playbackRate !== rate) video.playbackRate = rate; }
  function observeFrames(v, g) {
    if (typeof v.requestVideoFrameCallback !== 'function') return;
    callbackId = v.requestVideoFrameCallback((_, metadata) => {
      if (g !== generation || video !== v) return;
      frameTime = metadata.mediaTime;
      observeFrames(v, g);
    });
  }
  function initialSeek() {
    if (!initialSeekPending || !video || video.readyState < 1) return;
    const match = location.hash.match(/^#recipe-time=(\d+(?:\.\d+)?)$/);
    if (match) video.currentTime = Math.max(0, Math.min(Number(match[1]), video.duration || Infinity));
    initialSeekPending = false;
    enforcePause();
  }
  function bind(v) {
    if (video === v) return;
    stop(); generation++;
    if (video) {
      for (const [event, fn] of [['play', enforcePause], ['ratechange', enforceRate], ['loadedmetadata', initialSeek], ['seeking', invalidateFrame]]) video.removeEventListener(event, fn);
      if (callbackId !== null && video.cancelVideoFrameCallback) video.cancelVideoFrameCallback(callbackId);
      video.playbackRate = originalRate;
    }
    video = v; frameTime = null; callbackId = null;
    if (!video) { tell(capabilities()); return; }
    originalRate = video.playbackRate; initialSeekPending = true;
    video.addEventListener('play', enforcePause); video.addEventListener('ratechange', enforceRate); video.addEventListener('loadedmetadata', initialSeek); video.addEventListener('seeking', invalidateFrame);
    if (enabled) { video.pause(); video.playbackRate = rate; }
    initialSeek(); observeFrames(video, generation); tell(capabilities());
  }
  function discover() {
    const candidates = [...document.querySelectorAll('video')].filter(v => v.getBoundingClientRect().width > 0);
    candidates.sort((a, b) => b.getBoundingClientRect().width * b.getBoundingClientRect().height - a.getBoundingClientRect().width * a.getBoundingClientRect().height);
    bind(candidates[0]);
  }
  async function nextFrame() {
    stop();
    if (busy || !video) return;
    if (typeof video.seekToNextFrame !== 'function') { tell(capabilities()); return; }
    const v = video, g = generation;
    busy = true;
    try { await v.seekToNextFrame(); if (g === generation) tell('已使用浏览器原生下一帧'); }
    catch (error) { tell('下一帧失败：' + error.message); }
    finally { busy = false; v.pause(); }
  }
  async function screenshot() {
    stop();
    if (!video || busy || video.seeking || video.readyState < 2 || !video.videoWidth) { tell('画面尚未就绪；请等待缓冲／定位后重试'); return; }
    const v = video, g = generation;
    busy = true;
    try {
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (g !== generation || v.seeking) throw new Error('视频或位置已改变，请重试');
      const canvas = document.createElement('canvas'); canvas.width = v.videoWidth; canvas.height = v.videoHeight;
      canvas.getContext('2d').drawImage(v, 0, 0);
      const blob = await new Promise((resolve, reject) => { canvas.toBlob(b => b ? resolve(b) : reject(new Error('无法编码图片')), 'image/png'); });
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      const id = location.pathname.match(/BV[A-Za-z0-9]+/)?.[0] || 'bilibili';
      link.href = url; link.download = `${id}-${(frameTime ?? v.currentTime).toFixed(3)}s.png`; link.click();
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
    } else if (event.code === 'ArrowRight') { if (!event.repeat) nextFrame(); }
    else if (event.code === 'ArrowLeft') { stop(); tell('精确上一帧暂未实现；没有用跳秒代替'); }
    else if (event.code === 'KeyS') { if (!event.repeat) screenshot(); }
    else { const n = rates.indexOf(rate); setRate(rates[Math.max(0, Math.min(rates.length-1, n + (event.code === 'Minus' ? -1 : 1)))]); }
  }, true);
  window.addEventListener('keyup', event => { if (event.code === 'Space' && held) { event.preventDefault(); event.stopImmediatePropagation(); stop(); } }, true);
  const stopWhenActive = () => { if (enabled || held) stop(); };
  window.addEventListener('blur', stopWhenActive); window.addEventListener('pagehide', stopWhenActive);
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopWhenActive(); });
  toggle.addEventListener('change', () => { stop(); enabled = toggle.checked; if (video) video.playbackRate = enabled ? rate : originalRate; tell(enabled ? capabilities() : '已恢复站点原有键盘操作'); });
  speed.addEventListener('change', () => setRate(Number(speed.value)));
  panel.querySelector('button').addEventListener('click', screenshot);
  function positionPanel() { const parent = document.fullscreenElement; (parent && parent.tagName !== 'VIDEO' ? parent : document.body).append(panel); }
  document.addEventListener('fullscreenchange', positionPanel);
  positionPanel(); discover();
  new MutationObserver(discover).observe(document.body, {childList:true,subtree:true});
})();
