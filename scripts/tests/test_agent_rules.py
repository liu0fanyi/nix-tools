import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('agent_rules', Path(__file__).parents[1] / 'agent-rules.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AgentRulesTests(unittest.TestCase):
    def test_existing_content_preserved_and_links_follow_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / 'source', root / 'target'
            source.write_text('old'); target.write_text('old')
            module.install([(source, target)])
            self.assertFalse(target.is_symlink())
            module.install([(source, target)], apply=True)
            source.write_text('new')
            self.assertEqual(target.read_text(), 'new')
            module.install([(source, target)], apply=True)
            module.install([(source, target)], check=True)

    def test_conflict_prevents_all_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b, first, second = [root / name for name in ['a', 'b', 'first', 'second']]
            a.write_text('a'); b.write_text('b'); second.write_text('local edit')
            with self.assertRaises(ValueError):
                module.install([(a, first), (b, second)], apply=True)
            self.assertFalse(first.exists())
            self.assertEqual(second.read_text(), 'local edit')

    def test_other_symlink_and_parent_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, other, target = root/'source', root/'other', root/'target'
            source.write_text('same'); other.write_text('same'); target.symlink_to(other)
            with self.assertRaises(ValueError):module.install([(source,target)], apply=True)
            real = root/'real';real.mkdir();parent=root/'parent';parent.symlink_to(real)
            with self.assertRaises(ValueError):module.install([(source,parent/'file')], apply=True)
            self.assertFalse((real/'file').exists())

    def test_fresh_install_creates_only_managed_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root/'source', root/'new/AGENTS.md'
            source.write_text('rules')
            with self.assertRaises(ValueError):
                module.install([(source, target)], check=True)
            self.assertFalse(target.parent.exists())
            module.install([(source, target)], apply=True)
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.read_text(), 'rules')
