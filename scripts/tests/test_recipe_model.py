"""Local mock HTTP tests, never an external AI or paid request."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest import mock
import test_recipe_batch as fixtures

m = fixtures.m
spec = importlib.util.spec_from_file_location('model', m.ROOT / 'scripts/recipe-model.py')
api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)


class ModelChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixtures.BatchChecks.setUpClass()
    @classmethod
    def tearDownClass(cls): fixtures.BatchChecks.tearDownClass()

    def setUp(self):
        self.f = fixtures.BatchChecks('test_single_writer_and_live_read_only_status'); self.f.setUp()
        self.q = self.f.queue; self.q.run(); self.draft = self.f.draft(self.f.pending('extract'))
        self.requests = []; self.behavior = 'normal'
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                outer.requests.append(body)
                if outer.behavior == 'authentication':
                    self.send_response(401); self.end_headers(); self.wfile.write(b'private-error'); return
                if outer.behavior == 'rate_limit_once' and len(outer.requests) == 1:
                    self.send_response(429); self.end_headers(); return
                if outer.behavior == 'timeout': time.sleep(2)
                stage = body['text']['format']['name'].removeprefix('recipe_')
                payload = json.loads(body['input'][0]['content'][0]['text'])
                if stage == 'extract':
                    result = copy.deepcopy(outer.draft); result['source'] = payload['source']; result['recipe_id'] = payload['recipe_id']
                elif stage == 'review':
                    recipe = payload['recipe']; facts = [f for s in recipe['steps'] + recipe['variants'] for f in s['facts']]
                    result = {'stage': 'review', 'fact_reviews': [{'fact_id': f['id'], 'verdict': 'supported', 'reason': 'synthetic contract test', 'evidence_ids': f['evidence_ids']} for f in facts], 'ingredient_reviews': [{'ingredient_id': i['id'], 'verdict': 'supported', 'reason': 'unspecified is preserved in synthetic test', 'evidence_ids': i['evidence_ids']} for i in recipe['ingredients']], 'issue_reviews': [{'issue_id': i['id'], 'resolution': 'resolved', 'reason': 'synthetic contract test only', 'evidence_ids': ['ev_one']} for i in recipe['issues']], 'repair_requests': [], 'issues': []}
                else:
                    result = {'stage': 'select_images', 'step_id': payload['step']['id'], 'candidate_reviews': [{'step_id': payload['step']['id'], 'frame_id': f['id'], 'relevance': 'matches', 'quality': 'usable', 'reason': 'synthetic visual fixture only'} for f in payload['candidates']], 'selected_frame_id': payload['candidates'][0]['id'], 'no_image_reason': None, 'observations': []}
                if outer.behavior == 'malformed_result': result = {'bad': True}
                raw = {'id': 'resp-test-' + str(len(outer.requests)), 'model': 'test-model', 'status': 'completed', 'usage': {'input_tokens': 100, 'output_tokens': 50}, 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(result, ensure_ascii=False)}]}]}
                if outer.behavior == 'missing_usage': raw.pop('usage')
                if outer.behavior == 'refusal': raw['output'][0]['content'] = [{'type': 'refusal', 'refusal': 'synthetic refusal'}]
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                try: self.wfile.write(json.dumps(raw).encode())
                except BrokenPipeError: pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.config = {'protocol': 'responses', 'endpoint': f'http://127.0.0.1:{self.server.server_port}/v1/responses', 'api_key_env': None, 'models': {s: 'test-model' for s in ('extract', 'review', 'vision', 'repair')}, 'vision_models': ['test-model'], 'reasoning_effort': None, 'allow_text': True, 'allow_images': True, 'max_input_tokens': 1_000_000, 'max_output_tokens': 2000, 'image_token_ceiling': 16384, 'timeout_seconds': 5, 'max_attempts': 3, 'max_total_usd': .1, 'max_video_usd': .1, 'input_usd_per_million': .001, 'output_usd_per_million': .001}

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.f.tearDown()

    def runner(self, **changes): return api.Runner(self.q, {**self.config, **changes}, vars(m))

    def test_full_pipeline_real_image_request_and_resume_no_repeat(self):
        runner = self.runner(); result = runner.run(max_calls=10, execute=True)
        self.assertFalse(result['pauses']); self.assertEqual(result['new_requests'], 3); self.assertEqual(result['jobs'], {'complete': 1})
        image_request = self.requests[-1]['input'][0]['content']
        self.assertTrue(any(x['type'] == 'input_image' and x['image_url'].startswith('data:image/jpeg;base64,') for x in image_request))
        self.assertTrue(all(not request['store'] for request in self.requests))
        self.assertEqual(self.runner().run(max_calls=10, execute=True)['new_requests'], 0)
        output = self.f.root / 'model-library'; self.q.build(output, m.ROOT / 'config/recipe/ingredients.json')
        processing = m.load(output / 'recipes/BVTest123/processing.json'); self.assertEqual(len(processing['model_calls']), 3)
        recipe = m.load(output / 'recipes/BVTest123/recipe.internal.json'); self.assertEqual(recipe['status'], 'ready'); self.assertFalse(recipe['human_reviewed']); self.assertIsNone(recipe['ingredients'][0]['quantity']['min'])
        self.assertEqual(m.digest(self.f.video), self.f.source_digest)
        m.library_module().build(output / 'recipes', self.f.root / 'rebuilt', m.ROOT / 'config/recipe/ingredients.json')

    def test_dry_run_upload_and_budget_guards_make_no_request(self):
        self.assertTrue(self.runner().run(execute=False)['preview']); self.assertEqual(len(self.requests), 0)
        blocked = self.runner(allow_text=False).run(execute=True); self.assertEqual(blocked['pauses'][0]['reason'], 'upload_scope_not_enabled'); self.assertEqual(len(self.requests), 0)
        blocked = self.runner(max_total_usd=0).run(execute=True); self.assertEqual(blocked['pauses'][0]['reason'], 'positive_budget_and_rates_required'); self.assertEqual(len(self.requests), 0)
        blocked = self.runner(max_total_usd=.000001).run(execute=True); self.assertEqual(blocked['pauses'][0]['reason'], 'budget_limit'); self.assertEqual(len(self.requests), 0)

    def test_bounded_invalid_result_and_rate_limit_retries_account_attempts(self):
        self.behavior = 'rate_limit_once'
        with mock.patch.object(api.time, 'sleep'):
            result = self.runner().run(max_calls=4, execute=True)
        self.assertEqual(result['jobs'], {'complete': 1}); self.assertEqual(len(self.requests), 4)
        self.assertGreater(result['budget']['unsettled_reservations_usd'], 0)
        self.assertFalse(result['pauses']); self.assertEqual(len(result['retry_events']),1)

    def test_invalid_results_stop_after_three_requests(self):
        self.behavior = 'malformed_result'
        with mock.patch.object(api.time, 'sleep'):
            result = self.runner().run(max_calls=10, execute=True)
        self.assertEqual(len(self.requests), 3); self.assertEqual(result['pauses'][-1]['reason'], 'attempt_limit')
        self.assertEqual(result['jobs'], {'waiting_extract': 1})

    def test_timeout_and_missing_usage_never_blindly_repeat(self):
        self.behavior = 'timeout'; result = self.runner(timeout_seconds=1).run(execute=True)
        self.assertEqual(result['pauses'][0]['reason'], 'uncertain_transport')
        again = self.runner().run(execute=True); self.assertEqual(again['new_requests'], 0); self.assertEqual(len(self.requests), 1)

    def test_missing_usage_and_refusal_pause_with_no_followup_requests(self):
        self.behavior = 'missing_usage'
        result = self.runner().run(execute=True); self.assertEqual(result['pauses'][0]['reason'], 'missing_usage_reservation_retained')
        self.assertGreater(result['budget']['unsettled_reservations_usd'], 0)
        self.assertEqual(self.runner().run(execute=True)['new_requests'], 0)

    def test_received_response_recovery_does_not_call_server(self):
        runner = self.runner(); real = runner.accept
        def crash(*args): raise SystemExit('simulated kill after durable response')
        runner.accept = crash
        with self.assertRaises(SystemExit): runner.run(execute=True)
        self.assertEqual(len(self.requests), 1)
        resumed = self.runner(input_usd_per_million=.002, output_usd_per_million=.002).run(max_calls=1, execute=True)
        self.assertEqual(resumed['new_requests'], 1)  # cached extraction recovered, only the review calls the server
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(resumed['jobs'], {'waiting_images': 1})
        receipt = self.q.db.execute('SELECT actual FROM model_calls ORDER BY rowid LIMIT 1').fetchone()
        self.assertEqual(receipt['actual'],150)  # original rates survive a configuration change

    def test_schema_adapter_closed_objects_and_repair_wire_values(self):
        for stage in ('extract', 'review', 'select_images', 'repair'):
            schema = api.wire_schema(stage, m.CONTRACTS)
            self.assertEqual(schema['type'], 'object'); self.assertNotIn('oneOf', schema); self.assertNotIn('$ref', json.dumps(schema))
            def check(node):
                if isinstance(node, dict):
                    if node.get('type') == 'object':
                        self.assertFalse(node['additionalProperties']); self.assertEqual(set(node['properties']), set(node['required']))
                    for v in node.values(): check(v)
                elif isinstance(node, list):
                    for v in node: check(v)
            check(schema)
        self.assertIn('value_json', api.wire_schema('repair', m.CONTRACTS)['properties']['changes']['items']['properties'])

    def test_credentials_never_saved_and_remote_http_rejected(self):
        self.behavior = 'authentication'; secret = 'test-secret-not-real'
        with mock.patch.dict(os.environ, {'RECIPE_TEST_KEY': secret}):
            result = self.runner(api_key_env='RECIPE_TEST_KEY').run(execute=True)
        self.assertEqual(result['pauses'][0]['reason'], 'authentication')
        for path in self.q.root.rglob('*'):
            if path.is_file(): self.assertNotIn(secret.encode(), path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            self.runner(endpoint='http://example.com/v1/responses')
        self.assertEqual(api.redact({'k': secret}, secret), {'k': '[redacted]'})


if __name__ == '__main__': unittest.main()
