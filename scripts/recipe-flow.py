#!/usr/bin/env python3
"""Serial video-to-recipe workflow, durable publication and guarded media release."""
import argparse
import copy
import contextlib
import io
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


batch = module('recipe-batch')
ingredients = module('recipe-ingredients')
DEFAULT_SAMPLING = {'width': 960, 'candidates': 12, 'interval': 1, 'padding': 5, 'strategy': 'bounded-uniform-per-window'}
MEDIA_SUFFIXES = {'.mkv', '.mp4', '.webm', '.mov'}


def safe(path, base):
    """Reject links in every component, including ancestors of the declared root."""
    path = Path(os.path.abspath(path)); base = Path(os.path.abspath(base))
    if not path.is_relative_to(base):
        raise ValueError('path outside declared root: ' + str(path))
    for part in [path] + list(path.parents):
        if part.is_symlink():
            raise ValueError('linked path: ' + str(part))
    return path


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def durable_mkdir(path):
    path = safe(path, path)
    missing = []; current = path
    while not current.exists():
        missing.append(current); current = current.parent
    for directory in reversed(missing):
        directory.mkdir(); sync_dir(directory); sync_dir(directory.parent)


def durable_tree(path):
    for p in path.rglob('*'):
        if p.is_symlink(): raise ValueError('linked artifact')
        if p.is_file():
            with p.open('rb') as stream: os.fsync(stream.fileno())
    for p in sorted([p for p in path.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True): sync_dir(p)
    sync_dir(path)


def atomic(path, value, text=False, exclusive=False):
    path = Path(path); safe(path, path.parent); path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(value.encode() if text else batch.encoded(value)); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name, 0o644)
        if exclusive: os.link(name, path)
        else: os.replace(name, path)
        sync_dir(path.parent)
    finally:
        if os.path.exists(name): os.unlink(name)


def immutable(path, value):
    atomic(path, value, exclusive=True)

def build_library(source, destination, dictionary):
    with contextlib.redirect_stdout(io.StringIO()): batch.library_module().build(source, destination, dictionary)


