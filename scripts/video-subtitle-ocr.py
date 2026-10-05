#!/usr/bin/env python3
"""Extract burned-in subtitles locally; checkpoint and watch completed videos."""
from __future__ import annotations
import argparse, collections, fcntl, hashlib, json, math, os, re, shutil, signal
import subprocess, sys, time
from pathlib import Path

VERSION = 1
EXTENSIONS = {'.mkv', '.mp4', '.webm', '.mov', '.avi'}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.chmod(0o644)
    temp.replace(path)


def read_exact(stream, size):
    chunks, remaining = [], size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b''.join(chunks)
    if data and len(data) != size:
        raise RuntimeError(f'truncated raw frame: {len(data)}/{size}')
    return data


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    streams = [s for s in info['streams'] if s['codec_type'] == 'video'
               and not s.get('disposition', {}).get('attached_pic')]
    if not streams:
        raise ValueError('no video stream')
    stream = streams[0]
    duration = float(info.get('format', {}).get('duration') or stream.get('duration') or 0)
    if duration <= 0:
        raise ValueError('missing or invalid duration')
    return {'width': stream['width'], 'height': stream['height'], 'duration': duration,
            'video_index': stream['index'],
            'rotation': next((float(d.get('rotation', 0)) for d in stream.get('side_data_list', [])
                              if 'rotation' in d), 0)}


