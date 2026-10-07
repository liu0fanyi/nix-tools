import importlib.util,json,fcntl
from pathlib import Path
from unittest import mock
import unittest
import test_recipe_simple as base
m=base.m
spec=importlib.util.spec_from_file_location('worker',Path(__file__).resolve().parents[1]/'recipe-ai-worker.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
class WorkerChecks(unittest.TestCase):
 setUp=base.SimpleChecks.setUp
 prepare=base.SimpleChecks.prepare
 response=base.SimpleChecks.response
 platform=base.SimpleChecks.platform
 def ready(self):
  response=self.response();self.app.close();self.app=None
  return response
 def tearDown(self):
  if self.app:self.app.close()
  self.temp.cleanup()
 def test_auto_real_flow_fake_model(self):
  response=self.ready()
  class Fake:
   pid=123;returncode=0
   def __init__(inner,cmd,**kw):
    self.assertIn('read-only',cmd);self.assertIn('--ignore-user-config',cmd);inner.cmd=cmd
   def communicate(inner,prompt,timeout):
    text=prompt.decode();self.assertIn('生抽15克',text);self.assertIn('不调用任何工具',text)
    Path(inner.cmd[inner.cmd.index('--output-last-message')+1]).write_text(json.dumps(response['result']))
  with mock.patch.object(w.subprocess,'Popen',Fake):w.worker(self.root,once=True)
  self.app=m.Simple(self.root,read_only=True);self.assertEqual(self.app.status()['counts'],{'published':1})
  self.assertEqual(m.progress(self.root)['ai']['state'],'stopped')
  self.assertTrue((self.root/'library/recipes/BVTest123/recipe.html').exists())
 def test_recover_saved_answer_no_second_call(self):
  response=self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True)
  m.f.atomic(d/'answer.json',response['result'])
  with mock.patch.object(w.subprocess,'Popen',side_effect=AssertionError('no repeat model')):w.worker(self.root,once=True)
  self.app=m.Simple(self.root,read_only=True);self.assertEqual(self.app.status()['counts'],{'published':1})
 def test_incomplete_attempt_blocks_retry_and_retains_input(self):
  response=self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True)
  m.f.atomic(d/'started.json',{'input_sha256':response['input_sha256']})
  with mock.patch.object(w.subprocess,'Popen',side_effect=AssertionError('no repeat model')):
   with self.assertRaisesRegex(ValueError,'incomplete'):w.worker(self.root,once=True)
  self.app=m.Simple(self.root,read_only=True);self.assertEqual(self.app.status()['counts'],{'waiting_extract':1});self.assertEqual(m.progress(self.root)['ai']['state'],'failed')
 def test_invalid_model_cue_not_published(self):
  response=self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True);response['result']['steps'][0]['cue_ids']=[999]
  m.f.atomic(d/'answer.json',response['result'])
  with self.assertRaisesRegex(ValueError,'invented'):w.worker(self.root,once=True)
  self.app=m.Simple(self.root,read_only=True);self.assertEqual(self.app.status()['counts'],{'waiting_extract':1})
 def test_stop_and_duplicate_worker(self):
  self.ready();(self.root/'ai.stop').touch();w.worker(self.root,once=True);self.assertEqual(m.progress(self.root)['ai']['state'],'stopped')
  with (self.root/'.ai-worker.lock').open('a') as l:
   fcntl.flock(l,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaisesRegex(ValueError,'already running'):w.worker(self.root,once=True)

 def test_timeout_stops_child_and_keeps_waiting(self):
  import subprocess
  self.ready()
  child=mock.Mock(pid=123,returncode=1);child.communicate.side_effect=subprocess.TimeoutExpired('codex',1)
  with mock.patch.object(w.subprocess,'Popen',return_value=child),mock.patch.object(w.os,'killpg') as kill:
   with self.assertRaises(subprocess.TimeoutExpired):w.worker(self.root,once=True,timeout=1)
   kill.assert_called_once();child.wait.assert_called_once()
  self.app=m.Simple(self.root,read_only=True);self.assertEqual(self.app.status()['counts'],{'waiting_extract':1})
 def test_live_state_whitelist_and_stale_lock(self):
  self.ready();m.f.atomic(self.root/'ai-worker.json',{'state':'extracting','id':'BVTest123','model':'test','error':'private','path':'private'})
  self.assertEqual(m.progress(self.root)['ai']['state'],'stopped')
  with (self.root/'.ai-worker.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);state=m.progress(self.root)['ai'];self.assertTrue(state['active']);self.assertEqual(state['state'],'extracting');self.assertEqual(state['current_id'],'BVTest123');self.assertNotIn('path',state);self.assertNotIn('error',state)
 def test_saved_answer_wrong_input_binding_rejected(self):
  response=self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True);m.f.atomic(d/'started.json',{'input_sha256':'wrong'});m.f.atomic(d/'answer.json',response['result'])
  with self.assertRaisesRegex(ValueError,'input changed'):w.worker(self.root,once=True)
