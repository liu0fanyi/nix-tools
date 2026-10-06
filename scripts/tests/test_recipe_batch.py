"""Queue/recovery tests use synthetic subtitles and images, not culinary evaluation."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('batch', ROOT / 'recipe-batch.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class BatchChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media = tempfile.TemporaryDirectory()
        cls.video = Path(cls.media.name) / 'synthetic.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=green:s=160x90:r=10:d=5', '-c:v', 'mpeg4', str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.media.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.srt = self.root / 'source.srt'; self.srt.write_text('1\n00:00:00,000 --> 00:00:02,000\n豆腐翻炒\n', encoding='utf-8')
        self.manifest = self.root / 'manifest.json'
        m.write(self.manifest, [{'id': 'BVTest123', 'title': '合成测试', 'author': 'test', 'video': str(self.video), 'subtitles': str(self.srt), 'subtitle_origin': 'ocr'}])
        self.config = {'width': 160, 'candidates': 2, 'interval': 1, 'padding': 0, 'strategy': 'bounded-uniform-per-window'}
        self.queue = m.Queue(self.root / 'queue'); self.queue.add(self.manifest, self.config)
        self.source_digest = m.digest(self.video)

    def tearDown(self):
        self.queue.close(); self.temp.cleanup()

    def pending(self, stage):
        row = self.queue.db.execute("SELECT * FROM tasks WHERE stage=? AND status='waiting'", (stage,)).fetchone()
        self.assertIsNotNone(row)
        return self.queue.folder(row['key'])

    def envelope(self, folder, result):
        packet = m.load(folder / 'packet.json')
        return {'task_id': packet['task_id'], 'input_sha256': packet['input_sha256'], 'processor': 'synthetic-test', 'model': None, 'result': result}

    def send(self, folder, result):
        response = self.envelope(folder, result)
        path = self.root / ('response-' + str(len(list(self.root.glob('response*')))) + '.json'); m.write(path, response)
        return self.queue.import_result(path)

    def draft(self, folder):
        payload = m.load(folder / 'payload.json')
        quantity = {'mode': 'unspecified', 'min': None, 'max': None, 'unit': None, 'original': '未明确'}
        return {'schema_version': '1.0.0', 'recipe_id': payload['recipe_id'], 'title': '合成测试', 'source': payload['source'], 'coverage': 'full', 'covered_intervals': [{'start': 0, 'end': payload['source']['duration_seconds']}], 'status': 'draft', 'human_reviewed': False,
            'ingredients': [{'id': 'ing_tofu', 'name': '豆腐', 'role': 'main', 'quantity': quantity, 'evidence_ids': ['ev_one'], 'review_status': 'needs_review'}],
            'steps': [{'id': 'step_one', 'title': '翻炒', 'depends_on': [], 'facts': [{'id': 'fact_one', 'kind': 'action', 'text': '豆腐翻炒', 'measure': None, 'ingredient_ids': ['ing_tofu'], 'evidence_ids': ['ev_one'], 'review_status': 'needs_review'}], 'evidence_windows': [{'start': 0, 'end': 2}], 'image_goal': '仅合成结构测试', 'selected_frame_id': None, 'no_image_reason': '待选图'}],
            'variants': [], 'evidence': [{'id': 'ev_one', 'kind': 'subtitle', 'interval': {'start': 0, 'end': 2}, 'cue_ids': [1], 'frame_id': None, 'quote': '豆腐翻炒', 'observation': None}], 'frames': [], 'image_reviews': [],
            'issues': [{'id': 'issue_pending', 'code': 'other', 'target_ids': ['ing_tofu', 'fact_one'], 'description': '合成测试，未做真实语义验收。', 'evidence_ids': [], 'resolution': 'open', 'resolution_note': None}], 'runs': []}

    def to_images(self):
        self.queue.run(); folder = self.pending('extract'); self.send(folder, self.draft(folder))
        self.queue.run(); folder = self.pending('review')
        self.send(folder, {'stage': 'review', 'fact_reviews': [{'fact_id': 'fact_one', 'verdict': 'needs_review', 'reason': 'synthetic only', 'evidence_ids': ['ev_one']}], 'issues': []})
        self.queue.run()
        return self.pending('select_step_one')

    def selection(self, folder, missing=False):
        frames = m.load(folder / 'payload.json')['candidates']
        return {'stage': 'select_images', 'step_id': 'step_one', 'candidate_reviews': [{'step_id': 'step_one', 'frame_id': f['id'], 'relevance': 'matches', 'quality': 'usable', 'reason': 'synthetic structural fixture, not a real visual verdict'} for f in frames], 'selected_frame_id': None if missing else frames[0]['id'], 'no_image_reason': '合成缺图测试' if missing else None, 'observations': []}

    def test_end_to_end_build_and_resume_preserve_sources(self):
        folder = self.to_images(); self.send(folder, self.selection(folder))
        self.assertEqual(self.queue.run()['counts'], {'complete': 1})
        before = self.queue.status()['tasks']; self.queue.close(); self.queue = m.Queue(self.root / 'queue')
        self.assertEqual(self.queue.run()['tasks'], before)
        output = self.root / 'library'; result = self.queue.build(output, m.ROOT / 'config/recipe/ingredients.json')
        self.assertEqual(result['recipes'], 1)
        recipe = m.load(output / 'recipes/BVTest123/recipe.internal.json')
        self.assertEqual(recipe['status'], 'needs_review'); self.assertFalse(recipe['human_reviewed'])
        m.library_module().validate(output / 'recipes/BVTest123', m.load(m.CONTRACTS / 'video-recipe.schema.json'))
        rebuilt = self.root / 'rebuilt'; m.library_module().build(output / 'recipes', rebuilt, m.ROOT / 'config/recipe/ingredients.json')
        m.library_module().validate(rebuilt / 'recipes/BVTest123', m.load(m.CONTRACTS / 'video-recipe.schema.json'))
        self.assertEqual(m.digest(self.video), self.source_digest)
        self.assertEqual(self.srt.read_text(), '1\n00:00:00,000 --> 00:00:02,000\n豆腐翻炒\n')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.queue.build(output, m.ROOT / 'config/recipe/ingredients.json')

    def test_reject_invented_quote_and_escalation_then_accept_corrected_result(self):
        self.queue.run(); folder = self.pending('extract'); draft = self.draft(folder)
        bad = copy.deepcopy(draft); bad['evidence'][0]['quote'] = '虚构'
        with self.assertRaisesRegex(ValueError, 'quote'):
            self.send(folder, bad)
        bad = copy.deepcopy(draft); bad['human_reviewed'] = True
        with self.assertRaisesRegex(ValueError, 'human review'):
            self.send(folder, bad)
        self.send(folder, draft)
        self.assertEqual(self.send(folder, draft), 'already_imported')
        bad = copy.deepcopy(draft); bad['title'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'no overwrite'):
            self.send(folder, bad)
        self.assertEqual(len(list((self.queue.root / 'rejected').glob('*.json'))), 3)

    def test_reconfiguration_reuses_text_and_rejects_old_visual_packet(self):
        folder = self.to_images(); old_key = folder.name
        config = {**self.config, 'width': 192}; self.queue.add(self.manifest, config); self.queue.run()
        response = self.root / 'stale.json'; m.write(response, self.envelope(folder, self.selection(folder)))
        with self.assertRaisesRegex(ValueError, 'stale task'):
            self.queue.import_result(response)
        stages = self.queue.status()['tasks']
        self.assertEqual(sum(t['stage'] == 'prepare' for t in stages), 1)
        self.assertEqual(sum(t['stage'] == 'extract' for t in stages), 1)
        self.assertEqual(sum(t['stage'] == 'review' for t in stages), 1)
        self.assertEqual(sum(t['stage'] == 'select_step_one' for t in stages), 2)
        exported = self.root / 'packets'; self.queue.export(exported)
        self.assertFalse((exported / old_key).exists()); self.assertEqual(m.load(exported / 'manifest.json')['packets'], 1)

    def test_tampered_checkpoint_and_source_changes_fail_closed(self):
        self.queue.run(); folder = self.pending('extract'); (folder / 'payload.json').write_text('{}')
        self.assertEqual(self.queue.run()['counts'], {'failed': 1})
        self.assertIn('checkpoint was modified', self.queue.status()['jobs'][0]['error'])
        self.srt.write_text('changed')
        self.assertEqual(self.queue.run()['counts'], {'failed': 1})
        self.assertIn('source changed', self.queue.status()['jobs'][0]['error'])

    def test_missing_image_and_incomplete_review(self):
        self.queue.run(); extract = self.pending('extract'); self.send(extract, self.draft(extract)); self.queue.run()
        review = self.pending('review')
        with self.assertRaisesRegex(ValueError, 'every fact'):
            self.send(review, {'stage': 'review', 'fact_reviews': [], 'issues': []})
        self.send(review, {'stage': 'review', 'fact_reviews': [{'fact_id': 'fact_one', 'verdict': 'needs_review', 'reason': 'test', 'evidence_ids': ['ev_one']}], 'issues': []}); self.queue.run()
        folder = self.pending('select_step_one'); bad = self.selection(folder); bad['selected_frame_id'] = 'unprovided'
        with self.assertRaisesRegex(ValueError, 'selected frame'):
            self.send(folder, bad)
        self.send(folder, self.selection(folder, missing=True)); self.assertEqual(self.queue.run()['counts'], {'complete': 1})
        output = self.root / 'missing-image-library'; self.queue.build(output, m.ROOT / 'config/recipe/ingredients.json')
        self.assertIn('合成缺图测试', (output / 'recipes/BVTest123/recipe.html').read_text())

    def test_single_writer_and_live_read_only_status(self):
        with self.assertRaisesRegex(ValueError, 'busy'):
            m.Queue(self.queue.root)
        reader = m.Queue(self.queue.root, read_only=True)
        try:
            self.assertEqual(reader.status()['counts'], {'queued': 1})
        finally:
            reader.close()

    def test_crash_after_stage_publication_recovers_without_reexecution(self):
        real = self.queue.db
        class CrashBeforeCommit:
            def execute(self, sql, params=()):
                if sql.startswith('UPDATE tasks SET status='):
                    raise SystemExit('simulated kill after filesystem publication')
                return real.execute(sql, params)
            def commit(self): return real.commit()
        self.queue.db = CrashBeforeCommit()
        calls = []
        def action(folder, key):
            calls.append(key); m.write(folder / 'value.json', {'complete': True})
        with self.assertRaises(SystemExit):
            self.queue.stage('BVTest123', 'recovery_fixture', {'a': 1}, action)
        self.queue.db = real; self.queue.close(); self.queue = m.Queue(self.root / 'queue')
        folder, status = self.queue.stage('BVTest123', 'recovery_fixture', {'a': 1}, action)
        self.assertEqual(status, 'done'); self.assertEqual(len(calls), 1); m.verify(folder)

    def test_published_response_recovers_after_database_commit_interruption(self):
        self.queue.run(); folder = self.pending('extract'); result = self.draft(folder)
        response = self.root / 'interrupted-response.json'; m.write(response, self.envelope(folder, result))
        real = self.queue.db
        class CrashBeforeResultCommit:
            def execute(self, sql, params=()):
                if sql.startswith('UPDATE tasks SET status=') and params and params[0] == 'done':
                    raise SystemExit('simulated kill after result publication')
                return real.execute(sql, params)
            def commit(self): return real.commit()
        self.queue.db = CrashBeforeResultCommit()
        with self.assertRaises(SystemExit):
            self.queue.import_result(response)
        self.queue.db = real; self.queue.close(); self.queue = m.Queue(self.root / 'queue')
        self.assertEqual(self.queue.run()['counts'], {'waiting_review': 1})
        self.assertEqual(self.queue.import_result(response), 'already_imported')
        m.verify(self.queue.result(folder).parent)

    def test_successful_visual_response_becomes_stale_after_reconfiguration(self):
        folder = self.to_images(); selection = self.selection(folder); self.send(folder, selection)
        self.queue.add(self.manifest, {**self.config, 'width': 192}); self.queue.run()
        with self.assertRaisesRegex(ValueError, 'stale task'):
            self.send(folder, selection)

    def test_malformed_and_overflow_responses_are_archived_without_advancing(self):
        self.queue.run()
        for text in ['{"broken":', '{"value": 1e999}']:
            path = self.root / ('malformed-' + str(len(list(self.root.glob('malformed*')))) + '.json')
            path.write_text(text)
            with self.assertRaises(ValueError):
                self.queue.import_result(path)
        self.assertEqual(self.queue.run()['counts'], {'waiting_extract': 1})
        saved = {p.read_text() for p in (self.queue.root / 'rejected').glob('*.json')}
        self.assertEqual(saved, {'{"broken":', '{"value": 1e999}'})

    def test_sampling_keeps_each_disjoint_window_and_rejects_insufficient_budget(self):
        times = m.sample_times([{'start': 0, 'end': 1}, {'start': 4, 'end': 5}], 5, self.config)
        self.assertTrue(any(t < 1 for t in times)); self.assertTrue(any(t > 4 for t in times))
        with self.assertRaisesRegex(ValueError, 'more windows'):
            m.sample_times([{'start': 0, 'end': 1}, {'start': 4, 'end': 5}], 5, {**self.config, 'candidates': 1})
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            p = self.root / 'bad.json'; p.write_text('{"a":1,"a":2}'); m.load(p)


if __name__ == '__main__':
    unittest.main()
