"""Synthetic review transitions test evidence/state guards, not culinary quality."""
import unittest
import test_recipe_batch as fixture
m = fixture.m


class ReviewChecks(unittest.TestCase):
    setUpClass = classmethod(fixture.BatchChecks.setUpClass.__func__)
    tearDownClass = classmethod(fixture.BatchChecks.tearDownClass.__func__)
    setUp = fixture.BatchChecks.setUp
    tearDown = fixture.BatchChecks.tearDown
    pending = fixture.BatchChecks.pending
    envelope = fixture.BatchChecks.envelope
    send = fixture.BatchChecks.send
    draft = fixture.BatchChecks.draft
    selection = fixture.BatchChecks.selection

    def start(self):
        self.queue.run(); folder = self.pending('extract')
        recipe = self.draft(folder); self.send(folder, recipe); self.queue.run()
        return recipe

    def review(self, recipe, repairs=None):
        return {'stage': 'review', 'fact_reviews': [{'fact_id': f['id'], 'verdict': 'supported', 'reason': 'synthetic', 'evidence_ids': ['ev_one']} for s in recipe['steps'] for f in s['facts']], 'ingredient_reviews': [{'ingredient_id': i['id'], 'verdict': 'supported', 'reason': 'synthetic unknown quantity retained', 'evidence_ids': ['ev_one']} for i in recipe['ingredients']], 'issue_reviews': [{'issue_id': i['id'], 'resolution': 'resolved', 'reason': 'synthetic', 'evidence_ids': ['ev_one']} for i in recipe['issues']], 'issues': [], 'repair_requests': repairs or []}

    def test_ingredient_coverage_and_positive_evidence_required(self):
        recipe = self.start(); folder = self.pending('review')
        result = self.review(recipe); result['ingredient_reviews'] = []
        with self.assertRaisesRegex(ValueError, 'ingredient_id'): self.send(folder, result)
        result = self.review(recipe); result['ingredient_reviews'][0]['evidence_ids'] = []
        with self.assertRaisesRegex(ValueError, 'positive review'): self.send(folder, result)
        self.send(folder, self.review(recipe)); self.queue.run()
        payload = m.load(self.pending('select_step_one')/'payload.json')
        self.assertIsNone(payload['ingredients'][0]['quantity']['min'])

    def test_repair_rejects_self_certification_and_unrequested_targets(self):
        recipe = self.start(); helper = m.review_module()
        for target, field, value in [('ing_tofu', 'review_status', 'supported'), ('step_one', 'selected_frame_id', 'invented'), ('ing_tofu', 'name', 'another')]:
            with self.assertRaisesRegex(ValueError, 'whitelist'):
                helper.apply_repair(recipe, {'changes': [{'target_id': target, 'field': field, 'value': value}], 'issue_updates': []}, ['fact_one'])
        changed = helper.apply_repair(recipe, {'changes': [{'target_id': 'fact_one', 'field': 'text', 'value': '翻炒豆腐'}], 'issue_updates': []}, ['fact_one'])
        self.assertEqual(changed['steps'][0]['facts'][0]['review_status'], 'needs_review')
        self.assertEqual(changed['evidence'], recipe['evidence']); self.assertFalse(changed['human_reviewed'])

    def test_repair_requires_independent_review_and_stops_after_two(self):
        self.start()
        for attempt in range(3):
            folder = self.pending('review' if attempt == 0 else 'review_text_'+str(attempt))
            recipe = m.load(folder/'payload.json')['recipe']
            self.send(folder, self.review(recipe, [{'target_id': 'fact_one', 'reason': 'synthetic repair loop'}])); self.queue.run()
            if attempt < 2:
                repair = self.pending('repair_text_'+str(attempt+1))
                self.send(repair, {'stage': 'repair', 'changes': [{'target_id': 'fact_one', 'field': 'text', 'value': '翻炒豆腐', 'reason':'synthetic correction'}], 'issue_updates': []}); self.queue.run()
        selection = self.pending('select_step_one'); self.send(selection, self.selection(selection)); self.queue.run()
        assembled = next(self.queue.root.glob('stages/*/recipe.internal.json'))
        recipe = m.load(assembled)
        self.assertTrue(any(i['id']=='issue_repair_limit_text' and i['resolution']=='open' for i in recipe['issues']))
        self.assertEqual(recipe['status'], 'needs_review')
        output = self.root/'repair-library'; self.queue.build(output,m.ROOT/'config/recipe/ingredients.json')
        m.library_module().validate(output/'recipes/BVTest123',m.load(m.CONTRACTS/'video-recipe.schema.json'))

    def test_visual_observation_becomes_actual_frame_evidence_and_rereview(self):
        recipe = self.start(); self.send(self.pending('review'), self.review(recipe)); self.queue.run()
        folder = self.pending('select_step_one'); result = self.selection(folder)
        frame = m.load(folder/'payload.json')['candidates'][0]
        result['observations'] = [{'target_id': 'fact_one', 'frame_id': frame['id'], 'observation': '合成测试画面观察', 'verdict': 'needs_review'}]
        self.send(folder, result); self.queue.run()
        folder = self.pending('review_visual_0'); recipe = m.load(folder/'payload.json')['recipe']
        evidence = next(e for e in recipe['evidence'] if e['kind']=='frame')
        self.assertEqual(evidence['frame_id'], frame['id']); self.assertEqual(evidence['interval']['start'], frame['timestamp'])
        self.assertEqual(recipe['steps'][0]['facts'][0]['text'], '豆腐翻炒')
        self.assertFalse(recipe['human_reviewed']); self.assertTrue(m.load(folder/'packet.json')['image_inputs'])
        self.send(folder, self.review(recipe)); self.assertEqual(self.queue.run()['counts'], {'complete':1})

    def test_missing_image_cannot_be_resolved_without_selected_frame(self):
        recipe = self.start()
        recipe['issues'].append({'id':'issue_image', 'code':'missing_image', 'target_ids':['step_one'], 'description':'missing', 'evidence_ids':[], 'resolution':'open', 'resolution_note':None})
        with self.assertRaisesRegex(ValueError, 'actual selected frame'):
            m.review_module().validate_review(recipe, self.review(recipe))

if __name__ == '__main__': unittest.main()
