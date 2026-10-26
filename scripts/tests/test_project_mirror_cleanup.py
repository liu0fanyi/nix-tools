from pathlib import Path
import hashlib
import importlib.util
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("migration", Path(__file__).parents[1]/"migrate-project-overview-mirrors.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/"todos"; self.root.mkdir()
        (self.root/"old-project").mkdir(); (self.root/"old-project/旧说明.md").write_text("legacy")
        (self.root/"old-project/hardlink.md").hardlink_to(self.root/"old-project/旧说明.md")
        (self.root/"个人待办.md").write_text("keep exactly")
        (self.root/"projects").mkdir(); (self.root/"projects/demo.md").write_text("new summary")
        self.hashes={"demo.md":m.digest(self.root/"projects/demo.md")}
        self.base=Path(self.temp.name)/"backup"
    def backup(self):
        return m.backup(self.root,["old-project"],self.base,self.hashes)
    def test_verified_backup_then_cleanup_keeps_personal_and_new_docs(self):
        folder=self.backup(); result=m.cleanup(self.root,folder)
        self.assertFalse((self.root/"old-project").exists())
        self.assertEqual((self.root/"个人待办.md").read_text(),"keep exactly")
        self.assertEqual((self.root/"projects/demo.md").read_text(),"new summary")
        self.assertTrue((folder/"legacy-projects.tar.gz").is_file())
        self.assertEqual(result["backed_up_files"],2)
    def test_source_drift_refuses_every_deletion(self):
        folder=self.backup(); (self.root/"old-project/new.md").write_text("concurrent new data")
        with self.assertRaises(ValueError):m.cleanup(self.root,folder)
        self.assertTrue((self.root/"old-project/旧说明.md").is_file())
        self.assertTrue((self.root/"old-project/new.md").is_file())
    def test_new_overview_or_backup_corruption_refuses_deletion(self):
        folder=self.backup(); (self.root/"projects/demo.md").write_text("changed")
        with self.assertRaises(ValueError):m.cleanup(self.root,folder)
        self.assertTrue((self.root/"old-project").is_dir())
        (folder/"legacy-projects.tar.gz").write_bytes(b"corrupt")
        with self.assertRaises(ValueError):m.cleanup(self.root,folder)
        self.assertTrue((self.root/"old-project").is_dir())
    def test_no_parent_or_new_projects_tree_can_be_selected(self):
        for name in ["..","../outside","projects","."]:
            with self.assertRaises(ValueError):m.snapshot(self.root,[name])
