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

class LearningRegistration(unittest.TestCase):
    def test_preserves_other_settings_and_rejects_duplicate_registration(self):
        import tomllib
        from native_application_release import learning_map_binding
        before='lan=true\nauthorities=["nuc.local:5006"]\n[[applications]]\nname="quick-note"\nroot="/apps/quick-note"\n'
        after=learning_map_binding(before,Path('/apps/learning-map'))
        a,b=tomllib.loads(before),tomllib.loads(after)
        self.assertEqual(b['applications'][:-1],a['applications'])
        self.assertEqual(b['applications'][-1],{'name':'learning-map','root':'/apps/learning-map'})
        self.assertEqual(b['authorities'],a['authorities'])
        with self.assertRaises(ValueError):learning_map_binding(after,Path('/apps/learning-map'))

    def test_registration_config_is_an_owned_transaction_target_and_rolls_back(self):
        import tempfile,os
        from native_application_release import Manager,Scope,learning_map_binding
        from application_entry_transaction import ConfigurationTransaction,digest
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'private/config/application-entry.toml'
            config.parent.mkdir(parents=True)
            original='lan=true\n'
            config.write_text(original);config.chmod(0o600)
            source=root/'prepared.toml';source.write_text(learning_map_binding(original,root/'private/apps/learning-map'));source.chmod(0o600)
            scope=Scope('nuc',('private.service','readonly.service'),(root/'private/state',root/'readonly/state'),(),(),root/'releases',root/'units')
            manager=Manager(scope);plan={'application_registration':{'target':str(config)}}
            targets=manager.targets(plan)
            self.assertIn(config,targets);self.assertNotIn(root/'readonly/config/application-entry.toml',targets)
            transaction=ConfigurationTransaction(root/'transaction',{config})
            transaction.create({config:{'kind':'file','source':str(source),'sha256':digest(source)}})
            transaction.verify_before();transaction.install();transaction.verify_after()
            self.assertIn('learning-map',config.read_text())
            transaction.install(rollback=True);transaction.verify_before()
            self.assertEqual(config.read_text(),original);self.assertEqual(config.stat().st_mode&0o777,0o600)

class StartupRegistration(unittest.TestCase):
    def test_rebinds_only_existing_entry_and_refuses_wrong_original_hash(self):
        import json
        from native_application_release import learning_startup_binding
        target=Path('/fixed/application-entry.toml')
        original={'root':'/fixed','files':{str(target):'a'*64,'/other':'b'*64},'compose':['podman','compose']}
        after=json.loads(learning_startup_binding(json.dumps(original),target,'a'*64,'c'*64))
        expected=json.loads(json.dumps(original));expected['files'][str(target)]='c'*64
        self.assertEqual(after,expected)
        with self.assertRaises(ValueError):learning_startup_binding(json.dumps(original),target,'d'*64,'c'*64)
        with self.assertRaises(ValueError):learning_startup_binding(json.dumps(original),Path('/unknown'),'a'*64,'c'*64)
