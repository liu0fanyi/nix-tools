"""Lifecycle safety/recovery checks with owned synthetic media; no network or AI calls."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
from jsonschema import ValidationError

import test_recipe_batch as fixtures

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('flow', ROOT / 'recipe-flow.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)


class PowerLoss(BaseException):
    """Bypass ordinary failure handling to simulate a process disappearing."""


class FlowChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.BatchChecks.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.BatchChecks.tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.media = self.root / 'owned'; self.media.mkdir()
        self.video = self.media / 'source.mp4'
        shutil.copyfile(fixtures.BatchChecks.video, self.video)
        self.srt = self.media / 'source.srt'
        self.srt.write_text('1\n00:00:00,000 --> 00:00:02,000\n豆腐翻炒\n', encoding='utf-8')
        self.config = {'width': 160, 'candidates': 2, 'interval': 1, 'padding': 0, 'strategy': 'bounded-uniform-per-window'}
        self.flow = f.Flow(self.root / 'flow')
        self.flow.init(self.media, min_free_gib=0, sampling=self.config)
        self.entry = {'id': 'BVTest123', 'title': '合成测试', 'author': 'test', 'video': str(self.video), 'subtitles': str(self.srt), 'subtitle_origin': 'platform'}
        self.manifest = self.root / 'manifest.json'; f.batch.write(self.manifest, [self.entry])
        self.flow.add(self.manifest)
        self.helper = fixtures.BatchChecks(); self.helper.root = self.root

    def tearDown(self):
        self.flow.close(); self.temp.cleanup()

    def reopen(self):
        self.flow.close(); self.flow = f.Flow(self.root / 'flow')

    def pending(self, stage):
        row = self.flow.row('BVTest123')
        q = f.batch.Queue(row['queue'], read_only=True)
        try:
            task = q.db.execute("SELECT * FROM tasks WHERE stage=? AND status='waiting'", (stage,)).fetchone()
            self.assertIsNotNone(task)
            return q.folder(task['key'])
        finally: q.close()

    def send(self, folder, result):
        packet = f.batch.load(folder / 'packet.json')
        env = {'task_id': packet['task_id'], 'input_sha256': packet['input_sha256'], 'processor': 'synthetic-flow-test', 'model': None, 'result': result}
        path = self.root / ('response-' + str(len(list(self.root.glob('response-*')))) + '.json')
        f.batch.write(path, env)
        return self.flow.import_response(path)

    def stages(self, ready=True):
        self.flow.next(); folder = self.pending('extract')
        draft = self.helper.draft(folder)
        self.send(folder, draft)
        self.flow.next(); folder = self.pending('review')
        recipe = f.batch.load(folder / 'payload.json')['recipe']
        verdict = 'supported' if ready else 'needs_review'
        self.send(folder, {'stage': 'review', 'fact_reviews': [{'fact_id': 'fact_one', 'verdict': verdict, 'reason': 'Synthetic subtitle only; not culinary evaluation', 'evidence_ids': ['ev_one']}], 'ingredient_reviews': [{'ingredient_id': 'ing_tofu', 'verdict': verdict, 'reason': 'Synthetic tofu subtitle fixture', 'evidence_ids': ['ev_one']}], 'issue_reviews': [{'issue_id': i['id'], 'resolution': 'resolved' if ready else 'open', 'reason': 'Synthetic fixture evidence', 'evidence_ids': ['ev_one']} for i in recipe['issues']], 'repair_requests': [], 'issues': []})
        self.flow.next(); folder = self.pending('select_step_one')
        self.send(folder, self.helper.selection(folder))

    def published(self, ready=True):
        self.stages(ready); self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'published')
        return Path(self.flow.row('BVTest123')['archive'])

    def test_ready_release_defaults_to_preview_and_rebuild_without_video(self):
        archive = self.published()
        dry = self.flow.release('BVTest123')
        self.assertTrue(dry['eligible']); self.assertTrue(dry['dry_run']); self.assertTrue(self.video.exists())
        before = f.batch.artifacts(archive)
        self.assertTrue(self.flow.release('BVTest123', execute=True)['deleted'])
        self.assertFalse(self.video.exists()); self.assertTrue(self.srt.exists())
        self.assertEqual(f.batch.artifacts(archive), before)
        self.reopen(); self.flow.recover()
        output = self.root / 'rebuilt'; self.flow.rebuild(output)
        recipe = f.batch.library_module().validate(output / 'recipes/BVTest123', f.batch.load(f.batch.CONTRACTS / 'video-recipe.schema.json'))
        self.assertEqual(recipe['status'], 'ready'); self.assertFalse(recipe['human_reviewed'])
        self.assertTrue((output / 'index.html').exists())
        self.assertTrue(self.flow.release('BVTest123', execute=True)['already_deleted'])

    def test_needs_review_keeps_media_even_with_delete_enabled(self):
        self.published(ready=False)
        self.flow.recover(delete_videos=True)
        result = self.flow.release('BVTest123', execute=True)
        self.assertFalse(result['eligible']); self.assertTrue(self.video.exists()); self.assertTrue(self.srt.exists())
        self.assertFalse((self.flow.root / 'receipts/BVTest123-release.json').exists())

    def test_publication_intent_crash_before_rename_recovers(self):
        self.stages()
        real = Path.rename
        destination = self.flow.root / 'library/recipes/BVTest123'
        def crash(path, target):
            if Path(target) == destination: raise PowerLoss('before publication rename')
            return real(path, target)
        with mock.patch.object(Path, 'rename', crash):
            with self.assertRaises(PowerLoss): self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'accepted')
        self.assertTrue((self.flow.root / 'receipts/BVTest123-publication.json').exists())
        self.assertFalse(destination.exists()); self.assertTrue(self.video.exists())
        self.reopen(); self.flow.recover()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'published')
        self.assertTrue(self.flow.release('BVTest123')['eligible'])

    def test_quarantine_crash_recovers_committed_intent_without_new_delete_flag(self):
        self.published(); real = f.os.unlink
        def crash(path, *args, **kwargs):
            if str(path) == 'BVTest123.mp4' and 'dir_fd' in kwargs: raise PowerLoss('after quarantine rename')
            return real(path, *args, **kwargs)
        with mock.patch.object(f.os, 'unlink', side_effect=crash):
            with self.assertRaises(PowerLoss): self.flow.release('BVTest123', execute=True)
        self.assertFalse(self.video.exists()); self.assertTrue((self.media / '.recipe-release' / f.batch.sha(str(self.flow.root))[:16] / 'BVTest123.mp4').exists())
        self.assertEqual(self.flow.row('BVTest123')['state'], 'release_pending')
        self.reopen(); self.flow.recover()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'deleted')
        self.assertFalse((self.media / '.recipe-release' / f.batch.sha(str(self.flow.root))[:16] / 'BVTest123.mp4').exists()); self.assertTrue(self.srt.exists())

    def test_unlink_crash_recovers_without_repeating_ai_or_deleting_reappeared_media(self):
        self.published(); real = self.flow.update
        def crash(vid, **values):
            if values.get('state') == 'deleted': raise PowerLoss('after unlink')
            return real(vid, **values)
        with mock.patch.object(self.flow, 'update', side_effect=crash):
            with self.assertRaises(PowerLoss): self.flow.release('BVTest123', execute=True)
        self.assertFalse(self.video.exists()); self.assertEqual(self.flow.row('BVTest123')['state'], 'release_pending')
        self.reopen()
        with mock.patch.object(f.batch.Queue, 'run', side_effect=AssertionError('completed media must not reprocess')):
            self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'deleted')
        self.video.write_bytes(b'new media must survive')
        with self.assertRaisesRegex(ValueError, 'media reappeared'): self.flow.release('BVTest123', execute=True)
        self.assertEqual(self.video.read_bytes(), b'new media must survive')

    def test_source_modification_after_publication_blocks_release(self):
        self.published(); self.video.write_bytes(self.video.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'identity changed'): self.flow.release('BVTest123', execute=True)
        self.assertTrue(self.video.exists()); self.assertFalse((self.media / '.recipe-release' / f.batch.sha(str(self.flow.root))[:16] / 'BVTest123.mp4').exists())

    def test_linked_source_and_ancestor_paths_are_rejected(self):
        self.published(); original = self.media / 'saved.mp4'; self.video.rename(original); self.video.symlink_to(original)
        with self.assertRaisesRegex(ValueError, 'linked path'): self.flow.release('BVTest123', execute=True)
        self.assertTrue(original.exists()); self.assertTrue(self.video.is_symlink())
        link = self.root / 'linked-root'; link.symlink_to(self.media, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'linked path'): f.safe(link / 'saved.mp4', link)
        with self.assertRaisesRegex(ValueError, 'linked path'): f.Flow(link / 'state')

    def test_hardlinked_source_is_retained(self):
        self.published()
        extra = self.media / 'second-name.mp4'; f.os.link(self.video, extra)
        with self.assertRaisesRegex(ValueError, 'identity changed'): self.flow.release('BVTest123', execute=True)
        self.assertTrue(self.video.exists()); self.assertTrue(extra.exists())
        self.assertFalse((self.flow.root / 'receipts/BVTest123-release.json').exists())

    def test_quarantined_content_change_is_retained_on_resume(self):
        self.published(); real = f.os.unlink
        def crash(path, *args, **kwargs):
            if str(path) == 'BVTest123.mp4' and 'dir_fd' in kwargs: raise PowerLoss('before unlink')
            return real(path, *args, **kwargs)
        with mock.patch.object(f.os, 'unlink', side_effect=crash):
            with self.assertRaises(PowerLoss): self.flow.release('BVTest123', execute=True)
        quarantined = self.media / '.recipe-release' / f.batch.sha(str(self.flow.root))[:16] / 'BVTest123.mp4'
        quarantined.write_bytes(b'replaced quarantine data')
        self.reopen()
        with self.assertRaisesRegex(ValueError, 'quarantined identity mismatch'): self.flow.recover()
        self.assertEqual(quarantined.read_bytes(), b'replaced quarantine data')
        self.assertEqual(self.flow.row('BVTest123')['state'], 'release_pending')
        self.assertTrue(self.srt.exists())

    def test_registered_external_video_cannot_be_released(self):
        outside = self.root / 'external.mp4'; shutil.copyfile(self.video, outside)
        other = f.Flow(self.root / 'outside-flow')
        try:
            other.init(self.media, min_free_gib=0, sampling=self.config)
            manifest = self.root / 'outside.json'; f.batch.write(manifest, [{**self.entry, 'video': str(outside)}]); other.add(manifest)
            previous = self.flow; self.flow = other
            try:
                self.published()
                with self.assertRaisesRegex(ValueError, 'outside declared root'): other.release('BVTest123', execute=True)
            finally: self.flow = previous
            self.assertTrue(outside.exists())
        finally: other.close()

    def test_corrupt_directory_or_recipe_preserves_video(self):
        self.published()
        index = self.flow.root / 'library/index.html'; original = index.read_bytes(); index.write_bytes(b'wrong index')
        with self.assertRaisesRegex(ValueError, 'embedded directory index mismatch'): self.flow.release('BVTest123', execute=True)
        self.assertTrue(self.video.exists()); index.write_bytes(original)
        page = self.flow.root / 'library/recipes/BVTest123/recipe.html'; page.write_text('modified')
        with self.assertRaisesRegex(ValueError, 'publication verification failed'): self.flow.release('BVTest123', execute=True)
        self.assertTrue(self.video.exists())

    def test_ocr_review_flag_prevents_release_of_otherwise_ready_output(self):
        other = f.Flow(self.root / 'ocr-flow')
        try:
            other.init(self.media, min_free_gib=0, sampling=self.config)
            manifest = self.root / 'ocr.json'; f.batch.write(manifest, [{**self.entry, 'subtitle_origin': 'ocr'}]); other.add(manifest)
            report = self.video.with_suffix('.ocr.json')
            f.batch.write(report, {'source': str(self.video), 'srt_sha256': f.batch.digest(self.srt), 'status': 'review', 'flags': ['low confidence'], 'settings': {'duration': None}})
            previous = self.flow; self.flow = other
            try:
                archive = self.published()
                self.assertTrue(f.batch.load(archive / 'acceptance.json')['ocr_review_pending'])
                self.assertFalse(other.release('BVTest123', execute=True)['eligible'])
            finally: self.flow = previous
            self.assertTrue(self.video.exists())
        finally: other.close()

    def test_missing_ocr_report_retains_ready_media(self):
        other = f.Flow(self.root / 'no-report-flow')
        try:
            other.init(self.media, min_free_gib=0, sampling=self.config)
            manifest = self.root / 'no-report.json'; f.batch.write(manifest, [{**self.entry, 'subtitle_origin': 'ocr'}]); other.add(manifest)
            self.assertFalse(self.video.with_suffix('.ocr.json').exists())
            previous = self.flow; self.flow = other
            try:
                archive = self.published()
                self.assertTrue(f.batch.load(archive / 'acceptance.json')['ocr_review_pending'])
                self.assertFalse(other.release('BVTest123', execute=True)['eligible'])
            finally: self.flow = previous
            self.assertTrue(self.video.exists())
        finally: other.close()

    def test_failed_started_video_occupies_capacity_retry_preserves_slot(self):
        manifest = self.root / 'later.json'; f.batch.write(manifest, [{'id': 'BVLater1', 'title': 'later', 'author': 'test'}]); self.flow.add(manifest)
        config = self.flow.setting('config'); config['max_retained'] = 1
        with mock.patch.object(self.flow, 'setting', return_value=config):
            with mock.patch.object(self.flow, 'inputs', side_effect=ValueError('synthetic OCR failure')):
                with self.assertRaisesRegex(ValueError, 'synthetic OCR failure'): self.flow.next()
            self.assertEqual(self.flow.row('BVTest123')['state'], 'failed')
            self.assertEqual(self.flow.retain_count(), 1)
            with mock.patch.object(self.flow, 'inputs', side_effect=AssertionError('failed source consumes capacity')):
                self.assertEqual(self.flow.next()['paused'], 'retained-video limit')
            self.flow.retry('BVTest123'); self.assertEqual(self.flow.retain_count(), 1)
            self.flow.next()
            self.assertEqual(self.flow.row('BVTest123')['state'], 'waiting_extract')
            self.assertEqual(self.flow.row('BVLater1')['state'], 'queued')
        self.assertTrue(self.video.exists())

    def test_full_capacity_does_not_block_active_ai_pipeline(self):
        config = self.flow.setting('config'); config['max_retained'] = 1
        with mock.patch.object(self.flow, 'setting', return_value=config):
            self.flow.next(); self.assertEqual(self.flow.retain_count(), 1)
            self.published()
            self.assertTrue(self.flow.release('BVTest123')['eligible'])
        self.assertTrue(self.video.exists())

    def test_interrupted_atomic_publication_intent_leaves_no_partial_json(self):
        self.stages(); marker = self.flow.root / 'receipts/BVTest123-publication.json'; real = f.os.link
        def crash(source, destination, *args, **kwargs):
            if Path(destination) == marker: raise PowerLoss('before intent commit')
            return real(source, destination, *args, **kwargs)
        with mock.patch.object(f.os, 'link', side_effect=crash):
            with self.assertRaises(PowerLoss): self.flow.next()
        self.assertFalse(marker.exists()); self.assertEqual(self.flow.row('BVTest123')['state'], 'accepted')
        self.assertEqual(list(marker.parent.glob('.writing-*')), [])
        self.assertTrue(self.video.exists()); self.reopen(); self.flow.recover()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'published')
        self.assertIsInstance(f.batch.load(marker)['files'], dict)

    def test_interrupted_atomic_release_intent_never_deletes_without_commit(self):
        self.published(); marker = self.flow.root / 'receipts/BVTest123-release.json'; real = f.os.link
        def crash(source, destination, *args, **kwargs):
            if Path(destination) == marker: raise PowerLoss('before delete intent commit')
            return real(source, destination, *args, **kwargs)
        with mock.patch.object(f.os, 'link', side_effect=crash):
            with self.assertRaises(PowerLoss): self.flow.release('BVTest123', execute=True)
        self.assertFalse(marker.exists()); self.assertFalse(self.flow.row('BVTest123')['release'])
        self.assertEqual(list(marker.parent.glob('.writing-*')), [])
        self.reopen(); self.flow.recover()
        self.assertTrue(self.video.exists()); self.assertEqual(self.flow.row('BVTest123')['state'], 'published')
        self.flow.release('BVTest123', execute=True); self.assertFalse(self.video.exists())

    def test_large_manifest_serial_resume_read_only_status_and_single_writer(self):
        entries = [self.entry] + [{'id': 'BVFlow' + str(n), 'title': 'dish ' + str(n), 'author': 'test'} for n in range(1, 4200)]
        manifest = self.root / 'large.json'; f.batch.write(manifest, entries)
        self.assertEqual(self.flow.add(manifest)['total'], 4200)
        self.assertEqual(self.flow.add(manifest)['total'], 4200)
        with self.assertRaisesRegex(ValueError, 'single writer'): f.Flow(self.flow.root)
        reader = f.Flow(self.flow.root, read_only=True)
        try:
            self.assertEqual(reader.status()['total'], 4200)
            with self.assertRaises(f.sqlite3.OperationalError): reader.db.execute("UPDATE items SET state='bad'")
        finally: reader.close()
        self.flow.next(); task = self.pending('extract'); packet = f.batch.load(task / 'packet.json')
        queues = list((self.flow.root / 'queues').iterdir()); self.assertEqual(len(queues), 1)
        self.reopen(); self.assertEqual(self.flow.status()['total'], 4200)
        self.flow.next(); self.assertEqual(f.batch.load(self.pending('extract') / 'packet.json')['task_id'], packet['task_id'])
        self.assertEqual(self.flow.status()['counts'], {'waiting_extract': 1, 'queued': 4199})
        export = self.root / 'packets'; self.flow.export(export)
        self.assertTrue((export / packet['task_id'] / 'packet.json').exists())

    def review_seed_to_publication(self):
        self.flow.next(); folder = self.pending('review')
        recipe = f.batch.load(folder / 'payload.json')['recipe']
        self.send(folder, {'stage': 'review', 'fact_reviews': [{'fact_id': fact['id'], 'verdict': 'supported', 'reason': 'Synthetic rework cue independently checked', 'evidence_ids': fact['evidence_ids']} for step in recipe['steps'] + recipe['variants'] for fact in step['facts']], 'ingredient_reviews': [{'ingredient_id': i['id'], 'verdict': 'supported', 'reason': 'Synthetic ingredient checked', 'evidence_ids': i['evidence_ids']} for i in recipe['ingredients']], 'issue_reviews': [{'issue_id': i['id'], 'resolution': 'resolved', 'reason': 'Synthetic issue checked against original cue', 'evidence_ids': ['ev_one']} for i in recipe['issues']], 'repair_requests': [], 'issues': []})
        self.flow.next(); folder = self.pending('select_step_one')
        self.send(folder, self.helper.selection(folder)); self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'published')

    def test_durable_nested_directories_sync_each_new_directory_and_parent(self):
        target = self.root / 'new' / 'nested' / 'last'
        with mock.patch.object(f, 'sync_dir', wraps=f.sync_dir) as sync:
            f.durable_mkdir(target)
        synced = [Path(c.args[0]) for c in sync.call_args_list]
        for directory in (self.root / 'new', self.root / 'new/nested', target):
            self.assertIn(directory, synced); self.assertIn(directory.parent, synced)
            self.assertTrue(directory.is_dir())
        with mock.patch.object(f, 'sync_dir') as sync:
            f.durable_mkdir(target); sync.assert_not_called()

    def test_legacy_database_migrates_started_and_revision_without_losing_rows(self):
        root = self.root / 'legacy'; root.mkdir(); db = f.sqlite3.connect(root / 'flow.sqlite3')
        db.execute('CREATE TABLE items (id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, entry TEXT NOT NULL, state TEXT NOT NULL, queue TEXT, archive TEXT, publication TEXT, record TEXT, release TEXT, error TEXT)')
        for n, (vid, state, queue) in enumerate([('BVFresh1', 'queued', None), ('BVFailed1', 'failed', None), ('BVResume1', 'queued', '/synthetic/queue')]):
            db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?)', (vid, n, json.dumps(self.entry), state, queue, None, None, None, None, None))
        db.commit(); db.close()
        migrated = f.Flow(root)
        try:
            self.assertEqual(migrated.status()['total'], 3)
            self.assertEqual(migrated.row('BVFresh1')['started'], 0)
            self.assertEqual(migrated.row('BVFailed1')['started'], 1)
            self.assertEqual(migrated.row('BVResume1')['started'], 1)
            self.assertEqual(migrated.retain_count(), 2)
            for vid in ('BVFresh1', 'BVFailed1', 'BVResume1'):
                self.assertEqual(migrated.row(vid)['revision'], 1)
                self.assertIsNone(migrated.row(vid)['previous_archive']); self.assertIsNone(migrated.row(vid)['rework_seed'])
        finally: migrated.close()
        migrated = f.Flow(root)
        try: self.assertEqual(migrated.retain_count(), 2)
        finally: migrated.close()

    def test_ocr_release_requires_fresh_complete_report_binding(self):
        st = self.video.stat()
        valid = {'tool': 'video-subtitle-ocr', 'source': str(self.video), 'signature': {'size': st.st_size, 'mtime_ns': st.st_mtime_ns}, 'srt_sha256': f.batch.digest(self.srt), 'settings': {'duration': None}, 'status': 'done', 'flags': []}
        cases = [('valid', {}, True), ('old-tool', {'tool': 'old-tool'}, False), ('wrong-source', {'source': '/wrong/source.mp4'}, False), ('old-signature', {'signature': {'size': st.st_size, 'mtime_ns': st.st_mtime_ns - 1}}, False), ('no-signature', {'signature': None}, False), ('wrong-srt', {'srt_sha256': 'f' * 64}, False), ('partial', {'settings': {'duration': 2}}, False), ('not-done', {'status': 'review'}, False), ('flagged', {'flags': ['low confidence']}, False)]
        for name, change, eligible in cases:
            with self.subTest(name=name):
                other = f.Flow(self.root / ('ocr-binding-' + name)); other.init(self.media, min_free_gib=0, sampling=self.config)
                manifest = self.root / ('ocr-binding-' + name + '.json'); f.batch.write(manifest, [{**self.entry, 'subtitle_origin': 'ocr'}]); other.add(manifest)
                self.video.with_suffix('.ocr.json').write_text(json.dumps({**valid, **change}))
                previous = self.flow; self.flow = other
                try:
                    archive = self.published()
                    acceptance = f.batch.load(archive / 'acceptance.json')
                    self.assertEqual(acceptance['ocr_review_pending'], not eligible)
                    self.assertEqual(other.release('BVTest123')['eligible'], eligible)
                    self.assertTrue(self.video.exists())
                finally: self.flow = previous; other.close()

    def test_rework_preserves_old_page_until_independent_new_revision_publishes(self):
        archive = self.published(); old_queue = self.flow.row('BVTest123')['queue']
        old_archive = f.batch.artifacts(archive); old_page = self.flow.root / 'library/recipes/BVTest123'
        before_page = f.batch.artifacts(old_page); index = self.flow.root / 'library/search-index.json'; before_index = index.read_bytes()
        result = self.flow.rework('BVTest123'); self.assertEqual(result['revision'], 2)
        self.assertEqual(self.flow.row('BVTest123')['rework_seed'], str(archive))
        self.flow.next(); self.assertEqual(self.flow.row('BVTest123')['state'], 'waiting_review')
        self.assertNotEqual(self.flow.row('BVTest123')['queue'], old_queue)
        self.assertEqual(f.batch.artifacts(old_page), before_page); self.assertEqual(index.read_bytes(), before_index)
        self.reopen(); self.review_seed_to_publication()
        row = self.flow.row('BVTest123'); self.assertNotEqual(row['archive'], str(archive)); self.assertIn('-r2', row['archive'])
        self.assertIn('recipes/BVTest123-r2/', f.batch.load(index)[0]['page'])
        self.assertEqual(f.batch.artifacts(archive), old_archive); self.assertEqual(f.batch.artifacts(old_page), before_page)
        self.assertTrue(self.flow.release('BVTest123')['eligible'])
        self.flow.release('BVTest123', execute=True)
        with self.assertRaisesRegex(ValueError, 'retained media'): self.flow.rework('BVTest123')

    def test_rework_validates_explicit_seed_and_rejects_committed_deletion(self):
        archive = self.published(); seed = self.root / 'reworked-seed'; shutil.copytree(archive, seed)
        for name in ('recipe.internal.json', 'recipe-input.json'):
            data = f.batch.load(seed / name); data['title'] = '合成返工新标题'; (seed / name).write_text(json.dumps(data, ensure_ascii=False))
        (seed / 'checksums.json').write_text(json.dumps(f.batch.artifacts(seed)))
        f.batch.library_module().validate(seed, f.batch.load(f.batch.CONTRACTS / 'video-recipe.schema.json'))
        bad = self.root / 'bad-seed'; shutil.copytree(seed, bad); (bad / 'recipe.internal.json').write_text('{}')
        with self.assertRaises(Exception): self.flow.rework('BVTest123', bad)
        self.assertEqual(self.flow.row('BVTest123')['revision'], 1)
        self.flow.rework('BVTest123', seed); self.review_seed_to_publication()
        self.assertEqual(f.batch.load(self.flow.root / 'library/search-index.json')[0]['title'], '合成返工新标题')
        real = f.os.unlink
        def crash(path, *args, **kwargs):
            if str(path) == 'BVTest123.mp4' and 'dir_fd' in kwargs: raise PowerLoss('after delete intent')
            return real(path, *args, **kwargs)
        with mock.patch.object(f.os, 'unlink', side_effect=crash):
            with self.assertRaises(PowerLoss): self.flow.release('BVTest123', execute=True)
        with self.assertRaisesRegex(ValueError, 'committed deletion intent'): self.flow.rework('BVTest123')

    def test_vocabulary_review_applies_full_inventory_and_rejects_stale_packet(self):
        self.published(); packet = self.root / 'vocabulary-packet'; self.flow.inventory(packet)
        inventory = f.batch.load(packet / 'inventory.json'); dictionary = f.batch.load(packet / 'dictionary.json')
        occurrences = inventory['entries'][0]['occurrence_ids']
        self.assertEqual(inventory['recipe_count'], 1); self.assertEqual(inventory['entries'][0]['raw_name'], '豆腐')
        review = {'schema_version': f.ingredients.VERSION, 'inventory_sha256': f.ingredients.fingerprint(inventory), 'dictionary_sha256': f.ingredients.fingerprint(dictionary), 'reviewer': {'kind': 'ai', 'name': 'synthetic-flow-test'}, 'new_items': [], 'alias_additions': [{'item_id': 'tofu_group', 'alias': '豆腐测试别称', 'reason': 'Synthetic alias integration fixture', 'occurrence_ids': occurrences}], 'parent_additions': [], 'ambiguity_additions': [], 'decisions': [{'raw_name': '豆腐', 'verdict': 'mapped', 'item_id': 'tofu_group', 'reason': 'Review every raw ingredient name in this synthetic whole library', 'occurrence_ids': occurrences}]}
        path = self.root / 'vocabulary-review.json'; f.batch.write(path, review)
        bad = {**review, 'decisions': []}; bad_path = self.root / 'omitted-review.json'; f.batch.write(bad_path, bad)
        before = (self.flow.root / 'dictionary.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'omitted'): self.flow.apply_vocabulary(packet, bad_path)
        self.assertEqual((self.flow.root / 'dictionary.json').read_bytes(), before)
        self.flow.apply_vocabulary(packet, path)
        current = f.batch.load(self.flow.root / 'dictionary.json')
        self.assertEqual(current['revision'], dictionary['revision'] + 1)
        self.assertEqual(f.batch.load(self.flow.root / 'library/ingredient-dictionary.json'), current)
        records = f.batch.load(self.flow.root / 'library/search-index.json')
        self.assertIn('豆腐测试别称', records[0]['ingredients'][0]['search_terms'])
        self.assertEqual((self.flow.root / 'library/index.html').read_text(), f.ingredients.render_directory(records, self.flow.root / 'library'))
        self.assertTrue(self.flow.release('BVTest123')['eligible'])
        current_bytes = (self.flow.root / 'dictionary.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'stale inventory'): self.flow.apply_vocabulary(packet, path)
        self.assertEqual((self.flow.root / 'dictionary.json').read_bytes(), current_bytes)
        self.assertTrue(list((self.flow.root / 'receipts').glob('vocabulary-*.json')))

    def test_publication_crash_then_vocabulary_update_recovers_original_render(self):
        self.stages(); destination = self.flow.root / 'library/recipes/BVTest123'; real = Path.rename
        def crash(path, target):
            if Path(target) == destination: raise PowerLoss('publication pending dictionary change')
            return real(path, target)
        with mock.patch.object(Path, 'rename', crash):
            with self.assertRaises(PowerLoss): self.flow.next()
        marker = self.flow.root / 'receipts/BVTest123-publication.json'
        intent = f.batch.load(marker); self.assertFalse(destination.exists())
        dictionary_snapshot = self.flow.root / 'receipts/BVTest123-dictionary.json'
        self.assertEqual(f.batch.digest(dictionary_snapshot), intent['dictionary_sha256'])
        packet = self.root / 'pending-vocabulary'; self.flow.inventory(packet)
        inventory = f.batch.load(packet / 'inventory.json'); dictionary = f.batch.load(packet / 'dictionary.json'); occurrences = inventory['entries'][0]['occurrence_ids']
        review = {'schema_version': f.ingredients.VERSION, 'inventory_sha256': f.ingredients.fingerprint(inventory), 'dictionary_sha256': f.ingredients.fingerprint(dictionary), 'reviewer': {'kind': 'ai', 'name': 'synthetic-combination-test'}, 'new_items': [], 'alias_additions': [{'item_id': 'tofu_group', 'alias': '恢复时新增豆腐别名', 'reason': 'Synthetic publication recovery fixture', 'occurrence_ids': occurrences}], 'parent_additions': [], 'ambiguity_additions': [], 'decisions': [{'raw_name': '豆腐', 'verdict': 'mapped', 'item_id': 'tofu_group', 'reason': 'Synthetic full inventory checked', 'occurrence_ids': occurrences}]}
        path = self.root / 'pending-vocabulary-review.json'; f.batch.write(path, review)
        self.flow.apply_vocabulary(packet, path)
        self.assertNotEqual(f.batch.digest(self.flow.root / 'dictionary.json'), intent['dictionary_sha256'])
        self.reopen(); self.flow.recover()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'published')
        self.assertEqual(f.batch.artifacts(destination), intent['files'])
        records = f.batch.load(self.flow.root / 'library/search-index.json')
        self.assertIn('恢复时新增豆腐别名', records[0]['ingredients'][0]['search_terms'])
        self.assertTrue(self.flow.release('BVTest123')['eligible'])

    def test_rework_cannot_adopt_old_complete_queue_to_bypass_new_review(self):
        self.published(); old_queue = self.flow.row('BVTest123')['queue']
        old_record = self.flow.row('BVTest123')['record']; self.flow.rework('BVTest123')
        self.flow.next(); new_queue = self.flow.row('BVTest123')['queue']; self.pending('review')
        with self.assertRaisesRegex(ValueError, 'rework|revision|adopt'):
            self.flow.adopt(old_queue, 'BVTest123')
        row = self.flow.row('BVTest123')
        self.assertEqual(row['revision'], 2); self.assertIsNone(row['archive'])
        self.assertEqual(row['queue'], new_queue); self.assertNotEqual(new_queue, old_queue)
        self.assertEqual(row['record'], old_record); self.assertEqual(row['state'], 'waiting_review')
        self.review_seed_to_publication()
        self.assertIn('-r2', self.flow.row('BVTest123')['archive'])

    def test_legacy_ready_acceptance_policy_never_releases_media(self):
        self.stages(); real = self.flow.accept
        def legacy_accept(queue, job):
            real(queue, job); archive = Path(self.flow.row('BVTest123')['archive'])
            acceptance = f.batch.load(archive / 'acceptance.json'); acceptance.pop('release_policy')
            (archive / 'acceptance.json').write_text(json.dumps(acceptance))
            (archive / 'checksums.json').write_text(json.dumps(f.batch.artifacts(archive)))
        with mock.patch.object(self.flow, 'accept', side_effect=legacy_accept): self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'published')
        with self.assertRaisesRegex(ValueError, 'old release policy'): self.flow.release('BVTest123', execute=True)
        self.assertTrue(self.video.exists()); self.assertIsNone(self.flow.row('BVTest123')['release'])

    def test_serial_acquisition_uses_configured_media_root_and_resumes_without_redownload(self):
        media_root = self.root / 'downloaded-media'; other = f.Flow(self.root / 'acquisition-flow')
        other.init(media_root, min_free_gib=0, sampling=self.config)
        manifest = self.root / 'acquisition.json'; f.batch.write(manifest, [{'id': 'BVFetch123', 'title': 'synthetic acquisition', 'author': 'test'}]); other.add(manifest)
        video = media_root / 'BVFetch123/source.mkv'; subtitles = video.with_name('source.ocr.zh-CN.srt')
        calls = []
        def execute(workflow, vid, kind, command):
            calls.append((vid, kind, list(command)))
            self.assertEqual(vid, 'BVFetch123')
            if kind == 'download':
                self.assertEqual(command[0], 'yt-dlp')
                self.assertEqual(command[-1], 'https://www.bilibili.com/video/BVFetch123')
                self.assertEqual(command[command.index('-o') + 1], str(video.parent / 'source.%(ext)s'))
                self.assertIn('--no-playlist', command); self.assertIn('--continue', command); self.assertIn('--no-overwrites', command)
                for flag, expected in [('--sleep-requests', '15'), ('--sleep-interval', '30'), ('--max-sleep-interval', '60'), ('--limit-rate', '2M'), ('--concurrent-fragments', '1'), ('--retries', '3'), ('--fragment-retries', '3')]:
                    self.assertEqual(command[command.index(flag) + 1], expected)
                self.assertNotIn('--cookies-from-browser', command)
                f.subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(fixtures.BatchChecks.video), '-c', 'copy', '-f', 'matroska', str(video)], check=True)
                f.batch.write(video.with_name('source.info.json'), {'id': vid})
            elif kind == 'ocr':
                self.assertEqual(command[0], str(f.ROOT / 'scripts/subtitle-ocr')); self.assertEqual(command[1], str(video))
                self.assertEqual(command[command.index('--profile') + 1], 'auto')
                self.assertNotIn('--duration', command)
                subtitles.write_text('1\n00:00:00,000 --> 00:00:05,000\n豆腐翻炒\n', encoding='utf-8')
                st = video.stat()
                f.batch.write(video.with_name('source.ocr.json'), {'tool': 'video-subtitle-ocr', 'source': str(video), 'signature': {'size': st.st_size, 'mtime_ns': st.st_mtime_ns}, 'srt_sha256': f.batch.digest(subtitles), 'settings': {'duration': None}, 'status': 'done', 'flags': []})
            else: self.fail('unexpected acquisition command ' + kind)
        try:
            with mock.patch.object(f.Flow, 'log_command', autospec=True, side_effect=execute):
                other.next(); self.assertEqual(other.row('BVFetch123')['state'], 'waiting_extract')
                self.assertEqual([kind for _, kind, _ in calls], ['download', 'ocr'])
                source_digest = f.batch.digest(video); subtitle_digest = f.batch.digest(subtitles)
                q = f.batch.Queue(other.row('BVFetch123')['queue'], read_only=True)
                try:
                    task = q.db.execute("SELECT key FROM tasks WHERE stage='extract' AND status='waiting'").fetchone()['key']
                finally: q.close()
                other.close(); other = f.Flow(self.root / 'acquisition-flow')
                other.next(); other.next()
                self.assertEqual(len(calls), 2)
                self.assertEqual(f.batch.digest(video), source_digest); self.assertEqual(f.batch.digest(subtitles), subtitle_digest)
                self.assertTrue((video.parent / 'download.json').is_file())
                self.assertFalse((other.root / 'media/BVFetch123').exists())
                q = f.batch.Queue(other.row('BVFetch123')['queue'], read_only=True)
                try: self.assertEqual(q.db.execute("SELECT key FROM tasks WHERE stage='extract' AND status='waiting'").fetchone()['key'], task)
                finally: q.close()
        finally: other.close()

    def test_media_disk_shortage_pauses_before_acquisition_even_when_state_disk_has_space(self):
        config = self.flow.setting('config'); config['min_free_gib'] = 5
        checked = []
        def usage(path):
            checked.append(Path(path))
            free = 20 * 1024 ** 3 if Path(path) == self.flow.root else 1 * 1024 ** 3
            return shutil._ntuple_diskusage(30 * 1024 ** 3, 30 * 1024 ** 3 - free, free)
        with mock.patch.object(self.flow, 'setting', return_value=config), mock.patch.object(f.shutil, 'disk_usage', side_effect=usage), mock.patch.object(self.flow, 'inputs', side_effect=AssertionError('low media disk must not prepare input')):
            result = self.flow.next()
        self.assertEqual(result['paused'], 'low disk space')
        self.assertEqual(set(checked), {self.flow.root, self.media})
        self.assertEqual(self.flow.row('BVTest123')['state'], 'queued')
        self.assertEqual(self.flow.row('BVTest123')['started'], 0)
        self.assertFalse(list((self.flow.root / 'queues').iterdir()))

    def test_rebuild_rejects_protected_archive_output_and_allows_new_root_package(self):
        archive = self.published(); before = f.batch.artifacts(archive)
        output = self.flow.root / 'accepted/intruding-output'
        with self.assertRaisesRegex(ValueError, 'protected|internal'):
            self.flow.rebuild(output)
        self.assertFalse(output.exists()); self.assertEqual(f.batch.artifacts(archive), before)
        package = self.flow.root / 'new-output-package'; self.flow.rebuild(package)
        f.batch.library_module().validate(package / 'recipes/BVTest123', f.batch.load(f.batch.CONTRACTS / 'video-recipe.schema.json'))
        self.assertEqual(f.batch.artifacts(archive), before)

    def broker_envelope(self, task):
        folder = Path(task['folder']); packet = f.batch.load(folder / 'packet.json')
        payload = f.batch.load(folder / 'payload.json')
        if packet['stage'] == 'extract': result = self.helper.draft(folder)
        elif packet['stage'] == 'review':
            recipe = payload['recipe']
            result = {'stage': 'review', 'fact_reviews': [{'fact_id': fact['id'], 'verdict': 'supported', 'reason': 'Synthetic broker cue independently reviewed', 'evidence_ids': fact['evidence_ids']} for step in recipe['steps'] + recipe['variants'] for fact in step['facts']], 'ingredient_reviews': [{'ingredient_id': i['id'], 'verdict': 'supported', 'reason': 'Synthetic broker ingredient reviewed', 'evidence_ids': i['evidence_ids']} for i in recipe['ingredients']], 'issue_reviews': [{'issue_id': i['id'], 'resolution': 'resolved', 'reason': 'Synthetic broker issue checked against cue', 'evidence_ids': ['ev_one']} for i in recipe['issues']], 'repair_requests': [], 'issues': []}
        elif packet['stage'] == 'select_images': result = self.helper.selection(folder)
        else: self.fail('unexpected broker task stage ' + packet['stage'])
        return {'task_id': packet['task_id'], 'input_sha256': packet['input_sha256'], 'processor': 'synthetic-broker-test', 'model': None, 'result': result}

    def test_broker_consumes_atomic_responses_through_full_pipeline_without_manual_import(self):
        packets = self.flow.root / 'task-packages'; responses = self.flow.root / 'responses'
        result = self.flow.pump(packets, responses)
        stages = []
        for n in range(3):
            self.assertEqual(len(result['current']['tasks']), 1)
            task = result['current']['tasks'][0]; stages.append(task['stage'])
            f.atomic(responses / ('response-' + str(n) + '.json'), self.broker_envelope(task))
            result = self.flow.pump(packets, responses, initial=False)
            self.assertEqual(result['accepted_responses'], 1)
        self.assertEqual(stages, ['extract', 'review', 'select_images'])
        self.assertEqual(result['current']['tasks'], [])
        self.assertEqual(self.flow.row('BVTest123')['state'], 'published')
        self.assertEqual(len(list((responses / 'accepted').glob('*.json'))), 3)
        self.assertFalse(list(responses.glob('*.json')))
        self.assertTrue(self.flow.release('BVTest123')['eligible']); self.assertTrue(self.video.exists())
        f.batch.library_module().validate(self.flow.root / 'library/recipes/BVTest123', f.batch.load(f.batch.CONTRACTS / 'video-recipe.schema.json'))

    def test_broker_idle_and_duplicate_accepted_delivery_do_not_rerun_or_reexport(self):
        packets = self.flow.root / 'task-packages'; responses = self.flow.root / 'responses'
        result = self.flow.pump(packets, responses)
        first = self.broker_envelope(result['current']['tasks'][0])
        f.atomic(responses / 'first.json', first); result = self.flow.pump(packets, responses, initial=False)
        marker = packets / 'current.json'; mtimes = {str(p): p.stat().st_mtime_ns for p in packets.rglob('*') if p.is_file()}
        with mock.patch.object(f.batch.Queue, 'run', side_effect=AssertionError('idle must not rerun stages')), mock.patch.object(f.batch.Queue, 'export', side_effect=AssertionError('idle must not reexport packets')):
            self.flow.pump(packets, responses, initial=False)
            f.atomic(responses / 'duplicate.json', first)
            duplicate = self.flow.pump(packets, responses, initial=False)
        self.assertEqual(duplicate['accepted_responses'], 0)
        self.assertEqual({str(p): p.stat().st_mtime_ns for p in packets.rglob('*') if p.is_file()}, mtimes)
        self.assertEqual(f.batch.load(marker)['tasks'][0]['stage'], 'review')
        self.assertEqual(self.flow.db.execute("SELECT count(*) FROM deliveries WHERE state='accepted'").fetchone()[0], 1)
        self.assertFalse((responses / 'duplicate.json').exists()); self.assertTrue(self.video.exists())

    def test_broker_accepted_import_survives_receipt_failure_and_retry_advances(self):
        packets = self.flow.root / 'task-packages'; responses = self.flow.root / 'responses'
        result = self.flow.pump(packets, responses)
        inbox = responses / 'receipt-retry.json'
        f.atomic(inbox, self.broker_envelope(result['current']['tasks'][0]))
        sha = f.batch.digest(inbox)
        with mock.patch.object(self.flow, 'received', side_effect=OSError('synthetic receipt rename failure')):
            result = self.flow.pump(packets, responses, initial=False)
        self.assertIn('paused', result)
        receipt = self.flow.db.execute('SELECT state,error FROM deliveries WHERE sha=?', (sha,)).fetchone()
        self.assertEqual(receipt['state'], 'accepted')
        self.assertIn('synthetic receipt rename failure', receipt['error'])
        self.assertTrue(inbox.exists()); self.assertTrue(self.video.exists())
        self.assertEqual(self.flow.row('BVTest123')['state'], 'waiting_extract')
        self.reopen()
        with mock.patch.object(self.flow, 'import_response', side_effect=AssertionError('accepted response must not be reimported')):
            result = self.flow.pump(packets, responses, initial=False)
        self.assertNotIn('paused', result); self.assertEqual(result['accepted_responses'], 1)
        self.assertEqual(result['current']['tasks'][0]['stage'], 'review')
        receipt = self.flow.db.execute('SELECT state,error FROM deliveries WHERE sha=?', (sha,)).fetchone()
        self.assertEqual(receipt['state'], 'accepted'); self.assertIsNone(receipt['error'])
        self.assertFalse(inbox.exists()); self.assertTrue((responses / 'accepted' / (sha + '.json')).exists())
        self.assertTrue(self.video.exists())

    def test_broker_invalid_body_pauses_retains_video_and_corrected_hash_resumes(self):
        packets = self.flow.root / 'task-packages'; responses = self.flow.root / 'responses'
        result = self.flow.pump(packets, responses); good = self.broker_envelope(result['current']['tasks'][0])
        inbox = responses / 'result.json'; f.atomic(inbox, {**good, 'result': {}})
        bad_sha = f.batch.digest(inbox); result = self.flow.pump(packets, responses, initial=False)
        self.assertTrue(result['paused']); self.assertEqual(len(result['rejected']), 1)
        self.assertEqual(result['rejected'][0]['file'], str(inbox)); self.assertTrue(result['rejected'][0]['error'])
        self.assertTrue(inbox.exists()); self.assertTrue(self.video.exists())
        self.assertEqual(self.flow.row('BVTest123')['state'], 'waiting_extract')
        self.reopen()
        with mock.patch.object(self.flow, 'import_response', side_effect=AssertionError('unchanged rejected delivery must not retry')):
            self.assertIn('paused', self.flow.pump(packets, responses, initial=False))
        f.atomic(inbox, good); self.assertNotEqual(f.batch.digest(inbox), bad_sha)
        result = self.flow.pump(packets, responses, initial=False)
        self.assertNotIn('paused', result); self.assertEqual(result['current']['tasks'][0]['stage'], 'review')
        self.assertEqual(self.flow.db.execute("SELECT count(*) FROM deliveries WHERE state='rejected'").fetchone()[0], 1)
        self.assertEqual(self.flow.db.execute("SELECT count(*) FROM deliveries WHERE state='accepted'").fetchone()[0], 1)
        self.assertTrue(self.video.exists())

    def test_broker_watch_waits_for_ai_serially_and_exits_at_retained_capacity(self):
        manifest = self.root / 'broker-next.json'; f.batch.write(manifest, [{'id': 'BVLater1', 'title': 'later', 'author': 'test'}]); self.flow.add(manifest)
        packets = self.flow.root / 'task-packages'; responses = self.flow.root / 'responses'; stages = []; real_sleep = f.time.sleep
        config = self.flow.setting('config'); config['max_retained'] = 1
        def ai(seconds):
            if seconds != 1: return real_sleep(seconds)
            self.assertLess(len(stages), 3)
            current = f.batch.load(packets / 'current.json'); self.assertEqual(current['video_id'], 'BVTest123')
            self.assertEqual(self.flow.row('BVLater1')['state'], 'queued')
            self.assertFalse((self.flow.root / 'queues/BVLater1').exists())
            task = current['tasks'][0]; stages.append(task['stage'])
            f.atomic(responses / ('response-' + str(len(stages)) + '.json'), self.broker_envelope(task))
        with mock.patch.object(self.flow, 'setting', return_value=config), mock.patch.object(f.time, 'sleep', side_effect=ai), mock.patch('builtins.print'), mock.patch.object(self.flow, 'log_command', side_effect=AssertionError('must not download next video')):
            result = self.flow.run(packets, responses, watch=True, poll_seconds=1)
        self.assertEqual(stages, ['extract', 'review', 'select_images'])
        self.assertEqual(result['status']['paused'], 'retained-video limit')
        self.assertEqual(self.flow.row('BVLater1')['state'], 'queued'); self.assertTrue(self.video.exists())

    def test_broker_watch_exits_when_all_items_complete(self):
        packets = self.flow.root / 'task-packages'; responses = self.flow.root / 'responses'; stages = []; real_sleep = f.time.sleep
        def ai(seconds):
            if seconds != 1: return real_sleep(seconds)
            self.assertLess(len(stages), 3)
            task = f.batch.load(packets / 'current.json')['tasks'][0]; stages.append(task['stage'])
            f.atomic(responses / ('response-' + str(len(stages)) + '.json'), self.broker_envelope(task))
        with mock.patch.object(f.time, 'sleep', side_effect=ai), mock.patch('builtins.print'):
            result = self.flow.run(packets, responses, watch=True, poll_seconds=1)
        self.assertEqual(len(stages), 3); self.assertEqual(result['current']['tasks'], [])
        self.assertEqual(result['status']['counts'], {'published': 1})
        self.assertTrue(self.flow.release('BVTest123')['eligible'])

    def test_retained_and_disk_limits_pause_before_next_input(self):
        self.published(ready=False)
        manifest = self.root / 'next.json'; f.batch.write(manifest, [{'id': 'BVLater1', 'title': 'later', 'author': 'test'}]); self.flow.add(manifest)
        config = self.flow.setting('config'); config['max_retained'] = 1
        with mock.patch.object(self.flow, 'setting', return_value=config), mock.patch.object(self.flow, 'inputs', side_effect=AssertionError('must pause before download')):
            self.assertEqual(self.flow.next()['paused'], 'retained-video limit')
        config['max_retained'] = 3; config['min_free_gib'] = 5
        usage = shutil._ntuple_diskusage(100, 100, 0)
        with mock.patch.object(self.flow, 'setting', return_value=config), mock.patch.object(f.shutil, 'disk_usage', return_value=usage), mock.patch.object(self.flow, 'inputs', side_effect=AssertionError('must pause before download')):
            self.assertEqual(self.flow.next()['paused'], 'low disk space')
        self.assertTrue(self.video.exists())


    def proposal(self, archive):
        data = f.batch.load(archive / 'recipe.internal.json')
        fact = json.loads(json.dumps(data['steps'][0]['facts'][0])); fact['id'] = 'fact_revision_new'; fact['text'] = '补充原字幕豆腐翻炒动作'; fact['review_status'] = 'supported'
        data['steps'][0]['facts'].append(fact)
        path = self.root / 'proposal.json'; f.atomic(path, data)
        return path

    def test_additive_revision_preserves_history_and_new_fact_cannot_certify_itself(self):
        archive = self.published(); old = f.batch.artifacts(archive); proposal = self.proposal(archive)
        result = self.flow.prepare_revision('BVTest123', proposal, self.root / 'revision', 'synthetic-proposer')
        seed = Path(result['seed']); data = f.batch.library_module().validate(seed, f.batch.load(f.batch.CONTRACTS / 'video-recipe.schema.json'))
        self.assertEqual(data['steps'][0]['facts'][-1]['review_status'], 'needs_review')
        self.assertEqual(data['status'], 'needs_review'); self.assertFalse(data['human_reviewed'])
        self.assertEqual(f.batch.artifacts(archive), old)
        self.assertTrue(any(i['resolution'] == 'open' and 'fact_revision_new' in i['target_ids'] for i in data['issues']))
        f.batch.verify(seed); self.flow.rework('BVTest123', seed); self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'], 'waiting_review')
        folder = self.pending('review'); current = f.batch.load(folder / 'payload.json')['recipe']
        self.assertIn('fact_revision_new', [x['id'] for x in current['steps'][0]['facts']])

    def test_revision_keeps_resolved_pending_issue_history_when_old_fact_changes(self):
        archive = self.published(); old = f.batch.load(archive / 'recipe.internal.json')
        historical = {'id': 'issue_pending_fact_one', 'code': 'other', 'target_ids': ['fact_one'], 'description': '旧待审项', 'evidence_ids': ['ev_one'], 'resolution': 'resolved', 'resolution_note': '旧版本已经独立核对'}
        # Synthetic historical fixture; real accepted archives are never edited.
        old['issues'].append(historical); f.atomic(archive / 'recipe.internal.json', old)
        f.atomic(archive / 'checksums.json', f.batch.artifacts(archive))
        candidate = json.loads(json.dumps(old)); candidate['steps'][0]['facts'][0]['text'] = '修订豆腐翻炒原文说明'
        proposal = self.root / 'old-fact-proposal.json'; f.atomic(proposal, candidate)
        result = self.flow.prepare_revision('BVTest123', proposal, self.root / 'historical-seed', 'synthetic-proposer')
        data = f.batch.library_module().validate(Path(result['seed']), f.batch.load(f.batch.CONTRACTS / 'video-recipe.schema.json'))
        self.assertEqual(next(i for i in data['issues'] if i['id'] == historical['id']), historical)
        self.assertTrue(any(i['id'] != historical['id'] and i['resolution'] == 'open' and 'fact_one' in i['target_ids'] for i in data['issues']))

    def test_even_unchanged_ready_proposal_requires_independent_revision_review(self):
        archive = self.published(); proposal = self.root / 'unchanged-proposal.json'; f.atomic(proposal, f.batch.load(archive / 'recipe.internal.json'))
        result = self.flow.prepare_revision('BVTest123', proposal, self.root / 'unchanged-seed', 'synthetic-proposer')
        data = f.batch.library_module().validate(Path(result['seed']), f.batch.load(f.batch.CONTRACTS / 'video-recipe.schema.json'))
        self.assertEqual(data['status'], 'needs_review'); self.assertTrue(any(item['resolution'] == 'open' for item in data['issues']))

    def test_revision_rejects_source_history_id_quote_and_issue_tampering(self):
        archive = self.published(ready=False); original = f.batch.load(archive / 'recipe.internal.json')
        changes = [lambda d: d['source'].update(author='fabricated'), lambda d: d.update(human_reviewed=True), lambda d: d['evidence'][0].update(quote='fabricated'), lambda d: d['issues'][0].update(resolution='resolved', resolution_note='self-certified'), lambda d: d['steps'][0]['facts'].clear(), lambda d: d['frames'][0].update(sha256='0'*64), lambda d: d['evidence'].append({**d['evidence'][0], 'id': 'ev_new_fake', 'quote': 'fabricated new cue quote'})]
        for n, change in enumerate(changes):
            with self.subTest(change=n):
                data = json.loads(json.dumps(original)); change(data); proposal = self.root / 'tampered.json'; f.atomic(proposal, data)
                destination = self.root / ('bad-seed-' + str(n))
                with self.assertRaises((ValueError, ValidationError)): self.flow.prepare_revision('BVTest123', proposal, destination, 'synthetic-proposer')
                self.assertFalse(destination.exists())

    def test_revision_requires_new_safe_destination_and_keeps_original_proposal(self):
        archive = self.published(); proposal = self.proposal(archive); digest = f.batch.digest(proposal)
        existing = self.root / 'existing'; existing.mkdir(); marker = existing / 'keep'; marker.write_text('keep')
        for destination in (existing, self.flow.root / 'accepted/new', self.flow.root / 'library/new'):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                self.flow.prepare_revision('BVTest123', proposal, destination, 'synthetic-proposer')
        self.assertEqual(marker.read_text(), 'keep'); self.assertEqual(f.batch.digest(proposal), digest)


if __name__ == '__main__': unittest.main()
