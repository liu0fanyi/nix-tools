"""No-video workflow admission, bound AI output and interrupted publication."""
import copy
import importlib.util
import io
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

if __name__=='__main__':unittest.main()
