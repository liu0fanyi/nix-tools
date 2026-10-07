"""Ensure platform subtitle extraction never fetches unwanted language bodies."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

class PlatformError(Exception):
    def __init__(self, message, **kwargs): super().__init__(message)
class BaseIE:
    _HEADERS = {'Referer':'https://www.bilibili.com/'}
    def __init_subclass__(cls, plugin_name=None, **kwargs): super().__init_subclass__(**kwargs)
    def to_screen(self, message): self.messages.append(message)
    def _proto_relative_url(self, url, scheme): return scheme + url if url.startswith('//') else url
    def json2srt(self, body): return 'converted-subtitle'
    def _download_json(self, url, video_id, **kwargs):
        self.requests.append(url)
        return self.info if url.endswith('/v2') else self.body

class AIPluginChecks(unittest.TestCase):
    def setUp(self):
        modules={}
        for name in ('yt_dlp','yt_dlp.extractor','yt_dlp.extractor.bilibili','yt_dlp.utils'):modules[name]=types.ModuleType(name)
        modules['yt_dlp.extractor.bilibili'].BiliBiliIE=BaseIE
        modules['yt_dlp.utils'].ExtractorError=PlatformError
        modules['yt_dlp.utils'].url_or_none=lambda url:url if url.startswith(('https://','http://')) else None
        path=Path(__file__).resolve().parents[1]/'recipe-ytdlp-plugins/recipe-ai/yt_dlp_plugins/extractor/recipe_ai_subtitles.py'
        with mock.patch.dict(sys.modules,modules):
            spec=importlib.util.spec_from_file_location('recipe_ai_plugin',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.ie=module._RecipeAIOnlyIE();self.ie.requests=[];self.ie.messages=[]
        self.ie.body={'body':[{'from':0,'to':1,'content':'豆腐'}]}
        self.ie.info={'code':0,'data':{'subtitle':{'subtitles':[]}}}
    def test_many_languages_only_fetches_one_chinese_ai_body(self):
        tracks=[{'lan':'language-'+str(i),'subtitle_url':'https://unused.example/'+str(i)} for i in range(50)]
        tracks.extend([{'lan':'ai-en','subtitle_url':'https://unused.example/en'},{'lan':'ai-zh','subtitle_url':'//subtitle.example/zh'},{'lan':'ai-zh','subtitle_url':'https://unused.example/duplicate'}])
        self.ie.info['data']['subtitle']['subtitles']=tracks
        result=self.ie._get_subtitles('BVTest',123)
        self.assertEqual(set(result),{'ai-zh'});self.assertEqual(result['ai-zh'][0]['ext'],'srt')
        self.assertEqual(self.ie.requests,['https://api.bilibili.com/x/player/wbi/v2','https://subtitle.example/zh'])
        self.assertIn('Recipe AI-only subtitle filter active',self.ie.messages)
    def test_no_ai_track_returns_empty_without_fetching_manual_or_english(self):
        self.ie.info['data']['subtitle']['subtitles']=[{'lan':'zh-CN','subtitle_url':'https://unused.example/manual'},{'lan':'ai-en','subtitle_url':'https://unused.example/en'}]
        self.assertEqual(self.ie._get_subtitles('BVTest',123),{})
        self.assertEqual(len(self.ie.requests),1)
    def test_api_login_error_and_malformed_metadata_cannot_mean_absence(self):
        for info in [{'code':-352,'data':{}},{'code':0,'data':{'need_login_subtitle':True}},{'code':0,'data':{}},{'code':0,'data':{'subtitle':{'subtitles':[None]}}}]:
            self.ie.info=info
            with self.assertRaises(PlatformError):self.ie._get_subtitles('BVTest',123)
    def test_missing_url_and_empty_body_fail(self):
        self.ie.info['data']['subtitle']['subtitles']=[{'lan':'ai-zh','subtitle_url':''}]
        with self.assertRaises(PlatformError):self.ie._get_subtitles('BVTest',123)
        self.ie.info['data']['subtitle']['subtitles'][0]['subtitle_url']='https://subtitle.example/zh';self.ie.body={'body':[]}
        with self.assertRaises(PlatformError):self.ie._get_subtitles('BVTest',123)

if __name__=='__main__':unittest.main()
