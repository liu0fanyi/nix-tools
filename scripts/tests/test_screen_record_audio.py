"""Exercise audio routing failures without opening any real audio device."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('audio', Path(__file__).parents[1] / 'screen-record-audio.py')
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, XDG_RUNTIME_DIR=self.temp.name, XDG_STATE_HOME=self.temp.name)
        self.env.start()
        self.addCleanup(self.env.stop)

    def mode(self, value):
        path = audio.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def test_default_system_and_invalid_preference(self):
        self.assertEqual(audio.selected_mode(), 'system')
        self.mode('invalid')
        self.assertEqual(audio.selected_mode(), 'system')
        with patch.object(audio, 'sources', return_value=[{'name': 'speaker.monitor'}]), patch.object(audio, 'command', return_value='speaker') as command:
            self.assertEqual(audio.prepare(), 'speaker.monitor')
            command.assert_called_once_with('pactl', 'get-default-sink')

    def test_silent_does_not_connect_to_audio(self):
        self.mode('none')
        with patch.object(audio, 'command') as command:
            self.assertEqual(audio.prepare(), '')
            command.assert_not_called()

    def test_monitor_never_used_as_microphone(self):
        with self.assertRaisesRegex(RuntimeError, '没有可用麦克风'):
            audio.microphone([{'name': 'speaker.monitor'}])
        with patch.object(audio, 'command', return_value='speaker.monitor'):
            self.assertEqual(audio.microphone([{'name': 'speaker.monitor'}, {'name': 'usb_mic'}]), 'usb_mic')

    def test_default_physical_microphone_preferred(self):
        with patch.object(audio, 'command', return_value='mic2'):
            self.assertEqual(audio.microphone([{'name': 'mic1'}, {'name': 'mic2'}]), 'mic2')

    def test_menu_cancel_and_active_do_not_change_mode(self):
        self.mode('system')
        with patch.object(audio, 'active', return_value=False), patch.object(audio, 'command', side_effect=subprocess.CalledProcessError(1, 'fuzzel')):
            audio.choose()
        self.assertEqual(audio.selected_mode(), 'system')
        with patch.object(audio, 'active', return_value=True), patch.object(audio, 'notify'), patch.object(audio, 'command') as command:
            audio.choose()
            command.assert_not_called()
        self.assertEqual(audio.selected_mode(), 'system')

    def test_mix_partial_failure_cleans_only_owned_modules(self):
        self.mode('both')
        modules = []
        unloaded = []
        def command(*args):
            if args[1] == 'get-default-sink':
                return 'speaker'
            if args[1] == 'get-default-source':
                return 'mic'
            if args[1] == 'load-module':
                if len(modules) == 2:
                    raise subprocess.CalledProcessError(1, args)
                index = len(modules) + 10
                modules.append({'index': index, 'name': args[2], 'argument': ' '.join(args[3:])})
                return str(index)
            if args[1:4] == ('--format=json', 'list', 'modules'):
                return json.dumps(modules)
            if args[1] == 'unload-module':
                unloaded.append(int(args[2]))
                return ''
            self.fail('Unexpected audio change: ' + str(args))
        with patch.object(audio, 'sources', return_value=[{'name': 'speaker.monitor'}, {'name': 'mic'}]), patch.object(audio, 'command', side_effect=command):
            with self.assertRaises(subprocess.CalledProcessError):
                audio.prepare()
        self.assertEqual(unloaded, [11, 10])
        self.assertFalse(audio.ledger_path().exists())
        self.assertIn('sink=nix_tools_record_mix_', modules[1]['argument'])

    def test_reused_ids_and_sink_prefix_never_unloaded(self):
        owned = [{'id': 5, 'name': 'module-null-sink', 'sink': 'record_mix'}, {'id': 6, 'name': 'module-loopback', 'sink': 'record_mix'}]
        audio.ledger_path().write_text(json.dumps(owned))
        current = [{'index': 5, 'name': 'module-null-sink', 'argument': 'sink_name=record_mix_other'}, {'index': 6, 'name': 'module-loopback', 'argument': 'sink=other'}]
        with patch.object(audio, 'command', return_value=json.dumps(current)) as command:
            audio.cleanup()
            command.assert_called_once_with('pactl', '--format=json', 'list', 'modules')
        self.assertFalse(audio.ledger_path().exists())

    def test_cleanup_failure_preserves_retry_ledger(self):
        owned = {'id': 5, 'name': 'module-null-sink', 'sink': 'record_mix'}
        audio.ledger_path().write_text(json.dumps([owned]))
        current = [{'index': 5, 'name': 'module-null-sink', 'argument': 'sink_name=record_mix'}]
        with patch.object(audio, 'command', side_effect=[json.dumps(current), subprocess.CalledProcessError(1, 'unload')]):
            with self.assertRaises(RuntimeError):
                audio.cleanup()
        self.assertEqual(json.loads(audio.ledger_path().read_text()), [owned])


if __name__ == '__main__':
    unittest.main()
