"""Task views and real-response accounting; synthetic logs only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from jsonschema import Draft202012Validator
import test_recipe_batch as fixtures

spec=importlib.util.spec_from_file_location('session',Path(__file__).resolve().parents[1]/'recipe-session.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class SessionChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.logs=self.root/'sessions';self.logs.mkdir()
    def tearDown(self):self.temp.cleanup()
    def register(self,stage='extract',agent='/root/session_extract'):
        s.register(self.root,stage,agent,['abc123'])
    def log(self,name,agent,thread,usages):
        values=[{'type':'session_meta','payload':{'id':thread,'agent_path':agent}}]
        for response,usage,own_thread in usages:
            values.append({'type':'token_usage_record','payload':{'response_id':response,'thread_id':own_thread or thread,'usage':usage}})
        (self.logs/name).write_text(''.join(json.dumps(x)+'\n' for x in values))
    def usage(self,n=100):return {'input_tokens':n,'cached_input_tokens':80,'output_tokens':20,'reasoning_output_tokens':5,'total_tokens':n+20}
    def test_deduplicates_responses_counts_failures_and_excludes_inherited_other_threads(self):
        self.register();u=self.usage()
        self.log('one.jsonl','/root/session_extract','leaf',[('a',u,None),('a',u,None),('old',self.usage(999), 'parent'),('retry',self.usage(120),None)])
        self.log('two.jsonl','/root/session_extract','leaf',[('a',u,None)])
        result=s.report(self.root,self.logs,None)
        self.assertEqual(result['status'],'measured');self.assertEqual(result['stages'][0]['calls'],2)
        self.assertEqual(result['usage']['total_tokens'],260);self.assertEqual(result['uncached_input_tokens'],60)
        self.assertEqual(result['usage']['reasoning_output_tokens'],10)
    def test_missing_usage_is_not_reported_as_zero_measured_cost(self):
        self.register();result=s.report(self.root,self.logs,None)
        self.assertEqual(result['status'],'incomplete');self.assertEqual(result['missing_stages'],['extract'])
    def test_reused_worker_and_conflicting_records_are_rejected(self):
        self.register();self.log('one.jsonl','/root/session_extract','leaf',[('a',self.usage(),None),('a',self.usage(120),None)])
        with self.assertRaises(ValueError):s.report(self.root,self.logs,None)
        s.register(self.root,'review','/root/session_extract',['different'])
        with self.assertRaises(ValueError):s.report(self.root,self.logs,None)
    def test_usage_counter_invariants_are_enforced(self):
        self.register();u=self.usage();u['cached_input_tokens']=101
        self.log('one.jsonl','/root/session_extract','leaf',[('a',u,None)])
        with self.assertRaises(ValueError):s.report(self.root,self.logs,None)
    def test_registration_and_report_preserve_immutable_bindings(self):
        self.register();self.register()
        with self.assertRaises(ValueError):s.register(self.root,'extract','/root/other',['abc123'])
        self.log('one.jsonl','/root/session_extract','leaf',[('a',self.usage(),None)])
        dest=self.root/'report.json';s.report(self.root,self.logs,dest)
        with self.assertRaises(FileExistsError):s.report(self.root,self.logs,dest)
    def test_review_projection_keeps_all_semantics_and_cues_without_run_candidate_history(self):
        payload={'transcript':{'cues':[{'id':1,'text':'原文'}]},'recipe':{'evidence':[{'kind':'frame','frame_id':'f1'}], 'steps':[{'selected_frame_id':'f2','facts':[{'id':'fact'}]}], 'ingredients':[{'id':'food'}], 'variants':[], 'issues':[{'target_ids':['f3']}], 'frames':[{'id':x} for x in ['f1','f2','f3','unused']], 'runs':[{'long':'history'}], 'image_reviews':[{'long':'candidate history'}]}}
        result=s.projection(payload,'review')
        for key in ['steps','ingredients','variants','issues','evidence']:self.assertEqual(payload['recipe'][key],result['recipe'][key])
        self.assertEqual(payload['transcript'],result['transcript']);self.assertEqual(len(result['recipe']['frames']),3)
        self.assertEqual(result['recipe']['runs'],[]);self.assertEqual(len(payload['recipe']['frames']),4)
    def test_selection_projection_keeps_window_neighbors_and_relevant_issues(self):
        payload={'step':{'id':'step','facts':[{'id':'fact'}],'evidence_windows':[{'start':30,'end':32}]},'ingredients':[{'id':'food'}], 'recipe_issues':[{'target_ids':['food']},{'target_ids':['other']}], 'transcript':{'cues':[{'id':i,'start':i,'end':i+1,'text':str(i)} for i in range(100)]}}
        result=s.projection(payload,'select_images');ids=[c['id'] for c in result['transcript']['cues']]
        self.assertIn(30,ids);self.assertIn(32,ids);self.assertIn(22,ids);self.assertIn(39,ids);self.assertNotIn(90,ids)
        self.assertEqual(len(result['recipe_issues']),1);self.assertEqual(len(payload['transcript']['cues']),100)
    def test_prepare_binds_original_digest_preserves_source_and_rejects_modified_checkpoint(self):
        packets=self.root/'original';original=packets/'abc123';original.mkdir(parents=True)
        payload={'source':{'video_id':'BVTest'},'transcript':{'cues':[{'id':1,'text':'完整原文'}]}}
        packet={'task_id':'abc123','job_id':'BVTest','stage':'extract','input_sha256':s.batch.sha(payload),'image_inputs':[],'output_envelope':{'task_id':'abc123'}}
        s.flow.immutable(original/'payload.json',payload);s.flow.immutable(original/'packet.json',packet)
        s.flow.immutable(original/'checksums.json',s.batch.artifacts(original))
        result=s.prepare(packets,self.root/'compact');task=s.batch.load(Path(result['tasks'][0]['folder'])/'task.json')
        self.assertEqual(task['input_sha256'],packet['input_sha256']);self.assertEqual(task['payload'],payload)
        s.batch.verify(original);s.batch.verify(Path(result['tasks'][0]['folder']))
        with self.assertRaises(ValueError):s.prepare(packets,packets/'nested')
        (original/'payload.json').write_text('{}')
        with self.assertRaises(ValueError):s.prepare(packets,self.root/'bad-view')
        self.assertFalse((self.root/'bad-view').exists())

    def test_corrupt_complete_usage_records_rejected_partial_tail_not_counted(self):
        self.register();self.log('one.jsonl','/root/session_extract','leaf',[('a',self.usage(),None)])
        path=self.logs/'one.jsonl'
        with path.open('a') as stream:stream.write('{unfinished')
        self.assertEqual(s.report(self.root,self.logs,None)['usage']['total_tokens'],120)
        with path.open('a') as stream:stream.write('\n')
        with self.assertRaises(ValueError):s.report(self.root,self.logs,None)

    def test_read_only_preflight_checks_semantic_quantity_and_response_binding(self):
        original=self.root/'original'/'abc123';original.mkdir(parents=True)
        source={'platform':'bilibili','video_id':'BVTest123','url':'https://www.bilibili.com/video/BVTest123','author':'test','duration_seconds':2,'transcript_sha256':'0'*64,'subtitle_origin':'platform'}
        payload={'source':source,'recipe_id':'recipe_bvtest123','transcript':{'transcript_sha256':'0'*64,'cues':[{'id':1,'start':0,'end':2,'text':'豆腐翻炒'}]}}
        packet={'task_id':'abc123','job_id':'BVTest123','stage':'extract','input_sha256':s.batch.sha(payload),'image_inputs':[],'output_envelope':{}}
        s.flow.immutable(original/'payload.json',payload);s.flow.immutable(original/'packet.json',packet)
        recipe=fixtures.BatchChecks().draft(original)
        s.flow.immutable(original/'checksums.json',s.batch.artifacts(original));s.prepare(original.parent,self.root/'compact')
        view=self.root/'compact/abc123';response=self.root/'response.json'
        body={'task_id':'abc123','input_sha256':packet['input_sha256'],'processor':'synthetic-only','model':None,'result':recipe}
        s.flow.atomic(response,body);before=s.batch.artifacts(original)
        self.assertTrue(s.validate_view(view,response)['validated']);self.assertEqual(s.batch.artifacts(original),before)
        body['result']['ingredients'][0]['quantity'].update(mode='exact',unit='克')
        s.flow.atomic(response,body)
        with self.assertRaisesRegex(ValueError,'invalid quantity mode'):s.validate_view(view,response)
        body['input_sha256']='1'*64;s.flow.atomic(response,body)
        with self.assertRaisesRegex(ValueError,'response binding mismatch'):s.validate_view(view,response)

    def test_standalone_stage_schemas_keep_full_review_and_original_image_enums(self):
        for stage in ['extract','review','repair','select_images']:Draft202012Validator.check_schema(s.output_schema(stage))
        schema=s.output_schema('review');self.assertIn('ingredient_reviews',schema['required']);self.assertIn('issue_reviews',schema['required'])
        self.assertNotIn('video-recipe.schema.json',json.dumps(schema))

if __name__=='__main__':unittest.main()
