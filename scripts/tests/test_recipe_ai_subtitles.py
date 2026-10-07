"""AI-only workflow admission, failure semantics and resume with synthetic subtitles."""
import json
from pathlib import Path
import subprocess
import tempfile
import shutil
import unittest
from unittest import mock
import test_recipe_flow as fixtures

f = fixtures.f

class AISubtitleChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixtures.FlowChecks.setUpClass()
    @classmethod
    def tearDownClass(cls): fixtures.FlowChecks.tearDownClass()
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.video = self.root / 'existing.mp4'
        shutil.copyfile(fixtures.fixtures.BatchChecks.video, self.video)
        self.flow = f.Flow(self.root / 'workflow')
        self.flow.init(media_root=self.root, min_free_gib=0, max_retained=1, media_mode='clips', subtitle_policy='bilibili-ai-only')
        self.entry = {'id':'BVTest123', 'title':'豆腐', 'author':'test'}
        self.calls = []
    def tearDown(self): self.flow.close(); self.temp.cleanup()
    def add(self, *entries):
        p=self.root/'manifest.json'; f.atomic(p,list(entries)); self.flow.add(p)
    def platform(self, present=True, warning='', missing=False, malformed=False):
        def invoke(vid, kind, command):
            self.calls.append((kind,command))
            self.assertEqual(kind,'ai-subtitles') # Never OCR or video download here.
            self.assertIn('--skip-download',command); self.assertIn('--ignore-config',command)
            self.assertIn('--write-subs',command); self.assertEqual(command[command.index('--sub-langs')+1],'ai-zh')
            directory=self.flow.root/'platform-subtitles'/vid
            f.atomic(directory/'source.info.json', {'id':vid, 'duration':f.batch.probe(self.video), 'subtitles':{'ai-zh':[{'ext':'srt'}]} if present else {'danmaku':[{'ext':'xml'}]}})
            if present and not missing:
                (directory/'source.ai-zh.srt').write_text('bad' if malformed else '1\n00:00:00,000 --> 00:00:01,000\n豆腐翻炒\n',encoding='utf-8')
            return 'Recipe AI-only subtitle filter active\n' + warning
        return invoke
    def test_absent_skips_without_download_or_ocr_and_survives_resume(self):
        self.add(self.entry)
        with mock.patch.object(self.flow,'log_command',side_effect=self.platform(False)):
            result=self.flow.next(delete_videos=True)
        self.assertEqual(result['counts'],{'skipped':1}); self.assertEqual(self.flow.retain_count(),0)
        self.assertFalse((self.flow.root/'media/BVTest123').exists())
        self.assertFalse((self.flow.root/'queues/BVTest123').exists())
        self.assertEqual(self.flow.row('BVTest123')['error'],'no_ai_zh_subtitles')
        self.flow.close(); self.flow=f.Flow(self.root/'workflow')
        with mock.patch.object(self.flow,'log_command',side_effect=AssertionError('must not requery')):
            self.assertEqual(self.flow.next()['counts'],{'skipped':1})
        self.assertTrue(self.video.exists())
    def test_skipped_existing_video_retained_and_next_item_is_not_capacity_blocked(self):
        second={**self.entry,'id':'BVNext456','video':str(self.video)}
        self.add({**self.entry,'video':str(self.video)},second)
        with mock.patch.object(self.flow,'log_command',side_effect=self.platform(False)):
            self.flow.next(delete_videos=True); self.flow.next(delete_videos=True)
        self.assertEqual(self.flow.status()['counts'],{'skipped':2}); self.assertTrue(self.video.exists())
        self.assertEqual(len(self.calls),2)
        # A watching broker terminates once the only entries are skipped.
        result=self.flow.run(self.flow.root/'packets',self.flow.root/'responses',watch=True,poll_seconds=1)
        self.assertEqual(result['status']['counts'],{'skipped':2})
    def test_available_creates_text_task_and_caches_bound_platform_subtitles(self):
        self.add({**self.entry,'video':str(self.video)})
        with mock.patch.object(self.flow,'log_command',side_effect=self.platform()): self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'],'waiting_extract')
        inputs=f.batch.load(self.flow.root/'receipts/BVTest123-input.json')[0]
        self.assertEqual(inputs['subtitle_origin'],'platform')
        marker=self.flow.root/'platform-subtitles/BVTest123/result.json'
        self.assertEqual(f.batch.load(marker)['generation'],'ai')
        with mock.patch.object(self.flow,'log_command',side_effect=AssertionError('cached')):
            self.flow.inputs(self.flow.row('BVTest123'))
        self.assertEqual(len(self.calls),1)
        q=f.batch.Queue(self.flow.row('BVTest123')['queue'],read_only=True)
        try:
            payloads=[f.batch.load(p) for p in Path(q.root).rglob('payload.json')]
            self.assertTrue(any(p.get('source',{}).get('subtitle_origin')=='platform' for p in payloads))
        finally:q.close()
    def test_ai_subtitles_to_clips_archive_release_and_no_video_rebuild(self):
        self.add({**self.entry,'video':str(self.video)})
        def pending(stage):
            q=f.batch.Queue(self.flow.row('BVTest123')['queue'],read_only=True)
            try:
                task=q.db.execute("SELECT * FROM tasks WHERE stage=? AND status='waiting'",(stage,)).fetchone()
                self.assertIsNotNone(task);return q.folder(task['key'])
            finally:q.close()
        def send(folder,result):
            packet=f.batch.load(folder/'packet.json');p=self.root/'response.json'
            f.atomic(p,{'task_id':packet['task_id'],'input_sha256':packet['input_sha256'],'processor':'synthetic-'+packet['stage'],'model':None,'result':result})
            self.flow.import_response(p)
        with mock.patch.object(self.flow,'log_command',side_effect=self.platform()):self.flow.next()
        helper=fixtures.fixtures.BatchChecks();helper.root=self.root
        folder=pending('extract');send(folder,helper.draft(folder));self.flow.next();folder=pending('review')
        send(folder,{'stage':'review','fact_reviews':[{'fact_id':'fact_one','verdict':'supported','reason':'synthetic explicit subtitle','evidence_ids':['ev_one']}],'ingredient_reviews':[{'ingredient_id':'ing_tofu','verdict':'supported','reason':'synthetic explicit subtitle','evidence_ids':['ev_one']}],'issue_reviews':[{'issue_id':'issue_pending','resolution':'resolved','reason':'synthetic explicit subtitle','evidence_ids':['ev_one']}],'repair_requests':[],'issues':[]})
        with mock.patch.object(self.flow,'log_command',side_effect=AssertionError('no OCR or repeated download')):self.flow.next()
        row=self.flow.row('BVTest123');self.assertEqual(row['state'],'published')
        archive=Path(row['archive']);receipt=f.batch.load(archive/'source-platform-subtitles.json')
        self.assertEqual(receipt['generation'],'ai');self.assertEqual(receipt['sha256'],f.batch.digest(archive/'source.srt'))
        self.assertFalse((archive/'source-ocr.json').exists());self.assertFalse(f.batch.load(archive/'acceptance.json')['ocr_review_pending'])
        q=f.batch.Queue(row['queue'],read_only=True)
        try:self.assertFalse(q.db.execute("SELECT 1 FROM tasks WHERE stage LIKE 'select_%' OR stage LIKE 'review_visual_%'").fetchone())
        finally:q.close()
        self.assertTrue(self.flow.release('BVTest123')['eligible'])
        # Only delete this test's owned synthetic copy, then rebuild without it.
        self.flow.release('BVTest123',execute=True);self.assertFalse(self.video.exists())
        self.flow.close();self.flow=f.Flow(self.root/'workflow')
        with mock.patch.object(f.batch,'probe',side_effect=AssertionError('must not probe original')):
            self.flow.rebuild(self.root/'reconstructed')
        self.assertTrue(list((self.root/'reconstructed').glob('recipes/*/clips/*.mp4')))

    def test_network_failure_is_retryable_failure_not_permanent_skip(self):
        self.add(self.entry)
        with mock.patch.object(self.flow,'log_command',side_effect=subprocess.CalledProcessError(1,['yt-dlp'])):
            with self.assertRaises(subprocess.CalledProcessError):self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'],'failed')
        self.assertFalse((self.flow.root/'platform-subtitles/BVTest123/result.json').exists())
        self.flow.retry('BVTest123')
        with mock.patch.object(self.flow,'log_command',side_effect=self.platform(False)):self.flow.next()
        self.assertEqual(self.flow.row('BVTest123')['state'],'skipped')
    def test_login_or_partial_subtitle_warning_is_failure_not_skip(self):
        self.add(self.entry)
        for warning in ['WARNING: Subtitles are only available when logged in.', 'WARNING: Unable to download subtitle info: HTTP Error 412']:
            with mock.patch.object(self.flow,'log_command',side_effect=self.platform(False,warning)):
                with self.assertRaises(ValueError):self.flow.next()
            self.assertEqual(self.flow.row('BVTest123')['state'],'failed')
            self.flow.retry('BVTest123')
    def test_advertised_missing_or_corrupt_srt_is_not_accepted(self):
        self.add(self.entry)
        for options in [{'missing':True},{'malformed':True}]:
            with mock.patch.object(self.flow,'log_command',side_effect=self.platform(**options)):
                with self.assertRaises(ValueError):self.flow.next()
            self.assertFalse((self.flow.root/'platform-subtitles/BVTest123/result.json').exists())
            self.flow.retry('BVTest123')
    def test_subtitle_tampering_is_rejected(self):
        self.add({**self.entry,'video':str(self.video)})
        with mock.patch.object(self.flow,'log_command',side_effect=self.platform()):self.flow.inputs(self.flow.row('BVTest123'))
        (self.flow.root/'platform-subtitles/BVTest123/source.ai-zh.srt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'content changed'):self.flow.inputs(self.flow.row('BVTest123'))
    def test_changed_ai_provenance_receipt_is_rejected(self):
        self.add({**self.entry,'video':str(self.video)})
        with mock.patch.object(self.flow,'log_command',side_effect=self.platform()):self.flow.inputs(self.flow.row('BVTest123'))
        p=self.flow.root/'platform-subtitles/BVTest123/result.json';result=f.batch.load(p)
        for key,value in [('generation','human'),('origin','ocr'),('cue_count',999)]:
            f.atomic(p,{**result,key:value})
            with self.assertRaises(ValueError):self.flow.inputs(self.flow.row('BVTest123'))
        f.atomic(p,result)

    def test_external_ocr_or_seed_cannot_bypass_ai_only_admission(self):
        for field,value in [('subtitles',str(self.video)),('seed',str(self.root)),('subtitle_origin','ocr')]:
            with self.assertRaisesRegex(ValueError,'fetches its own'):self.add({**self.entry,'video':str(self.video),field:value})
        with self.assertRaisesRegex(ValueError,'cannot adopt'):self.flow.adopt(self.root/'external','BVTest123')
        self.assertEqual(self.flow.status()['total'],0)
    def test_log_warning_from_failed_attempt_does_not_poison_retry(self):
        path=self.flow.root/'logs/BVTest123-ai-subtitles.log'
        path.write_text('WARNING: Subtitles are only available when logged in.\n')
        def successful(command,**kwargs):kwargs['stdout'].write(b'new attempt succeeded\n')
        with mock.patch.object(f.subprocess,'run',side_effect=successful):
            result=self.flow.log_command('BVTest123','ai-subtitles',['yt-dlp'])
        self.assertEqual(result,'new attempt succeeded\n')

if __name__ == '__main__': unittest.main()
