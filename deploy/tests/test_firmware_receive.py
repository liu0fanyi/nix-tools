import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

p=Path(__file__).resolve().parents[1]/'scripts/firmware-receive.py'
s=importlib.util.spec_from_file_location('receiver',p);r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
class ReceiverTests(unittest.TestCase):
    def request(self,request,command='firmware-publish'):
        target=Mock()
        r.receive(io.StringIO(json.dumps(request)),command,target)
        target.assert_called_once()
    def test_read(self):self.request({'operation':'read'})
    def test_reject_shell_and_sftp(self):
        for command in ['',None,'sh','scp -t /tmp/a','rsync --server . /']:
            with self.subTest(command=command),self.assertRaises(ValueError):self.request({'operation':'read'},command)
    def test_reject_oversized_input_without_transaction(self):
        target=Mock()
        with self.assertRaises(ValueError):r.receive(io.StringIO(' '* (r.MAX_REQUEST+1)),'firmware-publish',target)
        target.assert_not_called()
    def test_no_delete_or_arbitrary_destination(self):
        for value in [{'operation':'delete'},{'operation':'read','root':'/tmp'},{'operation':'assets','assets':[]}]:
            with self.subTest(value=value),self.assertRaises(ValueError):self.request(value)
    def test_product_and_bootstrap_boundaries(self):
        entry=dict(product='esp32_device_bean',supportedSourceProducts=['esp32_device_bean'],bootstrapRequired=False,requiredResources=[])
        self.request(dict(operation='assets',assets=[dict(entry=entry,data='')]))
        for changes in [dict(product='device-bean'),dict(product='esp32_mp3_player'),dict(bootstrapRequired=True),dict(requiredResources=['model']),dict(supportedSourceProducts=['esp32_mp3_player'])]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.request(dict(operation='catalog',entries=[entry|changes],expected='a'*64))
