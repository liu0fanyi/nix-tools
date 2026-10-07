"""Synthetic structural fixtures; these tests do not claim visual or recipe correctness."""
from pathlib import Path
import copy,importlib.util,json,tempfile,unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recipe',ROOT/'recipe-library.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RecipeChecks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)/'inputs'/'BV1RXaD6DELQ';self.folder.mkdir(parents=True)
  self.schema=m.read(m.CONTRACTS/'video-recipe.schema.json');self.data=m.read(m.CONTRACTS/'video-recipe.example.json')
  cues=m.read(m.CONTRACTS/'transcript.example.json')['cues']
  def ts(t):
   whole=int(t);return f'{whole//3600:02}:{whole//60%60:02}:{whole%60:02},{round((t-whole)*1000):03}'
  text='\n\n'.join(f'{c["id"]}\n{ts(c["start"])} --> {ts(c["end"])}\n{c["text"]}'for c in cues)+'\n';(self.folder/'source.srt').write_text(text)
  sha=m.digest(self.folder/'source.srt');m.dump(self.folder/'transcript.json',{'transcript_sha256':sha,'cues':cues})
  d=self.data;d['source']['transcript_sha256']=sha;d['coverage']='full';d['covered_intervals']=[{'start':0,'end':d['source']['duration_seconds']}]
  d['issues'][0]['description']='Synthetic test fixture, not a recipe delivery.'
  (self.folder/'images').mkdir();Image.new('RGB',(16,9)).save(self.folder/'images/218.jpg')
  d['frames'][0].update(sha256=m.digest(self.folder/'images/218.jpg'),width=16,height=9)
  m.dump(self.folder/'candidates.json',[]);m.dump(self.folder/'processing.json',{'synthetic':True})
  m.dump(self.folder/'semantic-review.json',{'stage':'review','fact_reviews':[{'fact_id':'fact_duration','verdict':'needs_review','reason':'test fixture pending review','evidence_ids':['ev_93']}],'issues':[]})
  m.dump(self.folder/'image-selection.json',[{'stage':'select_images','step_id':'step_simmer','candidate_reviews':d['image_reviews'],'selected_frame_id':'frame_218','no_image_reason':None,'observations':[]}]);self.save()
 def tearDown(self):self.temp.cleanup()
 def save(self):m.dump(self.folder/'recipe.internal.json',self.data)
 def test_valid_fixture_then_reject_fabricated_quote(self):
  m.validate(self.folder,self.schema)
  self.data['evidence'][0]['quote']='invented';self.save()
  with self.assertRaisesRegex(ValueError,'quote'):m.validate(self.folder,self.schema)
 def test_millisecond_srt_normalization_agrees_and_rejects_real_changes(self):
  # 01:33,700 + 3.230 formerly differed from integer-seconds parsing by one ULP.
  transcript=m.read(self.folder/'transcript.json')
  cue={'id':999,'start':93.7,'end':97.23,'text':'真实毫秒时间轴合成测试'}
  transcript['cues'].append(cue)
  with (self.folder/'source.srt').open('a')as stream:stream.write('\n999\n00:01:33,700 --> 00:01:37,230\n真实毫秒时间轴合成测试\n')
  sha=m.digest(self.folder/'source.srt');self.data['source']['transcript_sha256']=sha;transcript['transcript_sha256']=sha
  m.dump(self.folder/'transcript.json',transcript);self.save();m.validate(self.folder,self.schema)
  transcript['cues'][-1]['end']=97.231;m.dump(self.folder/'transcript.json',transcript)
  with self.assertRaisesRegex(ValueError,'normalized transcript'):m.validate(self.folder,self.schema)
 def test_changed_image_and_dependency_cycle_rejected(self):
  self.data['steps'][0]['depends_on']=['step_simmer'];self.save()
  with self.assertRaisesRegex(ValueError,'dependency'):m.validate(self.folder,self.schema)
  self.data['steps'][0]['depends_on']=[];self.save();(self.folder/'images/218.jpg').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'image changed'):m.validate(self.folder,self.schema)
 def test_missing_image_and_partial_coverage_rejected(self):
  self.data['steps'][0]['selected_frame_id']=None;self.data['steps'][0]['no_image_reason']='no image';self.save()
  with self.assertRaisesRegex(ValueError,'empty image'):m.validate(self.folder,self.schema)
  self.data['steps'][0]['selected_frame_id']='frame_218';self.data['steps'][0]['no_image_reason']=None;self.data['coverage']='partial';self.save()
  with self.assertRaisesRegex(ValueError,'partial'):m.validate(self.folder,self.schema)
 def test_existing_output_preserved_and_export_agrees(self):
  output=Path(self.temp.name)/'output';output.mkdir();(output/'keep').write_text('keep')
  with self.assertRaisesRegex(ValueError,'already exists'):m.build(self.folder.parent,output,m.ROOT/'config/recipe/ingredients.json')
  self.assertEqual((output/'keep').read_text(),'keep')
  page,data=m.render_recipe(self.data,self.folder)
  self.assertEqual(len(data['recipeInstructions']),1);self.assertIn('6分钟',page)
 def test_unstructured_quantity_keeps_source_words_in_both_exports(self):
  self.data['ingredients'][0]['quantity']={'mode':'unspecified','min':None,'max':None,'unit':None,'original':'一斤二两'}
  page,data=m.render_recipe(self.data,self.folder)
  self.assertIn('用量待核对；原文：一斤二两',page)
  self.assertTrue(any('一斤二两'in x for x in data['recipeIngredient']))
  self.assertIsNone(self.data['ingredients'][0]['quantity']['min'])
 def test_rebuild_from_a_previous_output_retains_verifiable_history(self):
  first=Path(self.temp.name)/'first';second=Path(self.temp.name)/'second';dictionary=m.ROOT/'config/recipe/ingredients.json'
  m.build(self.folder.parent,first,dictionary);m.validate(first/'recipes'/'BV1RXaD6DELQ',self.schema)
  m.build(first/'recipes',second,dictionary);m.validate(second/'recipes'/'BV1RXaD6DELQ',self.schema)
  self.assertGreater(len(list((second/'recipes'/'BV1RXaD6DELQ').glob('recipe-input*.json'))),1)
 def test_text_cannot_expand_template_or_scripts(self):
  self.data['title']='{{STEPS}}</script><script>evil()</script>'
  page,_=m.render_recipe(self.data,self.folder)
  self.assertIn('{{STEPS}}&lt;/script&gt;',page);self.assertNotIn('<script>evil()',page)

if __name__=='__main__':unittest.main()
