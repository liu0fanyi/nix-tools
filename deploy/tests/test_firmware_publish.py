import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('publisher', Path(__file__).resolve().parents[1] / 'scripts/publish-firmware.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ns = {'__name__': 'remote_test'}
        exec(p.REMOTE, self.ns)
        self.ns['ROOT'] = Path(self.temp.name) / 'esp32'
        self.data = b'\0' * 8192
        self.entry = dict(product='esp32_mp3_player', version='0.4.5', family='waveshare-epaper154-v2', layoutVersion=1,
            chip='esp32s3', signingKeyId=self.ns['KEY'], size=len(self.data), sha256=self.ns['digest'](self.data),
            sourceCommit='a'*40, commonCommit='b'*40, url=p.BASE+'/esp32_mp3_player/0.4.5/application.bin')
    def call(self, **request):
        output = io.StringIO()
        with patch('sys.stdin', io.StringIO(json.dumps(request))), contextlib.redirect_stdout(output):
            self.ns['main']()
        return json.loads(output.getvalue())
    def asset(self):
        return dict(entry=self.entry, data=base64.b64encode(self.data).decode())
    def test_assets_not_advertised_before_commit_and_retry_is_idempotent(self):
        before=self.call(operation='read')
        self.call(operation='assets', assets=[self.asset()])
        self.assertEqual(self.call(operation='read'), before)
        self.call(operation='assets', assets=[self.asset()])
        self.call(operation='catalog', entries=[self.entry], expected=before['sha256'])
        after=self.call(operation='read')
        self.assertEqual(len(json.loads(after['catalog'])['releases']),1)
        self.call(operation='catalog', entries=[self.entry], expected=after['sha256'])
        self.assertEqual(self.call(operation='read'),after)
    def test_stale_catalog_commit_rejected(self):
        self.call(operation='assets', assets=[self.asset()])
        with self.assertRaises(AssertionError):
            self.call(operation='catalog', entries=[self.entry], expected='0'*64)
        self.assertEqual(self.call(operation='read')['catalog'],'')
    def test_corrupt_transfer_is_not_published(self):
        asset=self.asset(); asset['data']=base64.b64encode(b'bad').decode()
        with self.assertRaises(AssertionError): self.call(operation='assets',assets=[asset])
        self.assertFalse((self.ns['ROOT']/'esp32_mp3_player/0.4.5/application.bin').exists())
    def test_version_path_and_url_rejected(self):
        for changes in [dict(version='../x'),dict(url='https://example.com/a'),dict(signingKeyId='0'*64)]:
            with self.subTest(changes=changes),self.assertRaises(AssertionError):self.ns['validate'](self.entry | changes)
    def test_symlink_outside_root_rejected(self):
        root=self.ns['ROOT']; root.mkdir(); (root/'esp32_mp3_player').symlink_to(Path(self.temp.name))
        with self.assertRaises(AssertionError): self.call(operation='assets',assets=[self.asset()])
    def test_same_version_changed_metadata_rejected(self):
        catalog=json.dumps(dict(schemaVersion=1,releases=[self.entry]))
        with self.assertRaises(AssertionError):self.ns['merge'](catalog,[self.entry | dict(sha256='0'*64)])
    def test_public_download_failure_does_not_commit_catalog(self):
        package=Path(self.temp.name)/'package';package.mkdir()
        (package/'application.bin').write_bytes(self.data)
        (package/'catalog.json').write_text(json.dumps(dict(schemaVersion=1,releases=[self.entry])))
        calls=[]
        def remote(request):
            calls.append(request['operation'])
            return dict(catalog='',sha256=self.ns['digest'](b''))
        with patch.object(p,'remote',side_effect=remote),patch.object(p,'download',return_value=b'bad'):
            with self.assertRaises(ValueError):p.publish([package],True)
        self.assertEqual(calls,['read','assets'])

    def test_unified_release_preserves_legacy_catalog_and_is_immutable(self):
        old = self.entry.copy()
        self.call(operation='assets', assets=[self.asset()])
        before = self.call(operation='read')
        self.call(operation='catalog', entries=[old], expected=before['sha256'])
        self.entry = old | dict(product='esp32_device_bean', version='0.1.11',
            url=p.BASE+'/esp32_device_bean/0.1.11/application.bin')
        before = self.call(operation='read')
        self.call(operation='assets', assets=[self.asset()])
        self.assertEqual(self.call(operation='read'), before)
        self.call(operation='catalog', entries=[self.entry], expected=before['sha256'])
        after = self.call(operation='read')
        self.assertEqual(json.loads(after['catalog'])['releases'], [old, self.entry])
        with self.assertRaises(AssertionError):
            self.ns['merge'](after['catalog'], [self.entry | dict(sha256='0'*64)])
        with self.assertRaises(AssertionError):
            self.ns['validate'](self.entry | dict(product='unrelated_product'))
