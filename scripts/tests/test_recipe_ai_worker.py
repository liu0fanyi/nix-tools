import importlib.util,json,fcntl
from pathlib import Path
from unittest import mock
import unittest
from jsonschema import ValidationError
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

 def test_provider_schema_preserves_local_unique_validation(self):
  response=self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True)
  packet=m.f.batch.load(self.root/'tasks/BVTest123/packet.json');converted=w.provider_schema(packet['result_schema'])
  self.assertNotIn('uniqueItems',converted['properties']['steps']['items']['properties']['cue_ids']);self.assertTrue(packet['result_schema']['properties']['steps']['items']['properties']['cue_ids']['uniqueItems'])
  response['result']['steps'][0]['cue_ids']=[1,1];m.f.atomic(d/'answer.json',response['result'])
  with self.assertRaises(ValidationError):w.worker(self.root,once=True)
  self.app=m.Simple(self.root,read_only=True);self.assertEqual(self.app.status()['counts'],{'waiting_extract':1})

 def test_mechanical_chronology_sort_preserves_raw_answer(self):
  response=self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True);response['result']['steps'].reverse();m.f.atomic(d/'answer.json',response['result']);before=(d/'answer.json').read_bytes()
  with mock.patch.object(w.subprocess,'Popen',side_effect=AssertionError('no second model call')):w.worker(self.root,once=True)
  self.assertEqual((d/'answer.json').read_bytes(),before);out=m.f.batch.load(self.root/'results/BVTest123.json');self.assertEqual(out['steps'][0]['cue_ids'],[1])

 def routing_events(self):
  return [{'type':'thread.started'}, {'type':'turn.started'}, {'type':'error','message':w.ROUTING_ERROR}, {'type':'item.completed','item':{'type':'error','message':'Falling back. '+w.ROUTING_ERROR}}, {'type':'turn.failed','error':{'message':w.ROUTING_ERROR}}]
 def test_routing_failure_retries_and_preserves_attempt(self):
  response=self.ready();calls=[]
  class Fake:
   pid=123
   def __init__(inner,cmd,**kw):inner.cmd=cmd;inner.out=kw['stdout'];inner.returncode=1 if not calls else 0;calls.append(inner)
   def communicate(inner,prompt,timeout):
    if inner.returncode:
     inner.out.write(('\n'.join(json.dumps(e) for e in self.routing_events())+'\n').encode());inner.out.flush()
    else:Path(inner.cmd[inner.cmd.index('--output-last-message')+1]).write_text(json.dumps(response['result']))
  with mock.patch.object(w.subprocess,'Popen',Fake),mock.patch.object(w,'ROUTING_DELAYS',(0,0,0)):w.worker(self.root,once=True)
  self.assertEqual(len(calls),2)
  self.app=m.Simple(self.root,read_only=True);self.assertEqual(self.app.status()['counts'],{'published':1})
  self.assertTrue((self.root/'ai-work/BVTest123/routing-attempts/1/events.jsonl').exists())
 def test_routing_limit_survives_restart(self):
  self.ready();calls=[]
  class Fake:
   pid=123;returncode=1
   def __init__(inner,cmd,**kw):inner.out=kw['stdout'];calls.append(inner)
   def communicate(inner,prompt,timeout):inner.out.write(('\n'.join(json.dumps(e) for e in self.routing_events())+'\n').encode());inner.out.flush()
  with mock.patch.object(w.subprocess,'Popen',Fake),mock.patch.object(w,'ROUTING_DELAYS',(0,0,0)):
   with self.assertRaisesRegex(ValueError,'retry limit'):w.worker(self.root,once=True)
   self.assertEqual(len(calls),4)
   with self.assertRaisesRegex(ValueError,'retry limit'):w.worker(self.root,once=True)
   self.assertEqual(len(calls),4)
  self.assertEqual(m.f.batch.load(self.root/'ai-worker.json')['error_code'],'routing_unavailable')
 def test_routing_guard_rejects_inference_and_uncertain_events(self):
  self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True)
  good=self.routing_events()
  for events in ([good[-1]], [{**good[0],'usage':{}},*good[1:]],good[:-1], good[:-1]+[{'type':'item.completed','item':{'type':'reasoning','text':'started'}}]+good[-1:],good+[{'type':'turn.completed','usage':{}}],[{'type':'turn.failed','error':{'message':'quota exceeded'}}]):
   (d/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events));self.assertFalse(w.routing_failure(d))
  (d/'events.jsonl').write_text('not json');self.assertFalse(w.routing_failure(d))
  (d/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in good));self.assertTrue(w.routing_failure(d))
  (d/'answer.json').write_text('{}');self.assertFalse(w.routing_failure(d))
 def test_routing_wait_visible_and_stop_keeps_history(self):
  self.ready();d=self.root/'ai-work/BVTest123';d.mkdir(parents=True)
  (d/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in self.routing_events()))
  packet=m.f.batch.load(self.root/'tasks/BVTest123/packet.json');m.f.atomic(d/'started.json',{'input_sha256':packet['input_sha256']})
  observed=[]
  def sleep(seconds):
   observed.append(m.progress(self.root)['ai']);(self.root/'ai.stop').touch()
  with mock.patch.object(w.time,'sleep',sleep),mock.patch.object(w.subprocess,'Popen',side_effect=AssertionError('stop forbids model')):w.worker(self.root,once=True)
  self.assertEqual(observed[0]['state'],'retry_wait');self.assertEqual(observed[0]['retry_count'],1);self.assertIn('连接失败',observed[0]['failure_reason']);self.assertTrue((d/'routing-attempts/1/started.json').exists())
