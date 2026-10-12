import importlib.util
from pathlib import Path
import sys
import unittest

# These pure checks also run without an active service or access to user data.
sys.path.insert(0, str(Path(__file__).parents[1]))
from native_application_release import replace_command, command_line


class CommandBoundary(unittest.TestCase):
    def setUp(self):
        self.old = '/nix/store/' + 'a' * 32 + '-tag-all-workspace-native-0.1.0/bin/tag-all-core'
        self.front = '/nix/store/' + 'b' * 32 + '-frontend'
        self.new = Path('/nix/store/' + 'c' * 32 + '-tag-all-workspace-native-0.1.0')
        self.new_front = Path('/nix/store/' + 'd' * 32 + '-frontend')

    def test_only_program_and_frontend_change(self):
        old = self.old + " --state-dir '/private/state' --workspace-entry-read-only true --addr 127.0.0.1:18182 --workspace-entry-frontend " + self.front
        result, previous = replace_command(old, self.new, self.new_front)
        self.assertIn("--state-dir '/private/state'", result)
        self.assertIn('--workspace-entry-read-only true --addr 127.0.0.1:18182', result)
        self.assertEqual(result.replace(str(self.new / 'bin/tag-all-core'), self.old).replace(str(self.new_front), self.front), old)
        self.assertEqual(previous, [str(Path(self.old).parent.parent), self.front])

    def test_unknown_program_and_repeated_frontend_are_rejected(self):
        with self.assertRaises(ValueError): replace_command('/bin/sh --workspace-entry-frontend ' + self.front, self.new, self.new_front)
        with self.assertRaises(ValueError): replace_command(self.old + ' --workspace-entry-frontend ' + self.front + ' --workspace-entry-frontend ' + self.front, self.new, self.new_front)

    def test_reset_is_accepted_multiple_process_commands_are_refused(self):
        self.assertEqual(command_line('[Service]\nExecStart=\nExecStart='+self.old+'\n'), self.old)
        with self.assertRaises(ValueError): command_line('ExecStart=/first\nExecStart=/second\n')
