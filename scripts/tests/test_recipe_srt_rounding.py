import importlib.util,tempfile,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('batch',Path(__file__).resolve().parents[1]/'recipe-batch.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class SubtitleRoundingChecks(unittest.TestCase):
 def test_small_platform_overrun_and_original_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.srt';p.write_text('1\n00:09:40,570 --> 00:09:42,940\n谢谢\n');raw=p.read_bytes()
   self.assertEqual(m.parse_srt(p,582.936)[0]['end'],582.936);self.assertEqual(p.read_bytes(),raw)
   self.assertEqual(m.parse_srt(p,582.940)[0]['end'],582.940)
   with self.assertRaisesRegex(ValueError,'outside'):m.parse_srt(p,582.880)
   with self.assertRaisesRegex(ValueError,'outside'):m.parse_srt(p,580.569)

 def test_only_final_cue_accepts_frame_scale_tail(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.srt';p.write_text('1\n00:09:59,760 --> 00:10:01,420\n谢谢诸位观看\n');original=p.read_bytes()
   self.assertEqual(m.parse_srt(p,601.396)[0]['end'],601.396)
   self.assertEqual(p.read_bytes(),original)
   with self.assertRaisesRegex(ValueError,'outside'):m.parse_srt(p,601.360)
   p.write_text('1\n00:09:59,760 --> 00:10:01,420\n谢谢\n\n2\n00:10:01,000 --> 00:10:01,200\n结束\n')
   with self.assertRaisesRegex(ValueError,'outside'):m.parse_srt(p,601.396)
