import copy
import importlib.util
import json
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_nuc_plan', ROOT / 'scripts/native_nuc_plan.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class NucPlanTests(unittest.TestCase):
    def setUp(self):
        self.config = tomllib.loads((ROOT / 'deploy/instances/home.toml').read_text())
        p = self.config['paths']
        mounts = {
            'tag-server': [(p['tag_data'], '/data', True), (p['workspace'], '/workspace', True),
                           (p['media'], '/workspace/media', True), (p['whisper_models'], '/models', False)],
            'tag-server-readonly': [(p['readonly_tag_data'], '/data', True), (p['readonly'], '/workspace', False)],
            'dufs': [(p['workspace'], '/data', True), (p['media'], '/data/media', True)],
            'dufs-readonly': [(p['readonly'], '/data', False)],
            'tag-peer-discovery': [(p['tag_data'], '/data', True)],
            'caddy': [(p['caddy_data'], '/data/caddy', True), (p['dist'], '/srv/dist', False)],
        }
        self.inventory = [{'Name': module.PREFIX+s+'_1', 'Image': 'a'*64, 'State': {'Running': True},
                           'Config': {'Env': ['SECRET=must-not-appear'], 'Cmd': ['secret-command']},
                           'Mounts': [{'Source': a, 'Destination': b, 'RW': c} for a,b,c in mounts.get(s, [])]}
                          for s in module.REPLACE + module.KEEP]

    def test_split_and_no_secret_output_or_mutation(self):
        before = copy.deepcopy(self.inventory)
        result = module.make_plan(self.config, self.inventory)
        self.assertEqual(5, sum(r['action']=='replace' for r in result['containers']))
        self.assertEqual(4, sum(r['action']=='retain' for r in result['containers']))
        self.assertFalse(result['cutover_ready'])
        self.assertNotIn('must-not-appear', json.dumps(result))
        self.assertNotIn('secret-command', json.dumps(result))
        self.assertEqual(before, self.inventory)

    def test_readonly_writable_rejected(self):
        self.inventory[1]['Mounts'][1]['RW'] = True
        with self.assertRaises(ValueError): module.make_plan(self.config, self.inventory)

    def test_missing_model_mapping_rejected(self):
        self.inventory[0]['Mounts'].pop()
        with self.assertRaises(ValueError): module.make_plan(self.config, self.inventory)

    def test_readonly_git_key_rejected(self):
        self.inventory[1]['Mounts'].append({'Source': '/secret', 'Destination': '/root/.ssh', 'RW': False})
        with self.assertRaises(ValueError): module.make_plan(self.config, self.inventory)

    def test_floating_image_or_stopped_source_rejected(self):
        for field, value in [('Image', 'latest'), ('State', {'Running': False})]:
            inventory = copy.deepcopy(self.inventory); inventory[0][field] = value
            with self.assertRaises(ValueError): module.make_plan(self.config, inventory)

    def test_other_profile_rejected(self):
        self.config['deployment']['profile'] = 'anonymous'
        with self.assertRaises(ValueError): module.make_plan(self.config, self.inventory)

if __name__ == '__main__': unittest.main()
