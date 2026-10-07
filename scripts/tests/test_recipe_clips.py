"""Synthetic clip lifecycle and manual-picker protection tests; no culinary verdicts."""
import copy,importlib.util,json,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
import test_recipe_batch as fixtures
m=fixtures.m
spec=importlib.util.spec_from_file_location('picker',m.ROOT/'scripts/recipe-media-server.py');picker=importlib.util.module_from_spec(spec);spec.loader.exec_module(picker)

class ClipChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.BatchChecks.setUpClass()
 @classmethod
 def tearDownClass(cls):fixtures.BatchChecks.tearDownClass()
 def setUp(self):
  self.f=fixtures.BatchChecks();self.f.setUp();self.f.queue.close();self.f.queue=m.Queue(self.f.root/'clip-queue');self.q=self.f.queue
  self.q.add(self.f.manifest,{**self.f.config,'media_mode':'clips'})
 def tearDown(self):self.f.tearDown()
 def complete(self,multi=False):
  self.q.run();folder=self.f.pending('extract');draft=self.f.draft(folder)
  if multi:draft['steps'][0]['evidence_windows'].append({'start':3,'end':4})
  self.f.send(folder,draft);self.q.run();folder=self.f.pending('review');self.f.send(folder,{'stage':'review','fact_reviews':[{'fact_id':'fact_one','verdict':'needs_review','reason':'synthetic','evidence_ids':['ev_one']}],'issues':[]});self.q.run()
  row=self.q.db.execute('SELECT * FROM jobs').fetchone();self.assertEqual(row['status'],'complete',row['error'])
  self.assertFalse(self.q.db.execute("SELECT 1 FROM tasks WHERE stage LIKE 'select_%' OR stage LIKE 'review_visual_%'").fetchone())
  return next(p.parent for p in (self.q.root/'stages').glob('*/step-clips.json') if (p.parent/'recipe.internal.json').exists())
 def test_clip_windows_cover_fact_subtitles_and_preserve_real_gaps(self):
  clips=m.library_module().clips_module();step={'id':'step','evidence_windows':[{'start':10,'end':12}],'facts':[{'evidence_ids':['one','two']}]};evidence=[{'id':'one','kind':'subtitle','interval':{'start':13,'end':20}},{'id':'two','kind':'subtitle','interval':{'start':90,'end':94}}]
  self.assertEqual(clips.windows(step,100,5,evidence),[{'start':5,'end':25},{'start':85,'end':99}])

 def test_multiple_windows_no_vision_and_recovery(self):
  folder=self.complete(True);manifest=m.load(folder/'step-clips.json');self.assertEqual(len(manifest['clips']),2)
  self.assertEqual([(x['start'],x['end']) for x in manifest['clips']],[(0,2),(3,4)])
  before=m.artifacts(folder)
  with patch.object(m.subprocess,'run',side_effect=AssertionError('re-encode')):self.q.run()
  self.assertEqual(before,m.artifacts(folder));m.library_module().validate(folder,m.load(m.CONTRACTS/'video-recipe.schema.json'))
 def test_ready_clip_recipe_release_gate_and_rebuild_without_source(self):
  self.q.close();entry=m.load(self.f.manifest);entry[0]['subtitle_origin']='platform';self.f.manifest=self.f.root/'platform-manifest.json';m.write(self.f.manifest,entry);self.f.queue=m.Queue(self.f.root/'platform-queue');self.q=self.f.queue;self.q.add(self.f.manifest,{**self.f.config,'media_mode':'clips'})
  self.q.run();folder=self.f.pending('extract');self.f.send(folder,self.f.draft(folder));self.q.run();folder=self.f.pending('review')
  self.f.send(folder,{'stage':'review','fact_reviews':[{'fact_id':'fact_one','verdict':'supported','reason':'synthetic explicit subtitle','evidence_ids':['ev_one']}],'ingredient_reviews':[{'ingredient_id':'ing_tofu','verdict':'supported','reason':'synthetic explicit subtitle','evidence_ids':['ev_one']}],'issue_reviews':[{'issue_id':'issue_pending','resolution':'resolved','reason':'synthetic source covers both','evidence_ids':['ev_one']}],'repair_requests':[],'issues':[]});self.q.run()
  flow=picker.flow.Flow(self.f.root/'lifecycle')
  try:
   flow.init(self.f.video.parent,min_free_gib=0,media_mode='clips');flow.adopt(self.q.root,'BVTest123');gate=flow.release('BVTest123');self.assertTrue(gate['eligible']);self.assertTrue(self.f.video.exists())
   with patch.object(picker.flow.batch,'probe',side_effect=AssertionError('must not open original video')),patch.object(picker.flow.batch,'Queue',side_effect=AssertionError('must not recreate AI queue')):flow.rebuild(self.f.root/'reconstructed')
   self.assertTrue(list((self.f.root/'reconstructed').glob('recipes/*/clips/*.mp4')))
   archived=Path(flow.row('BVTest123')['archive']);proposal=m.load(archived/'recipe.internal.json');proposal['steps'][0]['evidence_windows'].append({'start':3,'end':4});proposal_path=self.f.root/'proposal.json';m.write(proposal_path,proposal)
   prepared=self.f.root/'revision';flow.prepare_revision('BVTest123',proposal_path,prepared,'synthetic-revision');self.assertEqual(len(m.load(prepared/'step-clips.json')['clips']),2)
   self.assertEqual(len(m.load(archived/'step-clips.json')['clips']),1)
   published=flow.root/'library/recipes/BVTest123';manifest=m.load(published/'step-clips.json');(published/manifest['clips'][0]['file']).write_bytes(b'changed')
   with self.assertRaises(ValueError):flow.release('BVTest123')
  finally:flow.close()

 def test_tampered_clip_and_missing_window_fail(self):
  folder=self.complete();schema=m.load(m.CONTRACTS/'video-recipe.schema.json');clips=m.load(folder/'step-clips.json');path=folder/clips['clips'][0]['file'];path.write_bytes(b'bad')
  with self.assertRaises(ValueError):m.library_module().validate(folder,schema)
 def test_picker_persists_outside_immutable_recipe_and_guards_inputs(self):
  folder=self.complete();out=self.f.root/'flow/library';self.q.build(out,m.ROOT/'config/recipe/ingredients.json');store=picker.Store(self.f.root/'flow');key='BVTest123';before=m.artifacts(out);state=store.get(key);clip=m.load(out/'recipes'/key/'step-clips.json')['clips'][0]
  state['steps']['step_one']={'mode':'both','frames':[{'clip_id':clip['id'],'time':.5},{'clip_id':clip['id'],'time':1.0}]};store.put(key,state);self.assertEqual(state,picker.Store(store.root).get(key));self.assertEqual(before,m.artifacts(out))
  images=list((store.root/'user-media'/key).glob('*.jpg'));self.assertEqual(len(images),2)
  for change in ['old','negative','outside','wrong_clip','empty']:
   bad=copy.deepcopy(state)
   if change=='old':bad['recipe_sha256']='0'*64
   elif change=='negative':bad['steps']['step_one']['frames'][0]['time']=-1
   elif change=='outside':bad['steps']['step_one']['frames'][0]['time']=100
   elif change=='wrong_clip':bad['steps']['step_one']['frames'][0]['clip_id']='../../escape'
   else:bad['steps']['step_one']={'mode':'images','frames':[]}
   with self.assertRaises(ValueError):store.put(key,bad)
  # Actual HTTP writes require matching Origin and Host, including local requests.
  server=picker.ThreadingHTTPServer(('127.0.0.1',0),picker.handler(store));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}/api/recipes/{key}/media'
  try:
   req=urllib.request.Request(url,data=json.dumps(state).encode(),method='PUT',headers={'Origin':'http://evil.example'})
   with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
   req=urllib.request.Request(url,data=json.dumps(state).encode(),method='PUT',headers={'Origin':f'http://127.0.0.1:{server.server_port}'})
   self.assertEqual(json.load(urllib.request.urlopen(req)),state)
   page=url.replace('/api/recipes/','/recipes/').replace('/media','/recipe.html');self.assertIn(b'window.__recipeMediaState=',urllib.request.urlopen(page).read())
   frame_url=url.replace('/media','/frames/'+clip['id']+'/0.500.jpg');self.assertTrue(urllib.request.urlopen(frame_url).read().startswith(b'\xff\xd8'))
  finally:server.shutdown();server.server_close();thread.join()
