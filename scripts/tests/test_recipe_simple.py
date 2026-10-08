"""No-video workflow admission, bound AI output and interrupted publication."""
import copy
import importlib.util
import io
import json
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from PIL import Image

path=Path(__file__).resolve().parents[1]/'recipe-simple.py'
spec=importlib.util.spec_from_file_location('simple',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class SimpleChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'workflow';self.app=m.Simple(self.root);self.app.init()
        self.entry={'id':'BVTest123','title':'豆腐做法','author':'测试'}
        self.manifest=Path(self.temp.name)/'manifest.json';m.f.atomic(self.manifest,[self.entry]);self.app.add(self.manifest)
        data=io.BytesIO();Image.new('RGB',(32,20),(100,200,100)).save(data,'JPEG');self.cover=data.getvalue()
    def tearDown(self):self.app.close();self.temp.cleanup()
    def platform(self,vid,kind,command):
        self.assertEqual(kind,'ai-subtitles');self.assertIn('--skip-download',command);self.assertNotIn('--write-auto-subs',command)
        base=self.root/'platform-subtitles'/vid
        m.f.atomic(base/'source.info.json',{'id':vid,'duration':3,'thumbnail':'http://i0.hdslb.com/cover.jpg','subtitles':{'ai-zh':[{'ext':'srt'}]}})
        (base/'source.ai-zh.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\n豆腐下锅\n\n2\n00:00:01,230 --> 00:00:02,500\n生抽15克\n')
        return 'Recipe AI-only subtitle filter active\n'
    def prepare(self):
        with mock.patch.object(self.app,'log_command',side_effect=self.platform),mock.patch.object(m,'fetch_cover',return_value=self.cover),mock.patch.object(m.f.batch,'probe',side_effect=AssertionError('no video probing')):
            self.assertEqual(self.app.next()['counts'],{'waiting_extract':1})
        return m.f.batch.load(self.app.packet(self.entry['id']))
    def response(self):
        packet=self.prepare();return {'task_id':packet['task_id'],'input_sha256':packet['input_sha256'],'processor':'synthetic','model':None,'result':{'title':'豆腐','ingredients':[{'name':'豆腐','amount':None,'optional':False}],'steps':[{'text':'豆腐下锅。','cue_ids':[1]},{'text':'加生抽。','cue_ids':[2]}],'notes':[]}}
    def send(self,response):
        p=Path(self.temp.name)/'response.json';m.f.atomic(p,response);return self.app.accept(p)
    def test_publish_resume_rebuild_no_video_and_exact_timing(self):
        response=self.response();self.send(response)
        recipe=m.f.batch.load(self.root/'results/BVTest123.json');self.assertEqual(recipe['steps'][1]['start'],1.23)
        self.assertEqual(self.app.next()['counts'],{'published':1});self.send(response)
        self.app.close();self.app=m.Simple(self.root)
        (self.root/'library/index.html').unlink()
        with mock.patch.object(self.app,'log_command',side_effect=AssertionError('no network')):self.app.next()
        self.assertTrue((self.root/'library/index.html').exists())
        self.assertFalse(any(p.suffix in ('.mp4','.mkv','.webm') for p in self.root.rglob('*')))
        self.assertFalse((self.root/'media').exists());self.assertFalse((self.root/'queues').exists())
        self.assertIn('豆腐',(self.root/'library/search-index.json').read_text())
    def test_source_change_and_stale_result_rejected(self):
        response=self.response();bad=copy.deepcopy(response);bad['input_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'stale'):self.send(bad)
        base=self.root/'platform-subtitles/BVTest123';(base/'source.ai-zh.srt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'input changed'):self.send(response)
    def test_bad_cue_and_out_of_order_rejected(self):
        response=self.response();bad=copy.deepcopy(response);bad['result']['steps'][0]['cue_ids']=[999]
        with self.assertRaisesRegex(ValueError,'invented'):self.send(bad)
        bad=copy.deepcopy(response);bad['result']['steps'].reverse()
        with self.assertRaisesRegex(ValueError,'chronological'):self.send(bad)
    def test_no_subtitles_skip_and_failure_retry(self):
        with mock.patch.object(self.app,'ai_subtitles',side_effect=m.f.NoAISubtitles()):self.app.next()
        self.assertEqual(self.app.status()['counts'],{'skipped':1})
        self.app.update(self.entry['id'],'queued')
        with mock.patch.object(self.app,'ai_subtitles',side_effect=RuntimeError('timeout')):
            with self.assertRaisesRegex(RuntimeError,'timeout'):self.app.next()
        self.assertEqual(self.app.status()['counts'],{'failed':1});self.app.retry(self.entry['id']);self.assertEqual(self.app.status()['counts'],{'queued':1})
    def test_waiting_reuses_cache_and_single_writer(self):
        self.prepare()
        with mock.patch.object(self.app,'ai_subtitles',side_effect=AssertionError('cache')):self.app.next()
        with self.assertRaisesRegex(ValueError,'busy'):m.Simple(self.root)
    def test_manifest_prevalidated_and_no_media_seed(self):
        m.f.atomic(self.manifest,[self.entry,{**self.entry,'id':'BVNext123','video':'/tmp/film.mp4'}])
        with self.assertRaisesRegex(ValueError,'only id'):self.app.add(self.manifest)
        self.assertEqual(self.app.status()['total'],1)
        m.f.atomic(self.manifest,[{'id':f'BVBulk{i}','title':'菜','author':'人'} for i in range(4200)])
        self.assertEqual(self.app.add(self.manifest)['total'],4201)
    def test_cover_hosts_and_https_upgrade(self):
        self.assertEqual(m.cover_url('http://i0.hdslb.com/x.jpg'),'https://i0.hdslb.com/x.jpg')
        for url in ['https://hdslb.com.evil/x','file:///tmp/x','https://127.0.0.1/x','https://i0.hdslb.com:8080/x','https://user@i0.hdslb.com/x']:
            with self.assertRaises(ValueError):m.cover_url(url)
    def test_modified_archive_rejected_on_rebuild(self):
        self.send(self.response())
        path=self.root/'results/BVTest123.json';recipe=m.f.batch.load(path);recipe['steps'][0]['start']=.2;m.f.atomic(path,recipe)
        with self.assertRaisesRegex(ValueError,'stored result changed'):self.app.publish('BVTest123')

    def test_html_keeps_content_inert(self):
        response=self.response();response['result']['title']='</script><script>bad()</script>';self.send(response)
        page=(self.root/'library/recipes/BVTest123/recipe.html').read_text();self.assertNotIn('<script>bad()',page);self.assertIn('&lt;script&gt;',page)

    def test_collector_bound_skips_waiting_and_resumes(self):
        self.prepare()
        next_entry={**self.entry,'id':'BVNext123'};m.f.atomic(self.manifest,[next_entry]);self.app.add(self.manifest)
        with mock.patch.object(self.app,'prepare',side_effect=lambda entry:self.app.packet(entry['id']).parent.mkdir(parents=True)) as prepare:
            self.assertEqual(self.app.prepare_pending(1)['phase'],'waiting_for_ai');prepare.assert_not_called()
            result=self.app.prepare_pending(2);self.assertEqual(result['phase'],'prepared');self.assertEqual(result['id'],'BVNext123')
            self.assertEqual(self.app.status()['counts'],{'waiting_extract':2})
        self.app.close();self.app=m.Simple(self.root)
        with mock.patch.object(self.app,'prepare',side_effect=AssertionError('must not repeat')):
            self.assertEqual(self.app.prepare_pending(2)['phase'],'waiting_for_ai')
    def test_collector_skip_failure_and_stop(self):
        with mock.patch.object(self.app,'prepare',side_effect=m.f.NoAISubtitles()):self.assertEqual(self.app.prepare_pending(10)['phase'],'skipped')
        self.assertEqual(self.app.prepare_pending(10)['phase'],'sources_finished')
        self.app.update(self.entry['id'],'queued')
        with mock.patch.object(self.app,'prepare',side_effect=ValueError('login required')):self.assertEqual(self.app.prepare_pending(10)['phase'],'failed')
        self.assertEqual(self.app.status()['counts'],{'failed':1})
        self.app.close();self.app=m.Simple(self.root)
        (self.root/'collect.stop').write_text('')
        with mock.patch.object(m.Simple,'prepare_pending',side_effect=AssertionError('stop before network')):
            self.assertEqual(m.collect(self.root)['phase'],'stopped')
    def test_collector_defaults_bound_watch_and_error_exit(self):
        self.app.close();self.app=m.Simple(self.root)
        # Producer cannot write while the ordinary writer is busy.
        with mock.patch.object(m,'Simple',side_effect=[ValueError('simple workflow busy'),self.app]),mock.patch.object(self.app,'prepare_pending',return_value={'phase':'waiting_for_ai','pending':10}),mock.patch.object(m.time,'sleep') as sleep:
            self.assertEqual(m.collect(self.root)['phase'],'waiting_for_ai');sleep.assert_called_once_with(5)
        self.app=m.Simple(self.root)
        with mock.patch.object(m,'Simple',return_value=self.app),mock.patch.object(self.app,'prepare_pending',side_effect=[{'phase':'waiting_for_ai','pending':10},{'phase':'failed','error':'HTTP 412'}]),mock.patch.object(m.time,'sleep') as sleep:
            self.assertEqual(m.collect(self.root,watch=True)['phase'],'failed');sleep.assert_called_once_with(30)
        self.app=m.Simple(self.root)
        with self.assertRaisesRegex(ValueError,'interval'):m.collect(self.root,interval=1)

    def test_progress_counts_and_real_collector_lock(self):
        self.app.close();self.app=m.Simple(self.root)
        m.f.atomic(self.manifest,[{**self.entry,'id':f'BVState{i}'} for i in range(4)]);self.app.add(self.manifest)
        for vid,state in zip([self.entry['id']]+[f'BVState{i}' for i in range(4)],['published','waiting_extract','queued','skipped','failed']):self.app.update(vid,state)
        m.f.atomic(self.root/'collector.json',{'max_pending':1,'interval':60,'error':'PRIVATE SECRET','root':'PRIVATE PATH'})
        lock=(self.root/'.collector.lock').open('a');m.fcntl.flock(lock,m.fcntl.LOCK_EX|m.fcntl.LOCK_NB)
        try:
            report=m.progress(self.root);self.assertEqual(report['total'],5);self.assertEqual(report['settled'],2);self.assertEqual(report['source_ready'],3);self.assertEqual(report['remaining'],3)
            self.assertEqual(report['collector']['state'],'waiting_for_ai');self.assertTrue(report['collector']['active']);self.assertNotIn('PRIVATE',json.dumps(report))
        finally:lock.close()
        self.assertEqual(m.progress(self.root)['collector']['state'],'stopped')
        self.app.update('BVState1','skipped');self.assertEqual(m.progress(self.root)['collector']['state'],'sources_finished')
    def test_progress_http_live_safe_and_no_store(self):
        import subprocess,sys,time,urllib.request,urllib.error,socket
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        proc=subprocess.Popen([sys.executable,str(path),'--root',str(self.root),'serve','--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/progress') as response:
                        self.assertEqual(response.headers['Cache-Control'],'no-store');self.assertEqual(json.load(response)['counts']['queued'],1)
                    break
                except urllib.error.URLError:time.sleep(.1)
            else:self.fail('server did not start')
            self.app.update(self.entry['id'],'waiting_extract')
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/progress') as response:self.assertEqual(json.load(response)['counts']['waiting_extract'],1)
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/progress.html') as response:self.assertIn('recipe-bar',response.read().decode())
            for url,code in [('/config.json',404),('/simple.sqlite3',404),('/../collector.json',404)]:
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(f'http://127.0.0.1:{port}'+url)
                self.assertEqual(error.exception.code,code)
            req=urllib.request.Request(f'http://127.0.0.1:{port}/api/progress',headers={'Host':'evil.invalid'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
            self.assertEqual(error.exception.code,403)
        finally:proc.terminate();proc.wait(timeout=10)

    def test_event_tail_redaction_collapse_and_blocked_health(self):
        self.app.close();self.app=m.Simple(self.root)
        secret='Cookie: SECRET_TOKEN /home/private </script>'
        m.f.atomic(self.root/'collector.json',{'phase':'failed','updated_at':1000,'error':'image file is truncated '+secret,'id':'BVTest123'})
        (self.root/'采集.log').write_text(json.dumps({'phase':'failed','id':'BVTest123','error':'image file is truncated '+secret})+'\n'+secret+'\n')
        (self.root/'AI整理.log').write_text(''.join(json.dumps({'state':'waiting_for_subtitles','id':None})+'\n' for _ in range(5000)))
        m.f.atomic(self.root/'ai-worker.json',{'state':'waiting_for_subtitles','updated_at':2000,'model':'test'})
        with (self.root/'.ai-worker.lock').open('a') as lock:
            m.fcntl.flock(lock,m.fcntl.LOCK_EX|m.fcntl.LOCK_NB);p=m.progress(self.root)
        self.assertTrue(p['ai']['active']);self.assertEqual(p['health']['state'],'blocked');self.assertEqual(p['health']['reason'],'source_failed');self.assertEqual(p['collector']['state'],'failed')
        self.assertEqual(len(p['events']),2);self.assertEqual(p['events'][0]['time'],1000);self.assertIn('封面图片解码失败',p['events'][0]['message']);self.assertNotIn('SECRET',json.dumps(p));self.assertNotIn('/home/private',json.dumps(p))
    def test_events_unknown_timestamp_and_progress_not_heartbeat(self):
        self.app.close();self.app=m.Simple(self.root)
        (self.root/'采集.log').write_text(json.dumps({'phase':'prepared','id':'BVTest123'})+'\n')
        (self.root/'AI整理.log').write_text(json.dumps({'state':'published','id':'BVTest123','updated_at':1500})+'\n')
        m.f.atomic(self.root/'ai-worker.json',{'state':'waiting_for_subtitles','updated_at':2500})
        p=m.progress(self.root);self.assertIsNone(p['events'][0]['time']);self.assertEqual(p['health']['last_progress_at'],1500)

if __name__=='__main__':unittest.main()
