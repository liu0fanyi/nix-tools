import importlib.util,unittest,io,tempfile,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('ocr',str(Path(__file__).resolve().parents[1]/'video-subtitle-ocr.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_short_pipe_reads_and_truncation(self):
  class Stream:
   def __init__(self):self.items=iter([b'a',b'b',b'cd'])
   def read(self,n):return next(self.items,b'')
  self.assertEqual(m.read_exact(Stream(),4),b'abcd')
  with self.assertRaises(RuntimeError):m.read_exact(io.BytesIO(b'abc'),4)
 def test_geometry_no_chroma_rounding_mismatch(self):
  for w,h in [(1920,1080),(1080,1920),(853,481)]:
   x,y,cw,ch=m.crop_pixels((.104,.809,.792,.117),w,h)
   self.assertTrue(x+cw<=w and y+ch<=h);self.assertEqual(cw%2,0);self.assertEqual(ch%2,0)
 def test_quantities_are_preserved(self):
  rows=[{'time':i/4,'text':('盐2克' if i<4 else '盐3克'),'confidence':.99} for i in range(8)]
  cues,_=m.cues_from_rows(rows,2,4);self.assertEqual([c['text'] for c in cues],['盐2克','盐3克']);self.assertIn('00:00:01,000 --> 00:00:02,000',m.srt_text(cues))
 def test_one_frame_glitch_bridged_but_short_real_cue_kept(self):
  texts=['豆腐']*4+['']+['豆腐']*4
  cues,_=m.cues_from_rows([{'time':i/4,'text':t,'confidence':.99 if t else 0} for i,t in enumerate(texts)],2.25,4)
  self.assertEqual(len(cues),1);self.assertEqual(cues[0]['end'],2.25);self.assertGreater(cues[0]['confidence'],.98)
  cues,_=m.cues_from_rows([{'time':0,'text':'盐','confidence':.99}],.25,4)
  self.assertEqual(cues[0]['text'],'盐');self.assertIn('short-caption',cues[0]['flags'])
 def test_scan_skips_samples_symlinks_partials_and_unstable(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'a.mkv').touch();(root/'b.mkv.part').touch();(root/'OCR样稿').mkdir();(root/'OCR样稿/sample.mkv').touch();(root/'alias.mkv').symlink_to(root/'a.mkv')
   self.assertEqual(m.discover(root,False,30),[(root/'a.mkv').resolve()]);self.assertEqual(m.discover(root,True,30),[])
if __name__=='__main__':unittest.main()