class Flow:
    def __init__(self, root, read_only=False):
        self.root = safe(root, root); safe(self.root / 'flow.sqlite3', self.root); self.lock = None
        if read_only:
            self.db = sqlite3.connect((self.root / 'flow.sqlite3').as_uri() + '?mode=ro', uri=True)
        else:
            durable_mkdir(self.root)
            lockfile = safe(self.root / '.lock', self.root); self.lock = lockfile.open('a')
            try: fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.lock.close(); raise ValueError('workflow busy; single writer required')
            safe(self.root / 'flow.sqlite3', self.root)
            self.db = sqlite3.connect(self.root / 'flow.sqlite3')
            self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA synchronous=FULL')
            self.db.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, started INTEGER NOT NULL DEFAULT 0, entry TEXT NOT NULL, state TEXT NOT NULL, queue TEXT, archive TEXT, publication TEXT, record TEXT, release TEXT, error TEXT)')
            if 'started' not in {row[1] for row in self.db.execute('PRAGMA table_info(items)')}:
                self.db.execute('ALTER TABLE items ADD COLUMN started INTEGER NOT NULL DEFAULT 0')
                self.db.execute("UPDATE items SET started=1 WHERE state != 'queued' OR queue IS NOT NULL OR archive IS NOT NULL")
            columns = {row[1] for row in self.db.execute('PRAGMA table_info(items)')}
            for name, declaration in [('revision', 'INTEGER NOT NULL DEFAULT 1'), ('previous_archive', 'TEXT'), ('rework_seed', 'TEXT')]:
                if name not in columns: self.db.execute('ALTER TABLE items ADD COLUMN ' + name + ' ' + declaration)
            self.db.execute('CREATE TABLE IF NOT EXISTS deliveries (sha TEXT PRIMARY KEY,path TEXT NOT NULL,state TEXT NOT NULL,error TEXT)')
            self.db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL)'); self.db.commit()
        self.db.row_factory = sqlite3.Row

    def close(self):
        self.db.close()
        if self.lock: self.lock.close()

    def setting(self, key):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        if not row: raise ValueError('initialize workflow first')
        return json.loads(row['value'])

    def init(self, media_root=None, browser=None, max_retained=3, min_free_gib=5, sampling=None, media_mode=None):
        settings = {'media_root': str(safe(media_root or self.root / 'media', media_root or self.root / 'media')), 'browser': browser, 'max_retained': max_retained, 'min_free_gib': min_free_gib, 'sampling': sampling or DEFAULT_SAMPLING}
        if media_mode is not None:
            if media_mode not in ('images','clips'): raise ValueError('invalid media mode')
            settings['sampling'] = {**settings['sampling'], 'media_mode': media_mode}
        if type(max_retained) is not int or max_retained < 1 or not batch.finite(min_free_gib) or min_free_gib < 0: raise ValueError('invalid capacity')
        if browser is not None and (not isinstance(browser, str) or not browser.startswith('firefox') or '\n' in browser): raise ValueError('browser must be firefox or firefox:/absolute/Zen/profile')
        if self.db.execute('SELECT 1 FROM settings').fetchone():
            if self.setting('config') != settings: raise ValueError('existing workflow configuration is immutable')
            return
        sampling = settings['sampling']
        if not 16 <= sampling['width'] <= 3840 or not 1 <= sampling['candidates'] <= 12 or not batch.finite(sampling['interval']) or sampling['interval'] <= 0 or not batch.finite(sampling['padding']) or not 0 <= sampling['padding'] <= 60: raise ValueError('invalid sampling')
        for name in ('queues', 'accepted', 'receipts', 'library', 'media', 'logs'): durable_mkdir(safe(self.root / name, self.root))
        durable_mkdir(Path(settings['media_root']))
        dictionary = batch.load(ROOT / 'config/recipe/ingredients.json'); ingredients.vocabulary(dictionary)
        atomic(self.root / 'dictionary.json', dictionary)
        with self.db: self.db.execute('INSERT INTO settings VALUES(?,?)', ('config', json.dumps(settings)))

    def row(self, vid):
        row = self.db.execute('SELECT * FROM items WHERE id=?', (vid,)).fetchone()
        if not row: raise ValueError('unknown video ID')
        return row

    def key(self, row):
        return row['id'] if row['revision'] == 1 else row['id'] + '-r' + str(row['revision'])

    def update(self, vid, **values):
        if not set(values) <= {'state', 'queue', 'archive', 'publication', 'record', 'release', 'error', 'started', 'revision', 'previous_archive', 'rework_seed'}: raise ValueError('invalid workflow update')
        with self.db: self.db.execute('UPDATE items SET ' + ','.join(k + '=?' for k in values) + ' WHERE id=?', tuple(values.values()) + (vid,))

    def add(self, path):
        self.setting('config'); entries = batch.load(path)
        # Also accept yt-dlp --flat-playlist --dump-single-json output; enumeration is separate.
        if isinstance(entries, dict) and isinstance(entries.get('entries'), list):
            entries = [{'id': e.get('id'), 'title': e.get('title'), 'author': e.get('uploader') or entries.get('uploader')} for e in entries['entries']]
        if not isinstance(entries, list) or not entries: raise ValueError('nonempty manifest required')
        prepared = []
        for raw in entries:
            if not isinstance(raw, dict) or set(raw) - {'id', 'title', 'author', 'video', 'subtitles', 'subtitle_origin', 'seed'}: raise ValueError('invalid entry fields')
            if not all(isinstance(raw.get(k), str) and raw[k].strip() for k in ('id', 'title', 'author')) or not re.fullmatch(r'BV[A-Za-z0-9]+', raw['id']): raise ValueError('invalid video metadata')
            entry = copy.deepcopy(raw)
            for k in ('video', 'subtitles', 'seed'):
                if k in entry:
                    p = Path(entry[k]); p = p if p.is_absolute() else Path(path).absolute().parent / p
                    safe(p, p); entry[k] = str(p.absolute())
            if ('subtitles' in entry or 'seed' in entry) and 'video' not in entry: raise ValueError('subtitles/seed require a video')
            if entry.get('subtitle_origin', 'ocr') not in ('ocr', 'platform', 'asr'): raise ValueError('invalid subtitle origin')
            old = self.db.execute('SELECT entry FROM items WHERE id=?', (entry['id'],)).fetchone()
            if old and json.loads(old['entry']) != entry: raise ValueError('registered metadata is immutable: ' + entry['id'])
            prepared.append(entry)
        if len({e['id'] for e in prepared}) != len(prepared): raise ValueError('duplicate manifest IDs')
        ordinal = self.db.execute('SELECT coalesce(max(ordinal),0) FROM items').fetchone()[0]
        with self.db:
            for entry in prepared:
                ordinal += 1
                self.db.execute('INSERT OR IGNORE INTO items(id,ordinal,entry,state) VALUES(?,?,?,?)', (entry['id'], ordinal, json.dumps(entry, ensure_ascii=False), 'queued'))
        return {'registered': len(prepared), 'total': self.db.execute('SELECT count(*) FROM items').fetchone()[0]}

    def log_command(self, vid, kind, command):
        # Never record Cookie values; only the browser selector is persisted in config.
        with safe(self.root / 'logs' / (vid + '-' + kind + '.log'), self.root).open('ab') as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, pass_fds=(self.lock.fileno(),))

    def inputs(self, row):
        config = self.setting('config'); entry = json.loads(row['entry']); vid = entry['id']
        if 'video' not in entry:
            directory = safe(Path(config['media_root']) / vid, config['media_root']); durable_mkdir(directory)
            video = directory / 'source.mkv'; info = directory / 'source.info.json'; marker = directory / 'download.json'
            if not marker.exists():
                command = ['yt-dlp', '--no-playlist', '--continue', '--no-overwrites', '--no-progress', '--sleep-requests', '15', '--sleep-interval', '30', '--max-sleep-interval', '60', '--limit-rate', '2M', '--concurrent-fragments', '1', '--retries', '3', '--fragment-retries', '3', '--write-info-json', '--merge-output-format', 'mkv', '--remux-video', 'mkv', '-o', str(directory / 'source.%(ext)s')]
                if config['browser']: command += ['--cookies-from-browser', config['browser']]
                self.log_command(vid, 'download', command + ['https://www.bilibili.com/video/' + vid])
                if not info.is_file() or batch.load(info).get('id') != vid: raise ValueError('download metadata ID mismatch')
                batch.probe(batch.file(video)); atomic(marker, {'id': vid, 'sha256': batch.digest(video), 'stat': batch.stamp(video)})
            saved = batch.load(marker)
            if saved['id'] != vid or batch.stamp(video) != saved['stat'] or batch.digest(video) != saved['sha256']: raise ValueError('download changed')
            entry['video'] = str(video)
        if row['rework_seed']:
            entry['seed'] = row['rework_seed']
        video = batch.file(safe(entry['video'], entry['video'])); batch.probe(video)
        if 'subtitles' not in entry:
            subtitles = video.with_name(video.stem + '.ocr.zh-CN.srt'); report = video.with_name(video.stem + '.ocr.json')
            self.log_command(vid, 'ocr', [str(ROOT / 'scripts/subtitle-ocr'), str(video), '--profile', 'auto', '--min-free-gib', str(config['min_free_gib'])])
            data = batch.load(report)
            if data.get('tool') != 'video-subtitle-ocr' or data.get('status') not in ('done', 'review') or data.get('settings', {}).get('duration') is not None or data.get('source') != str(video) or batch.digest(subtitles) != data.get('srt_sha256'): raise ValueError('OCR did not yield a verified full subtitle file')
            entry['subtitles'] = str(subtitles); entry['subtitle_origin'] = 'ocr'
        entry.setdefault('subtitle_origin', 'ocr')
        return entry

    def retain_count(self):
        return self.db.execute("SELECT count(*) FROM items WHERE (started=1 OR archive IS NOT NULL) AND state != 'deleted'").fetchone()[0]

    def next(self, delete_videos=False):
        # Frozen accepted snapshots bypass the stage controller and original video entirely.
        self.recover(delete_videos)
        row = self.db.execute("SELECT * FROM items WHERE archive IS NULL AND state != 'failed' ORDER BY ordinal LIMIT 1").fetchone()
        if not row: return self.status()
        config = self.setting('config')
        if not row['started'] and self.retain_count() >= config['max_retained']: return {'paused': 'retained-video limit', **self.status()}
        if min(shutil.disk_usage(self.root).free, shutil.disk_usage(config['media_root']).free) < config['min_free_gib'] * 1024 ** 3: return {'paused': 'low disk space', **self.status()}
        vid = row['id']
        try:
            queue_path = Path(row['queue']) if row['queue'] else self.root / 'queues' / self.key(row)
            if not row['queue']:
                self.update(vid, state='preparing', started=1)
                entry = self.inputs(row)
                manifest = self.root / 'receipts' / (self.key(row) + '-input.json')
                if manifest.exists():
                    if batch.load(manifest) != [entry]: raise ValueError('prepared input changed')
                else: immutable(manifest, [entry])
                with_queue = batch.Queue(queue_path)
                try: with_queue.add(manifest, config['sampling'])
                finally: with_queue.close()
                self.update(vid, queue=str(queue_path), state='processing')
            q = batch.Queue(safe(queue_path, self.root))
            try:
                result = q.run(vid); job = q.db.execute('SELECT * FROM jobs WHERE id=?', (vid,)).fetchone()
                if job['status'] == 'failed': raise ValueError(job['error'])
                self.update(vid, state=job['status'], error=None)
                if job['status'] == 'complete': self.accept(q, job)
            finally: q.close()
        except Exception as exc:
            self.update(vid, state='failed', error=str(exc)); raise
        return self.recover(delete_videos)

    def accept(self, q, job):
        vid = job['id']; entry, _ = q.entry(job)
        folders = [q.folder(key) for key in q.active_keys(job) if q.db.execute('SELECT stage,status FROM tasks WHERE key=?', (key,)).fetchone()['stage'] == 'assemble']
        if len(folders) != 1: raise ValueError('one current assembly required')
        source = folders[0]; batch.verify(source)
        data = batch.library_module().validate(source, batch.load(batch.CONTRACTS / 'video-recipe.schema.json'))
        if data['source']['video_id'] != vid or batch.digest(entry['video']) != entry['video_sha256']: raise ValueError('source changed before acceptance')
        target = safe(self.root / 'accepted' / self.key(self.row(vid)), self.root)
        if target.exists(): batch.verify(target)
        else:
            with tempfile.TemporaryDirectory(prefix='.accept-', dir=target.parent) as tmp:
                draft = Path(tmp) / 'output'; shutil.copytree(source, draft); (draft / 'checksums.json').unlink()
                ocr = Path(entry['video']).with_name(Path(entry['video']).stem + '.ocr.json')
                ocr_review = entry['subtitle_origin'] == 'ocr'
                if entry['subtitle_origin'] == 'ocr' and ocr.is_file():
                    report = batch.load(ocr)
                    st = Path(entry['video']).stat()
                    signature = {'size': st.st_size, 'mtime_ns': st.st_mtime_ns}
                    bound = report.get('tool') == 'video-subtitle-ocr' and report.get('source') == entry['video'] and report.get('signature') == signature and report.get('srt_sha256') == entry['subtitles_sha256'] and 'settings' in report and report['settings'].get('duration') is None
                    shutil.copyfile(ocr, draft / 'source-ocr.json')
                    ocr_review = not bound or report.get('status') != 'done' or bool(report.get('flags'))
                ready = data['status'] == 'ready' and data['coverage'] == 'full' and (batch.load(source/'processing.json').get('media_mode') == 'clips' or all(s['selected_frame_id'] for s in data['steps'])) and not any(i['resolution'] == 'open' for i in data['issues']) and not ocr_review
                immutable(draft / 'acceptance.json', {'video_id': vid, 'source_video': entry['video'], 'video_sha256': entry['video_sha256'], 'video_stat': batch.stamp(entry['video']), 'assembly_sha256': batch.digest(source / 'recipe.internal.json'), 'release_ready': ready, 'release_policy': '1.0.0', 'ocr_review_pending': ocr_review, 'human_reviewed': False})
                immutable(draft / 'checksums.json', batch.artifacts(draft)); durable_tree(draft); draft.rename(target); sync_dir(target.parent)
        acceptance = batch.load(target / 'acceptance.json')
        if acceptance['assembly_sha256'] != batch.digest(source / 'recipe.internal.json') or acceptance['video_sha256'] != entry['video_sha256']: raise ValueError('accepted revision collision')
        self.update(vid, archive=str(target), state='accepted', error=None, started=1)

    def adopt(self, queue_path, vid):
        q = batch.Queue(queue_path, read_only=True)
        try:
            binding = q.db.execute("SELECT value FROM settings WHERE key='model_binding'").fetchone(); q.model_binding = binding['value'] if binding else None
            job = q.db.execute('SELECT * FROM jobs WHERE id=?', (vid,)).fetchone()
            if not job or job['status'] != 'complete': raise ValueError('only complete current queue jobs can be adopted')
            entry, _ = q.entry(job)
            raw = {k: entry[k] for k in ('id', 'title', 'author', 'video', 'subtitles', 'subtitle_origin')}
            temp = self.root / 'receipts' / (vid + '-adopt.json')
            if not temp.exists(): immutable(temp, [raw])
            existing = self.db.execute('SELECT * FROM items WHERE id=?', (vid,)).fetchone()
            if existing and (existing['rework_seed'] or existing['revision'] > 1): raise ValueError('adopt cannot bypass a requested revision review')
            self.add(temp)
            row = self.row(vid)
            if row['archive']: return {'already_accepted': vid}
            self.accept(q, job)
        finally: q.close()
        self.recover(False); return self.status()

    def publish(self, row):
        vid = row['id']; archive = safe(row['archive'], self.root / 'accepted'); batch.verify(archive)
        library = self.root / 'library'; destination = safe(library / 'recipes' / self.key(row), self.root); durable_mkdir(destination.parent)
        marker = self.root / 'receipts' / (self.key(row) + '-publication.json')
        render_dictionary = self.root / 'receipts' / (self.key(row) + '-dictionary.json')
        if not render_dictionary.exists(): immutable(render_dictionary, batch.load(self.root / 'dictionary.json'))
        if not marker.exists():
            with tempfile.TemporaryDirectory(prefix='.publish-', dir=self.root) as tmp:
                work = Path(tmp); inputs = work / 'inputs'; inputs.mkdir(); shutil.copytree(archive, inputs / vid)
                built = work / 'output'; build_library(inputs, built, render_dictionary)
                page = built / 'recipes' / vid; files = batch.artifacts(page); record = batch.load(built / 'search-index.json')[0]
                for field in ('page', 'thumbnail'):
                    if record[field]: record[field] = record[field].replace('recipes/' + vid + '/', 'recipes/' + self.key(row) + '/', 1)
                # Intent precedes rename: publication can be resumed at either side of the rename.
                immutable(marker, {'files': files, 'record': record, 'archive_sha256': batch.digest(archive / 'checksums.json'), 'dictionary_sha256': batch.digest(render_dictionary)}); sync_dir(marker.parent)
                durable_tree(page)
                if destination.exists():
                    if batch.artifacts(destination) != files: raise ValueError('existing publication differs')
                else: page.rename(destination); sync_dir(destination.parent)
        publication = batch.load(marker)
        if publication.get('dictionary_sha256', batch.digest(render_dictionary)) != batch.digest(render_dictionary): raise ValueError('publication dictionary snapshot changed')
        if publication['archive_sha256'] != batch.digest(archive / 'checksums.json'): raise ValueError('publication archive changed')
        if not destination.exists():
            # A crash after durable intent but before rename: reproduce exactly, then compare.
            with tempfile.TemporaryDirectory(prefix='.recover-publish-', dir=self.root) as tmp:
                work = Path(tmp); inputs = work / 'inputs'; inputs.mkdir(); shutil.copytree(archive, inputs / vid)
                built = work / 'output'; build_library(inputs, built, render_dictionary); page = built / 'recipes' / vid
                if batch.artifacts(page) != publication['files']: raise ValueError('renderer changed; publication recovery requires original renderer')
                durable_tree(page); page.rename(destination); sync_dir(destination.parent)
        if batch.artifacts(destination) != publication['files']: raise ValueError('published recipe was modified')
        batch.library_module().validate(destination, batch.load(batch.CONTRACTS / 'video-recipe.schema.json'))
        self.update(vid, publication=str(marker), record=json.dumps(publication['record'], ensure_ascii=False), state='published')

    def index(self):
        records = [json.loads(r['record']) for r in self.db.execute('SELECT record FROM items WHERE record IS NOT NULL ORDER BY id')]
        if not records: return
        dictionary = batch.load(self.root / 'dictionary.json'); records = ingredients.index_records(records, dictionary); records.sort(key=lambda r: r['title'])
        inputs = batch.sha({'records': records, 'dictionary': dictionary, 'renderer': {name: batch.digest(ROOT / 'scripts' / name) for name in ('recipe-directory.html', 'recipe-directory.js', 'recipe-ingredient-search.js', 'recipe-ingredients.py')}})
        marker = self.root / 'receipts' / 'directory.json'
        if marker.is_file():
            checkpoint = batch.load(marker)
            if checkpoint['inputs_sha256'] == inputs and all((self.root / 'library' / name).is_file() and batch.digest(self.root / 'library' / name) == sha for name, sha in checkpoint['files'].items()): return
        html = ingredients.render_directory(records, self.root / 'library')
        # HTML embeds its own complete index. An interrupted JSON/HTML pair is repaired on resume.
        atomic(self.root / 'library' / 'search-index.json', records); atomic(self.root / 'library' / 'ingredient-dictionary.json', dictionary); atomic(self.root / 'library' / 'index.html', html, text=True)
        atomic(marker, {'inputs_sha256': inputs, 'files': {name: batch.digest(self.root / 'library' / name) for name in ('index.html', 'search-index.json', 'ingredient-dictionary.json')}})

    def verify_publication(self, row):
        archive = safe(row['archive'], self.root / 'accepted'); batch.verify(archive)
        publication = batch.load(safe(row['publication'], self.root)); destination = self.root / 'library' / 'recipes' / self.key(row)
        if 'dictionary_sha256' in publication:
            dictionary = safe(self.root / 'receipts' / (self.key(row) + '-dictionary.json'), self.root)
            if not dictionary.is_file() or batch.digest(dictionary) != publication['dictionary_sha256']: raise ValueError('publication dictionary snapshot changed')
        if batch.digest(archive / 'checksums.json') != publication['archive_sha256'] or batch.artifacts(destination) != publication['files']: raise ValueError('publication verification failed')
        batch.library_module().validate(destination, batch.load(batch.CONTRACTS / 'video-recipe.schema.json'))
        records = batch.load(self.root / 'library' / 'search-index.json'); expected = ingredients.index_records([publication['record']], batch.load(self.root / 'dictionary.json'))[0]
        if [r for r in records if r['id'] == row['id']] != [expected]: raise ValueError('directory index does not include the current recipe')
        html = ingredients.render_directory(records, self.root / 'library')
        if (self.root / 'library' / 'index.html').read_text() != html: raise ValueError('embedded directory index mismatch')
        return batch.load(archive / 'acceptance.json')

    def release(self, vid, execute=False):
        try: return self._release(vid, execute)
        except Exception as exc:
            self.update(vid, error=str(exc)); raise

    def _release(self, vid, execute=False):
        row = self.row(vid)
        if not row['publication']: return {'id': vid, 'eligible': False, 'reason': 'not published'}
        gate = batch.load(safe(Path(row['archive']) / 'acceptance.json', self.root / 'accepted'))
        if not gate['release_ready']: return {'id': vid, 'eligible': False, 'reason': 'open issues, missing images or OCR review; video retained'}
        accepted = self.verify_publication(row)
        if accepted.get('release_policy') != '1.0.0': raise ValueError('old release policy; retain media and rework before deletion')
        video = safe(accepted['source_video'], self.setting('config')['media_root'])
        if video.suffix.lower() not in MEDIA_SUFFIXES: raise ValueError('release requires a registered media file')
        quarantine_base = video.parent / '.recipe-release' / batch.sha(str(self.root))[:16]
        quarantine = safe(quarantine_base / (vid + video.suffix), self.setting('config')['media_root'])
        if row['state'] == 'deleted':
            if video.exists() or quarantine.exists(): raise ValueError('media reappeared after deletion; do not delete it')
            return {'id': vid, 'already_deleted': True}
        if not execute: return {'id': vid, 'eligible': True, 'video': str(video), 'sha256': accepted['video_sha256'], 'dry_run': True}
        if not row['release']:
            if batch.stamp(video) != accepted['video_stat'] or batch.digest(video) != accepted['video_sha256'] or video.stat().st_nlink != 1: raise ValueError('video identity changed; retained')
            intent = self.root / 'receipts' / (self.key(row) + '-release.json')
            if intent.exists():
                if batch.load(intent) != accepted: raise ValueError('release intent differs')
            else: immutable(intent, accepted); sync_dir(intent.parent)
            self.update(vid, release=str(intent), state='release_pending')
        elif batch.load(safe(row['release'], self.root)) != accepted: raise ValueError('release intent changed')
        # Move only this exact registered filename; no glob, recursive deletion or sidecar removal.
        durable_mkdir(quarantine.parent); quarantine.parent.chmod(0o700); sync_dir(quarantine.parent)
        parent_fd = os.open(video.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        quarantine_fd = os.open(quarantine.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            if video.exists() and quarantine.exists(): raise ValueError('both source and quarantine exist; retained')
            if video.exists():
                if batch.stamp(video) != accepted['video_stat'] or batch.digest(video) != accepted['video_sha256']: raise ValueError('video changed after release intent')
                os.rename(video.name, quarantine.name, src_dir_fd=parent_fd, dst_dir_fd=quarantine_fd); os.fsync(parent_fd); os.fsync(quarantine_fd)
            if quarantine.exists():
                st = quarantine.stat(); expected = accepted['video_stat']
                if [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns] != expected[:4] or quarantine.is_symlink() or st.st_nlink != 1 or batch.digest(quarantine) != accepted['video_sha256']: raise ValueError('quarantined identity mismatch; held without deletion')
                # Unlink the quarantined file only after independent durable outputs were checked.
                os.unlink(quarantine.name, dir_fd=quarantine_fd); os.fsync(quarantine_fd)
        finally: os.close(parent_fd); os.close(quarantine_fd)
        self.update(vid, state='deleted', error=None)
        return {'id': vid, 'deleted': str(video), 'retained': 'subtitles, frames, recipe, evidence and audit'}

    def recover(self, delete_videos=False):
        for row in self.db.execute("SELECT * FROM items WHERE archive IS NOT NULL AND state NOT IN ('deleted','failed') ORDER BY ordinal").fetchall():
            if row['state'] == 'accepted': self.publish(row)
        self.index()
        for row in self.db.execute("SELECT * FROM items WHERE publication IS NOT NULL AND state NOT IN ('failed','deleted') ORDER BY ordinal").fetchall():
            # Previously committed deletion intents are always completed, even without a new flag.
            if (row['release'] and row['state'] != 'deleted') or delete_videos: self.release(row['id'], execute=True)
        return self.status()

    def import_response(self, path):
        response = batch.load(path); task = response.get('task_id')
        if not isinstance(task, str) or not re.fullmatch('[a-f0-9]{64}', task): raise ValueError('bad task ID')
        for row in self.db.execute('SELECT * FROM items WHERE queue IS NOT NULL AND archive IS NULL').fetchall():
            directory = safe(Path(row['queue']) / 'stages' / task, self.root)
            if directory.is_dir():
                q = batch.Queue(row['queue'])
                try: result = q.import_result(path)
                finally: q.close()
                return {'id': row['id'], 'result': result, 'next': 'run next to advance'}
        raise ValueError('no active video owns that task')

    def received(self, path, sha, responses):
        if batch.digest(path) != sha: raise ValueError('response changed during import; publish response files atomically')
        accepted = responses / 'accepted'; durable_mkdir(accepted)
        target = accepted / (sha + '.json')
        if target.exists(): target = accepted / (sha + '-' + str(time.time_ns()) + '.json')
        with path.open('rb') as stream: os.fsync(stream.fileno())
        path.rename(target); sync_dir(responses); sync_dir(accepted)

    def pump(self, packets, responses, delete_videos=False, initial=True):
        packets = self.output_path(packets); responses = self.output_path(responses)
        if packets == responses or packets.is_relative_to(responses) or responses.is_relative_to(packets): raise ValueError('packet and response directories must be separate')
        durable_mkdir(packets); durable_mkdir(responses)
        accepted = 0; rejected = []
        for path in sorted(responses.glob('*.json')):
            safe(path, responses)
            if not path.is_file(): continue
            sha = batch.digest(path)
            old = self.db.execute('SELECT state,error FROM deliveries WHERE sha=?', (sha,)).fetchone()
            if old and old['state'] == 'rejected':
                rejected.append({'file': str(path), 'error': old['error']}); continue
            if not old:
                try:
                    self.import_response(path)
                except Exception as exc:
                    with self.db: self.db.execute('INSERT OR REPLACE INTO deliveries VALUES(?,?,?,?)', (sha, str(path), 'rejected', str(exc)))
                    rejected.append({'file': str(path), 'error': str(exc)}); continue
                with self.db: self.db.execute('INSERT INTO deliveries VALUES(?,?,?,NULL)', (sha, str(path), 'accepted'))
            # The imported result is immutable. Archival failures must never revoke acceptance.
            try:
                self.received(path, sha, responses)
                with self.db: self.db.execute('UPDATE deliveries SET error=NULL WHERE sha=?', (sha,))
                if not old or old['error']: accepted += 1
            except Exception as exc:
                with self.db: self.db.execute('UPDATE deliveries SET error=? WHERE sha=?', (str(exc), sha))
                rejected.append({'file': str(path), 'error': 'accepted response archival failed: ' + str(exc)})
        if rejected:
            return {'paused': 'response files need correction or archival retry; rerun after resolving the error', 'rejected': rejected, 'status': self.status()}
        waiting = self.db.execute("SELECT * FROM items WHERE state LIKE 'waiting_%' AND archive IS NULL ORDER BY ordinal LIMIT 1").fetchone()
        if initial or accepted or not waiting:
            result = self.next(delete_videos)
        else:
            result = self.status()
        row = self.db.execute("SELECT * FROM items WHERE state LIKE 'waiting_%' AND archive IS NULL ORDER BY ordinal LIMIT 1").fetchone()
        cached = packets / 'current.json'
        if not initial and not accepted and row and cached.is_file():
            current = batch.load(cached)
            if current.get('video_id') == row['id'] and current.get('revision') == row['revision'] and current.get('tasks'):
                result.pop('items', None)
                return {'accepted_responses': 0, 'current': current, 'status': result}
        if row:
            q = batch.Queue(row['queue'])
            try:
                job = q.db.execute('SELECT * FROM jobs WHERE id=?', (row['id'],)).fetchone()
                keys = [key for key in q.active_keys(job) if q.db.execute('SELECT status FROM tasks WHERE key=?', (key,)).fetchone()['status'] == 'waiting']
                folder = packets / batch.sha(sorted(keys))
                if not folder.exists(): q.export(folder)
                jobs = []
                for key in sorted(keys):
                    task_folder = folder / key; batch.verify(task_folder); packet = batch.load(task_folder / 'packet.json')
                    jobs.append({'task_id': key, 'stage': packet['stage'], 'folder': str(task_folder), 'images': len(packet['image_inputs'])})
                current = {'video_id': row['id'], 'revision': row['revision'], 'response_directory': str(responses), 'tasks': jobs}
                marker = packets / 'current.json'
                if not marker.exists() or batch.load(marker) != current: atomic(marker, current)
            finally: q.close()
        else:
            current = {'video_id': None, 'tasks': [], 'response_directory': str(responses)}
            marker = packets / 'current.json'
            if not marker.exists() or batch.load(marker) != current: atomic(marker, current)
        result.pop('items', None)
        return {'accepted_responses': accepted, 'current': current, 'status': result}

    def run(self, packets, responses, delete_videos=False, watch=False, poll_seconds=10):
        if not batch.finite(poll_seconds) or poll_seconds < 1: raise ValueError('poll interval must be finite and at least one second')
        initial = True; last = None
        while True:
            result = self.pump(packets, responses, delete_videos, initial)
            initial = False
            if result != last:
                print(json.dumps(result, ensure_ascii=False), flush=True); last = result
            if not watch or result.get('paused') or result['status'].get('paused'): return result
            if result['current']['tasks']:
                time.sleep(poll_seconds); continue
            # Ready publication may just have finished. Advance to the next queued item.
            if self.db.execute("SELECT 1 FROM items WHERE archive IS NULL AND state != 'failed'").fetchone(): continue
            return result

    def output_path(self, destination):
        destination = safe(destination, destination)
        if destination == self.root or any(destination.is_relative_to(self.root / name) for name in ('accepted', 'queues', 'receipts', 'library', 'media', 'logs', 'quarantine')):
            raise ValueError('output cannot enter protected workflow data')
        return destination

    def export(self, destination):
        destination = self.output_path(destination)
        row = self.db.execute("SELECT * FROM items WHERE archive IS NULL AND queue IS NOT NULL AND state != 'failed' ORDER BY ordinal LIMIT 1").fetchone()
        if not row: raise ValueError('no pending AI task')
        q = batch.Queue(row['queue'])
        try: return q.export(destination)
        finally: q.close()

    def rebuild(self, destination):
        destination = self.output_path(destination)
        with tempfile.TemporaryDirectory(prefix='.rebuild-', dir=self.root) as tmp:
            inputs = Path(tmp)
            for row in self.db.execute('SELECT * FROM items WHERE archive IS NOT NULL OR previous_archive IS NOT NULL ORDER BY id'):
                archive = safe(row['archive'] or row['previous_archive'], self.root / 'accepted'); batch.verify(archive); shutil.copytree(archive, inputs / row['id'])
            build_library(inputs, destination, self.root / 'dictionary.json')
        return {'output': str(destination), 'requires_video': False}

    def inventory(self, destination):
        with tempfile.TemporaryDirectory(prefix='.inventory-', dir=self.root) as tmp:
            inputs = Path(tmp)
            for row in self.db.execute('SELECT * FROM items WHERE archive IS NOT NULL OR previous_archive IS NOT NULL ORDER BY id'):
                archive = safe(row['archive'] or row['previous_archive'], self.root / 'accepted'); batch.verify(archive); shutil.copytree(archive, inputs / row['id'])
            records = ingredients.input_records(inputs)
        dictionary = batch.load(self.root / 'dictionary.json'); inventory = ingredients.collect_records(records, dictionary)
        destination = self.output_path(destination); destination.mkdir(exist_ok=False)
        for name, value in [('inventory.json', inventory), ('packet.json', ingredients.review_packet(inventory, dictionary)), ('dictionary.json', dictionary)]: immutable(destination / name, value)
        return {'output': str(destination), 'names': len(inventory['entries']), 'recipe_count': len(records)}

    def prepare_revision(self, vid, proposal, destination, processor):
        """Validate an additive content proposal and create an explicitly unreviewed seed."""
        row = self.row(vid)
        if not row['archive'] or row['release'] or row['state'] == 'deleted': raise ValueError('revision proposal requires retained archived source')
        archive = safe(row['archive'], self.root / 'accepted'); batch.verify(archive)
        old = batch.load(archive / 'recipe.internal.json'); candidate = batch.load(safe(proposal, proposal))
        batch.schema('extract').validate(candidate)
        for name in ('schema_version', 'recipe_id', 'title', 'source', 'coverage', 'covered_intervals', 'human_reviewed', 'frames', 'image_reviews', 'runs'):
            if candidate[name] != old[name]: raise ValueError('proposal cannot change provenance or review history: ' + name)
        _, old_ids = batch.objects(old); _, candidate_ids = batch.objects(candidate)
        if not old_ids.keys() <= candidate_ids.keys(): raise ValueError('proposal cannot remove historical IDs')
        for name in ('evidence', 'issues'):
            originals = {item['id']: item for item in old[name]}
            for item in candidate[name]:
                if item['id'] in originals and item != originals[item['id']]: raise ValueError('proposal cannot overwrite evidence or issue history')
                if name == 'issues' and item['id'] not in originals and item['resolution'] != 'open': raise ValueError('proposal cannot certify new issues')
        # Facts remain attached to their original step/variant; relationships may be corrected.
        for name in ('steps', 'variants'):
            original = {item['id']: item for item in old[name]}
            if not original.keys() <= {item['id'] for item in candidate[name]}: raise ValueError('proposal removed a step or variant')
            for item in candidate[name]:
                if item['id'] in original and not {x['id'] for x in original[item['id']]['facts']} <= {x['id'] for x in item['facts']}:
                    raise ValueError('proposal cannot relocate historical facts')
        facts, _ = batch.objects(candidate); changed = []
        for item in candidate['ingredients'] + facts:
            previous = old_ids.get(item['id'])
            if previous is None or {k: v for k, v in item.items() if k != 'review_status'} != {k: v for k, v in previous.items() if k != 'review_status'}:
                item['review_status'] = 'needs_review'; changed.append(item['id'])
            else: item['review_status'] = previous['review_status']
        for step in candidate['steps']:
            previous = old_ids.get(step['id'])
            if previous and (step['selected_frame_id'] != previous['selected_frame_id'] or step['no_image_reason'] != previous['no_image_reason']):
                raise ValueError('proposal cannot select or remove images')
            selected = step['selected_frame_id']
            if selected:
                frame = candidate_ids[selected]
                if not any(max(0, w['start'] - 5) <= frame['timestamp'] <= w['end'] + 5 for w in step['evidence_windows']):
                    step['selected_frame_id'] = None; step['no_image_reason'] = '修订后取图窗口变化，待按新窗口重新核对候选图。'
                    candidate['issues'].append({'id': 'issue_revision_image_' + str(row['revision'] + 1) + '_' + step['id'], 'code': 'missing_image', 'target_ids': [step['id']], 'description': step['no_image_reason'], 'evidence_ids': [], 'resolution': 'open', 'resolution_note': None})
        candidate['status'] = 'needs_review'
        for item in candidate['ingredients'] + facts:
            if item['review_status'] == 'needs_review' and not any(issue['resolution'] == 'open' and item['id'] in issue['target_ids'] for issue in candidate['issues']):
                key = 'issue_revision_pending_' + str(row['revision'] + 1) + '_' + item['id']; suffix = 0
                while any(issue['id'] == key for issue in candidate['issues']):
                    suffix += 1; key = 'issue_revision_pending_' + str(row['revision'] + 1) + '_' + item['id'] + '_' + str(suffix)
                candidate['issues'].append({'id': key, 'code': 'other', 'target_ids': [item['id']], 'description': '修订项证据仍需独立核对，历史问题结论保留。', 'evidence_ids': item['evidence_ids'], 'resolution': 'open', 'resolution_note': None})
        if not any(item['resolution'] == 'open' for item in candidate['issues']):
            candidate['issues'].append({'id': 'issue_revision_review_' + str(row['revision'] + 1), 'code': 'other', 'target_ids': [step['id'] for step in candidate['steps']], 'description': '修订准备不是独立审阅；新版本仍须独立文字和视觉复核。', 'evidence_ids': [], 'resolution': 'open', 'resolution_note': None})
        transcript = batch.load(archive / 'transcript.json'); batch.validate_text(candidate, old['source'], transcript, extraction=False)
        destination = self.output_path(destination)
        if destination.exists(): raise ValueError('revision destination already exists')
        durable_mkdir(destination.parent)
        audit = {'method': 'unreviewed-additive-revision-proposal', 'processor': processor, 'model': None, 'source_archive': str(archive), 'source_checksums_sha256': batch.digest(archive / 'checksums.json'), 'proposal_sha256': batch.digest(proposal), 'changed_or_new_items': changed, 'proposal': batch.load(proposal), 'requires_independent_review': True}
        if not isinstance(processor, str) or not processor.strip(): raise ValueError('actual proposal processor required')
        with tempfile.TemporaryDirectory(prefix='.revision-', dir=destination.parent) as tmp:
            draft = Path(tmp) / 'seed'; shutil.copytree(archive, draft)
            for name in ('checksums.json', 'acceptance.json'): (draft / name).unlink(missing_ok=True)
            audit_file = draft / 'revision-proposal.json'; atomic(audit_file, audit)
            audit_sha = batch.digest(audit_file); shutil.copyfile(audit_file, draft / ('stage-input-' + audit_sha + '.json'))
            candidate['runs'].append({'stage': 'repair', 'processor': processor, 'model': None, 'prompt_version': 'revision-seed-1.0.0', 'input_sha256': audit_sha})
            # A preparation receipt is not an AI judgment. Preserve prior verdicts only for unchanged items.
            semantic = {'stage': 'review', 'fact_reviews': [{'fact_id': item['id'], 'verdict': item['review_status'], 'reason': 'Revision preparation only; changed facts await independent review; unchanged verdict retained from archive.', 'evidence_ids': item['evidence_ids']} for item in facts], 'ingredient_reviews': [{'ingredient_id': item['id'], 'verdict': item['review_status'], 'reason': 'Revision preparation only; changed ingredients await independent review; unchanged verdict retained from archive.', 'evidence_ids': item['evidence_ids']} for item in candidate['ingredients']], 'issue_reviews': [{'issue_id': item['id'], 'resolution': item['resolution'], 'reason': item['resolution_note'] or 'Historical or new issue retained for independent review.', 'evidence_ids': item['evidence_ids']} for item in candidate['issues']], 'repair_requests': [], 'issues': []}
            selections = batch.load(draft / 'image-selection.json')
            for selection in selections:
                step = next(item for item in candidate['steps'] if item['id'] == selection['step_id'])
                selection['selected_frame_id'] = step['selected_frame_id']; selection['no_image_reason'] = step['no_image_reason']
            atomic(draft / 'recipe.internal.json', candidate); atomic(draft / 'semantic-review.json', semantic); atomic(draft / 'image-selection.json', selections)
            if batch.load(draft/'processing.json').get('media_mode') == 'clips':
                media = batch.library_module().clips_module(); manifest = batch.load(draft/'step-clips.json')
                expected = [(s['id'],w['start'],w['end']) for s in candidate['steps'] for w in media.windows(s,candidate['source']['duration_seconds'],manifest['padding_seconds'],candidate['evidence'])]
                actual = [(c['step_id'],c['start'],c['end']) for c in manifest['clips']]
                if expected != actual:
                    accepted = batch.load(archive/'acceptance.json'); video = safe(accepted['source_video'],self.setting('config')['media_root'])
                    if batch.stamp(video)!=accepted['video_stat'] or batch.digest(video)!=accepted['video_sha256']:raise ValueError('source changed; cannot regenerate revision clips')
                    shutil.rmtree(draft/'clips')  # Only this owned temporary draft, never the archive.
                    media.build(video,accepted['video_sha256'],candidate,draft,manifest['padding_seconds'],manifest['width'])
                    if batch.stamp(video)!=accepted['video_stat']:raise ValueError('source changed while regenerating clips')
            batch.library_module().validate(draft, batch.load(batch.CONTRACTS / 'video-recipe.schema.json'))
            immutable(draft / 'checksums.json', batch.artifacts(draft)); durable_tree(draft); draft.rename(destination); sync_dir(destination.parent)
        return {'id': vid, 'seed': str(destination), 'changed_or_new_items': changed, 'requires_independent_review': True}

    def rework(self, vid, seed=None):
        row = self.row(vid)
        if not row['archive'] or row['release'] or row['state'] == 'deleted': raise ValueError('rework requires retained media and no committed deletion intent')
        archive = safe(row['archive'], self.root / 'accepted'); batch.verify(archive)
        accepted = batch.load(archive / 'acceptance.json'); video = batch.file(safe(accepted['source_video'], accepted['source_video']))
        if batch.stamp(video) != accepted['video_stat'] or batch.digest(video) != accepted['video_sha256']: raise ValueError('retained source changed')
        seed = safe(seed or archive, seed or archive)
        data = batch.library_module().validate(seed, batch.load(batch.CONTRACTS / 'video-recipe.schema.json'))
        if data['source']['video_id'] != vid or data['source']['transcript_sha256'] != batch.digest(archive / 'source.srt'): raise ValueError('rework seed source mismatch')
        # Keep the old page/index usable during review; the new version has distinct immutable paths.
        self.update(vid, revision=row['revision'] + 1, previous_archive=row['archive'], archive=None, publication=None, queue=None, release=None, rework_seed=str(seed), state='queued', error=None)
        return {'id': vid, 'revision': self.row(vid)['revision'], 'next': 'next resumes independent review; previous version retained'}

    def apply_vocabulary(self, packet, review):
        packet = Path(packet); dictionary = batch.load(self.root / 'dictionary.json'); inventory = batch.load(packet / 'inventory.json')
        with tempfile.TemporaryDirectory(prefix='.current-vocabulary-', dir=self.root) as tmp:
            inputs = Path(tmp)
            for row in self.db.execute('SELECT * FROM items WHERE archive IS NOT NULL OR previous_archive IS NOT NULL ORDER BY id'):
                archive = safe(row['archive'] or row['previous_archive'], self.root / 'accepted'); batch.verify(archive); shutil.copytree(archive, inputs / row['id'])
            current = ingredients.collect_records(ingredients.input_records(inputs), dictionary)
        if inventory != current: raise ValueError('stale inventory; regenerate full ingredient review packet')
        result = ingredients.apply_review(dictionary, inventory, batch.load(review))
        audit = self.root / 'receipts' / ('vocabulary-' + ingredients.fingerprint(result) + '.json')
        if not audit.exists(): immutable(audit, {'inventory': inventory, 'review': batch.load(review), 'dictionary': result})
        atomic(self.root / 'dictionary.json', result); self.index()
        return {'dictionary_revision': result['revision'], 'authority_source': 'workflow dictionary; synchronize repository vocabulary separately after review'}

    def retry(self, vid):
        row = self.row(vid)
        if row['state'] != 'failed': raise ValueError('only failed items may be retried')
        if row['release']: self.update(vid, state='release_pending', error=None)
        elif row['archive']: self.update(vid, state='accepted' if not row['publication'] else 'published', error=None)
        else:
            if row['queue']:
                q = batch.Queue(row['queue'])
                try: q.retry(vid)
                finally: q.close()
            self.update(vid, state='queued', error=None)

    def status(self):
        revision = 'revision' if 'revision' in {r[1] for r in self.db.execute('PRAGMA table_info(items)')} else '1 AS revision'
        rows = [dict(r) for r in self.db.execute('SELECT id,' + revision + ',state,error FROM items ORDER BY ordinal')]; counts = {}
        for row in rows: counts[row['state']] = counts.get(row['state'], 0) + 1
        pending = next((r for r in rows if r['state'].startswith('waiting_')), None)
        return {'root': str(self.root), 'total': len(rows), 'counts': counts, 'waiting': pending, 'items': rows, 'note': 'AI tasks need this session or a configured model; ready outputs only can release video'}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--root', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--media-mode', choices=['clips','images'], default='clips'); init.add_argument('--media-root', type=Path); init.add_argument('--browser'); init.add_argument('--max-retained', type=int, default=3); init.add_argument('--min-free-gib', type=float, default=5)
    serve = sub.add_parser('serve'); serve.add_argument('--port',type=int,default=8765)
    add = sub.add_parser('add'); add.add_argument('manifest', type=Path)
    next_ = sub.add_parser('next'); next_.add_argument('--delete-videos', action='store_true')
    run = sub.add_parser('run'); run.add_argument('--packets', type=Path); run.add_argument('--responses', type=Path); run.add_argument('--delete-videos', action='store_true'); run.add_argument('--watch', action='store_true'); run.add_argument('--poll-seconds', type=float, default=10)
    status = sub.add_parser('status'); status.add_argument('--summary', action='store_true')
    export = sub.add_parser('export'); export.add_argument('destination', type=Path)
    imp = sub.add_parser('import'); imp.add_argument('response', type=Path)
    adopt = sub.add_parser('adopt'); adopt.add_argument('--queue', type=Path, required=True); adopt.add_argument('--job', required=True)
    recover = sub.add_parser('resume'); recover.add_argument('--delete-videos', action='store_true')
    release = sub.add_parser('release'); release.add_argument('--job', required=True); release.add_argument('--execute', action='store_true')
    rebuild = sub.add_parser('rebuild'); rebuild.add_argument('destination', type=Path)
    inventory = sub.add_parser('inventory'); inventory.add_argument('destination', type=Path)
    preparation = sub.add_parser('prepare-revision'); preparation.add_argument('--job', required=True); preparation.add_argument('--proposal', type=Path, required=True); preparation.add_argument('--output', type=Path, required=True); preparation.add_argument('--processor', required=True)
    rework = sub.add_parser('rework'); rework.add_argument('--job', required=True); rework.add_argument('--seed', type=Path)
    vocabulary = sub.add_parser('apply-vocabulary'); vocabulary.add_argument('--packet', type=Path, required=True); vocabulary.add_argument('--review', type=Path, required=True)
    retry = sub.add_parser('retry'); retry.add_argument('--job', required=True)
    args = parser.parse_args()
    if args.command == 'serve':
        module('recipe-media-server').serve(args.root,args.port); return
    flow = Flow(args.root, read_only=args.command == 'status')
    try:
        if args.command == 'init': flow.init(args.media_root, args.browser, args.max_retained, args.min_free_gib, media_mode=args.media_mode); result = flow.status()
        elif args.command == 'add': result = flow.add(args.manifest)
        elif args.command == 'run':
            flow.run(args.packets or args.root / 'task-packages', args.responses or args.root / 'responses', args.delete_videos, args.watch, args.poll_seconds); return
        elif args.command == 'next': result = flow.next(args.delete_videos)
        elif args.command == 'resume': result = flow.recover(args.delete_videos)
        elif args.command == 'adopt': result = flow.adopt(args.queue, args.job)
        elif args.command == 'export': result = flow.export(args.destination)
        elif args.command == 'import': result = flow.import_response(args.response)
        elif args.command == 'release': result = flow.release(args.job, args.execute)
        elif args.command == 'rebuild': result = flow.rebuild(args.destination)
        elif args.command == 'inventory': result = flow.inventory(args.destination)
        elif args.command == 'prepare-revision': result = flow.prepare_revision(args.job, args.proposal, args.output, args.processor)
        elif args.command == 'rework': result = flow.rework(args.job, args.seed)
        elif args.command == 'apply-vocabulary': result = flow.apply_vocabulary(args.packet, args.review)
        elif args.command == 'retry': flow.retry(args.job); result = flow.status()
        else: result = flow.status()
        if args.command == 'status' and args.summary: result.pop('items', None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally: flow.close()


if __name__ == '__main__': main()