def crop_pixels(region, width, height):
    x, y, w, h = region
    if min(x, y) < 0 or w <= 0 or h <= 0 or x + w > 1.00001 or y + h > 1.00001:
        raise ValueError('crop must be normalized x,y,width,height inside [0,1]')
    # Even geometry also works with chroma-subsampled sources. RGB conversion is
    # before exact crop: the declared raw byte size always matches FFmpeg output.
    xx, yy = int(x * width) // 2 * 2, int(y * height) // 2 * 2
    ww = min(max(2, int(w * width) // 2 * 2), width - xx)
    hh = min(max(2, int(h * height) // 2 * 2), height - yy)
    return xx, yy, ww, hh


def normalize(text):
    return re.sub(r'\s+', '', text)


def stamp(seconds):
    total = round(seconds * 1000)
    hours, total = divmod(total, 3600000)
    minutes, total = divmod(total, 60000)
    secs, millis = divmod(total, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02},{millis:03}'


def cues_from_rows(rows, duration, fps):
    groups = []
    for row in rows:
        end = min(duration, row['time'] + 1 / fps)
        if end <= row['time']:
            continue
        if groups and groups[-1]['text'] == row['text'] and row['time'] - groups[-1]['end'] < 1 / fps + .001:
            g = groups[-1]
            g['end'] = end
            g['scores'].append(row['confidence'])
        else:
            groups.append({'start': row['time'], 'end': end, 'text': row['text'],
                           'scores': [row['confidence']]})
    # Only bridge a short recognition glitch when the text on BOTH sides is
    # identical; never fuzzy-merge changing quantities or Chinese numerals.
    changed = True
    while changed:
        changed = False
        for i in range(1, len(groups) - 1):
            before, middle, after = groups[i - 1:i + 2]
            if (before['text'] and before['text'] == after['text']
                    and middle['end'] - middle['start'] <= .25 + 1e-6
                    and middle['end'] - middle['start'] < before['end'] - before['start']
                    and middle['end'] - middle['start'] < after['end'] - after['start']):
                before['end'] = after['end']
                before['scores'] += after['scores']
                before.setdefault('flags', []).append('bridged-single-frame-glitch')
                del groups[i:i + 2]
                changed = True
                break
    cues, rejected = [], []
    for g in groups:
        if not g['text']:
            continue
        scores = g.pop('scores')
        score = sum(scores) / len(scores)
        flags = g.setdefault('flags', [])
        length = g['end'] - g['start']
        if length < .5 and score < .85:
            rejected.append({**g, 'confidence': score, 'reason': 'short-low-confidence'})
            continue
        if length < .5:
            flags.append('short-caption')
        if score < .9:
            flags.append('low-confidence')
        if len(normalize(g['text'])) / length > 18:
            flags.append('fast-reading')
        if len(g['text'].splitlines()) > 2:
            flags.append('more-than-two-lines')
        cues.append({**g, 'confidence': round(score, 4)})
    return cues, rejected


def srt_text(cues):
    last = 0
    blocks = []
    for n, cue in enumerate(cues, 1):
        assert cue['start'] >= last - .00001 and cue['end'] > cue['start']
        assert cue['text'].strip()
        last = cue['end']
        blocks.append(f'{n}\n{stamp(cue["start"])} --> {stamp(cue["end"])}\n{cue["text"]}')
    return '\n\n'.join(blocks) + ('\n' if blocks else '')


class OCR:
    def __init__(self, threads):
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
        self.np = np
        self.engine = RapidOCR(intra_op_num_threads=threads, inter_op_num_threads=1,
                               det_limit_type='max', det_limit_side_len=1280, use_cls=False)

    def boxes(self, image):
        result, _ = self.engine(image)
        return result or []

    def text(self, image):
        result = self.boxes(image)
        if not result:
            return '', 0
        selected = []
        for box, text, score in result:
            tall = max(p[1] for p in box) - min(p[1] for p in box)
            if score >= .65 and tall >= max(10, image.shape[0] * .07):
                selected.append((box, normalize(text), float(score)))
        if not selected:
            return '', 0
        selected.sort(key=lambda r: (sum(p[1] for p in r[0]) / 4,
                                      min(p[0] for p in r[0])))
        # Cluster fragments into horizontal lines, then join lines top to bottom.
        lines = []
        for box, text, score in selected:
            center = sum(p[1] for p in box) / 4
            tall = max(p[1] for p in box) - min(p[1] for p in box)
            for line in lines:
                if abs(center - line['y']) <= tall * .6:
                    line['parts'].append((min(p[0] for p in box), text))
                    break
            else:
                lines.append({'y': center, 'parts': [(min(p[0] for p in box), text)]})
        text = '\n'.join(''.join(t for _, t in sorted(line['parts']))
                         for line in sorted(lines, key=lambda line: line['y']))
        return text, min(r[2] for r in selected)

    def detect_region(self, video, info, duration):
        w, h = info['width'], info['height']
        base = crop_pixels((.1, .08, .8, .87), w, h)
        x, y, cw, ch = base
        candidates = []
        for point in (.1, .25, .4, .55, .7, .85):
            t = min(duration - .1, max(0, duration * point))
            cmd = ['ffmpeg', '-v', 'error', '-threads', '2', '-noautorotate', '-ss', str(t),
                   '-i', str(video), '-map', f'0:{info["video_index"]}', '-frames:v', '1',
                   '-vf', f'format=bgr24,crop={cw}:{ch}:{x}:{y}:exact=1',
                   '-pix_fmt', 'bgr24', '-f', 'rawvideo', 'pipe:1']
            data = subprocess.run(cmd, capture_output=True, check=True).stdout
            if len(data) != cw * ch * 3:
                raise RuntimeError('region-probe raw frame size mismatch')
            img = self.np.frombuffer(data, dtype=self.np.uint8).reshape(ch, cw, 3)
            for box, text, score in self.boxes(img):
                cx = sum(p[0] for p in box) / 4 + x
                cy = sum(p[1] for p in box) / 4 + y
                bh = max(p[1] for p in box) - min(p[1] for p in box)
                if score >= .8 and len(normalize(text)) >= 3 and .25*w < cx < .75*w and bh >= .015*h:
                    candidates.append({'y': cy/h, 'height': bh/h, 'text': normalize(text), 'at': t})
        clusters = []
        for item in candidates:
            for cluster in clusters:
                if abs(item['y'] - sum(c['y'] for c in cluster)/len(cluster)) <= .035:
                    cluster.append(item)
                    break
            else:
                clusters.append([item])
        reliable = [c for c in clusters if len({v['at'] for v in c}) >= 3
                    and len({v['text'] for v in c}) >= 3]
        if not reliable:
            return (.1, .79, .8, .15), ['region-not-confirmed'], candidates
        best = max(reliable, key=lambda c: (len({v['at'] for v in c}),
                                            sum(len(v['text']) for v in c)))
        center = sorted(v['y'] for v in best)[len(best)//2]
        pad = max(.045, max(v['height'] for v in best) * 1.5)
        lower, upper = max(0, center-pad), min(1, center+pad)
        return (.08, lower, .84, upper-lower), [], candidates


def signature(video):
    st = video.stat()
    return {'size': st.st_size, 'mtime_ns': st.st_mtime_ns}


def config(args):
    return {'version': VERSION, 'fps': args.fps, 'profile': args.profile,
            'crop': args.crop, 'duration': args.duration, 'chunk_seconds': args.chunk_seconds,
            'engine': 'rapidocr-onnxruntime-1.4.4/PP-OCRv4', 'corrections': args.corrections_data}


def process_video(video, args, ocr, control):
    before = signature(video)
    settings = config(args)
    report_path = video.with_name(video.stem + '.ocr.json')
    srt_path = video.with_name(video.stem + '.ocr.zh-CN.srt')
    cache_key = hashlib.sha256(json.dumps([str(video), before, settings], sort_keys=True).encode()).hexdigest()
    work = control / 'work' / cache_key
    work.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        previous = json.loads(report_path.read_text())
        owned = (previous.get('tool') == 'video-subtitle-ocr'
                 and previous.get('source') == str(video))
        if not owned:
            return {'status': 'output-conflict', 'video': str(video), 'report': str(report_path)}
        if previous.get('fingerprint') == cache_key and previous.get('status') in ('done', 'review', 'no_subtitles'):
            expected = previous.get('srt_sha256')
            valid = (not expected and not srt_path.exists()) or (srt_path.exists() and hashlib.sha256(srt_path.read_bytes()).hexdigest() == expected)
            if valid:
                return {'status': 'skipped', 'previous_status': previous['status'], 'video': str(video), 'cues': previous['cue_count']}
        recovering = (previous.get('status') == 'publishing' and previous.get('fingerprint') == cache_key
                      and (not srt_path.exists() or hashlib.sha256(srt_path.read_bytes()).hexdigest() == previous.get('srt_sha256')))
        if not args.replace_owned and not recovering:
            return {'status': 'output-conflict', 'video': str(video), 'reason': 'changed source, settings or output; use --replace-owned only for owned output'}
        if srt_path.exists() and hashlib.sha256(srt_path.read_bytes()).hexdigest() != previous.get('srt_sha256'):
            return {'status': 'output-conflict', 'video': str(video), 'reason': 'subtitle edited externally; preserved'}
    elif srt_path.exists():
        return {'status': 'output-conflict', 'video': str(video), 'reason': 'existing subtitle is not owned by this tool'}
    info = probe(video)
    duration = min(info['duration'], args.duration) if args.duration else info['duration']
    region_file = work/'region.json'
    if region_file.exists():
        detection = json.loads(region_file.read_text())
    else:
        flags = ['rotation-requires-check'] if info['rotation'] else []
        if args.crop:
            region, extra, candidates = args.crop, [], []
        elif args.profile == 'cooking':
            region, extra, candidates = (.104, .809, .792, .117), [], []
        else:
            region, extra, candidates = ocr.detect_region(video, info, duration)
        detection = {'region': region, 'flags': flags+extra, 'candidates': candidates}
        atomic_json(region_file, detection)
    x,y,width,height = crop_pixels(detection['region'], info['width'], info['height'])
    rows = []
    start_clock = time.monotonic()
    chunks = math.ceil(duration / args.chunk_seconds)
    for chunk in range(chunks):
        if shutil.disk_usage(control).free < args.min_free_gib * 1024**3:
            raise RuntimeError('paused: insufficient free disk space')
        chunk_path = work/f'{chunk:06}.json'
        if chunk_path.exists():
            rows.extend(json.loads(chunk_path.read_text()))
            continue
        start = chunk * args.chunk_seconds
        length = min(args.chunk_seconds, duration-start)
        cmd = ['ffmpeg', '-v', 'error', '-threads', '2', '-noautorotate', '-ss', str(start),
               '-i', str(video), '-t', str(length), '-map', f'0:{info["video_index"]}',
               '-filter_threads', '1', '-vf', f'setpts=PTS-STARTPTS,fps={args.fps},format=bgr24,crop={width}:{height}:{x}:{y}:exact=1',
               '-pix_fmt', 'bgr24', '-f', 'rawvideo', 'pipe:1']
        error_path = work/'ffmpeg-error.log'
        chunk_rows = []
        with error_path.open('wb') as stderr:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=stderr)
            try:
                n = 0
                while True:
                    raw = read_exact(proc.stdout, width*height*3)
                    if not raw:
                        break
                    img = ocr.np.frombuffer(raw, dtype=ocr.np.uint8).reshape(height,width,3)
                    text, score = ocr.text(img)
                    chunk_rows.append({'time': start+n/args.fps, 'text': text, 'confidence': score})
                    n += 1
                if proc.wait() != 0:
                    raise RuntimeError('FFmpeg decode failed: '+error_path.read_text()[-500:])
            finally:
                proc.stdout.close()
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
        expected = length*args.fps
        if len(chunk_rows) == 0 or abs(len(chunk_rows)-expected)>2:
            raise RuntimeError(f'frame count mismatch: {len(chunk_rows)} vs {expected:.2f}')
        atomic_json(chunk_path, chunk_rows)
        rows.extend(chunk_rows)
        print(json.dumps({'video':video.name,'processed_seconds':round(start+length,2),
                          'duration':round(duration,2),'frames':len(rows)},ensure_ascii=False),flush=True)
    if signature(video) != before:
        raise RuntimeError('source changed during OCR; output was not published')
    cues, rejected = cues_from_rows(rows, duration, args.fps)
    for cue in cues:
        if cue['text'] in args.corrections_data:
            cue['text'] = args.corrections_data[cue['text']]
            cue['flags'].append('dictionary-correction')
    flags = list(detection['flags'])
    if rejected:
        flags.append('rejected-fragments')
    if cues and sum(c['end']-c['start'] for c in cues)/duration < .08:
        flags.append('sparse-subtitles')
    review = [dict(index=i, **c) for i,c in enumerate(cues,1) if c['flags']]
    if review:
        flags.append('uncertain-cues')
    state = ('review' if flags else 'done') if cues else 'no_subtitles'
    payload = srt_text(cues).encode('utf-8')
    # Publish a recovery journal first. A crash between SRT and final report is
    # recoverable, but a different preexisting subtitle never gets overwritten.
    report = {'tool':'video-subtitle-ocr','version':VERSION,'source':str(video),
              'signature':before,'fingerprint':cache_key,'settings':settings,
              'status':state,'human_reviewed':False,'cue_count':len(cues),
              'duration':duration,'info':info,'region':detection['region'],
              'timing_resolution':1/args.fps,'frames':len(rows),
              'elapsed_seconds':round(time.monotonic()-start_clock,2),
              'flags':flags,'review_cues':review,'rejected':rejected,
              'srt_sha256':hashlib.sha256(payload).hexdigest() if cues else None}
    if cues:
        atomic_json(report_path, {**report, 'status':'publishing'})
        temp = srt_path.with_name(srt_path.name+'.tmp')
        temp.write_bytes(payload);temp.chmod(0o644);temp.replace(srt_path)
        subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name',
                        '-of','csv=p=0',str(srt_path)],capture_output=True,check=True)
    atomic_json(report_path,report)
    return {'status':state,'video':str(video),'cues':len(cues),'flags':flags,'report':str(report_path)}


def discover(root, watch, stable_seconds):
    if root.is_file():
        files = [root]
    else:
        files = sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS
                       and not any(part.startswith('.') or part == 'OCR样稿'
                                   for part in p.relative_to(root).parts))
    return [p.resolve() for p in files if not p.is_symlink()
            and (not watch or time.time()-p.stat().st_mtime >= stable_seconds)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--profile',choices=['auto','cooking'],default='auto')
    parser.add_argument('--crop',help='normalized x,y,width,height; overrides profile')
    parser.add_argument('--fps',type=float,default=4)
    parser.add_argument('--duration',type=float,help='process only first N seconds (for samples)')
    parser.add_argument('--chunk-seconds',type=int,default=60)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--watch',action='store_true',help='watch for completed new videos')
    parser.add_argument('--poll-seconds',type=int,default=120)
    parser.add_argument('--stable-seconds',type=int,default=30)
    parser.add_argument('--max-videos',type=int,default=0)
    parser.add_argument('--min-free-gib',type=float,default=5)
    parser.add_argument('--replace-owned',action='store_true',help='replace only unedited outputs created by this tool')
    parser.add_argument('--corrections',type=Path,help='optional JSON dictionary of complete-cue replacements')
    parser.add_argument('--list',action='store_true',help='list input files without OCR or writes')
    args=parser.parse_args()
    if not args.input.exists():parser.error('input does not exist')
    if args.crop:
        try:args.crop=[float(x) for x in args.crop.split(',')];assert len(args.crop)==4;crop_pixels(args.crop,1920,1080)
        except (AssertionError,ValueError):parser.error('invalid --crop x,y,width,height')
    if not (0<args.fps<=12) or args.chunk_seconds<=0 or not 1<=args.threads<=32 or args.poll_seconds<1 or args.stable_seconds<0 or args.min_free_gib<0 or args.max_videos<0 or (args.duration is not None and args.duration<=0):parser.error('invalid numeric option')
    if abs(args.chunk_seconds*args.fps-round(args.chunk_seconds*args.fps))>1e-6:parser.error('chunk-seconds * fps must be an integer')
    args.corrections_data=json.loads(args.corrections.read_text()) if args.corrections else {}
    if not isinstance(args.corrections_data,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v.strip() for k,v in args.corrections_data.items()):parser.error('corrections must map text to nonempty text')
    root=args.input.resolve()
    if args.list:
        for p in discover(root,args.watch,args.stable_seconds):print(p)
        return 0
    control=(root.parent if root.is_file() else root)/'.subtitle-ocr'
    control.mkdir(exist_ok=True)
    with (control/'lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:parser.error('another OCR task is already running in this directory')
        ocr=OCR(args.threads)
        index_path=control/'index.json'
        index=json.loads(index_path.read_text()) if index_path.exists() else {}
        seen,processed,errors={},0,0
        retry_after={}
        while True:
            for video in discover(root,args.watch,args.stable_seconds):
                current=signature(video)
                if seen.get(str(video))==current or time.time()<retry_after.get(str(video),0):continue
                try:result=process_video(video,args,ocr,control)
                except Exception as e:
                    result={'status':'error','video':str(video),'error':str(e)};errors+=1
                print(json.dumps(result,ensure_ascii=False),flush=True)
                index[str(video)]=result;atomic_json(index_path,index)
                if result['status']=='error':retry_after[str(video)]=time.time()+600
                else:seen[str(video)]=current
                if result['status']!='skipped':processed+=1
                if args.max_videos and processed>=args.max_videos:return 1 if errors else 0
            if not args.watch:return 1 if errors else 0
            print(json.dumps({'status':'waiting','known_videos':len(seen),'poll_seconds':args.poll_seconds}),flush=True)
            time.sleep(args.poll_seconds)

if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:sys.exit(130)
