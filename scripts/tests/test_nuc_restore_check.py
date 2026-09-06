import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

script = Path(__file__).resolve().parents[1] / "nuc-restore-check.py"
if not script.exists():
    script = Path(__file__).with_name("nuc-restore-check.py")
spec = importlib.util.spec_from_file_location("restore_check", script)
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)

class RestoreTests(unittest.TestCase):
    def test_manifest_rejects_seed(self):
        manifest = dict(host="nuc", backup_uuid=restore.backup.UUID, scope="business",
                        copy_complete=True, checksum_verified=True, quiesced=False)
        with self.assertRaises(RuntimeError):
            restore.validate_manifest(manifest)
        manifest["quiesced"] = True
        restore.validate_manifest(manifest)

    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "escape").symlink_to("/etc")
            with self.assertRaises(RuntimeError):
                restore.inside(root, "escape/passwd")
            with self.assertRaises(RuntimeError):
                restore.inside(root, "../elsewhere")

    def test_database(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "test.db"
            with sqlite3.connect(db) as con:
                con.execute("CREATE TABLE example (id INTEGER)")
                con.execute("INSERT INTO example VALUES (1)")
            self.assertEqual(restore.check_database(db), {"integrity": "ok", "tables": 1})

    def test_missing_database_not_created(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "absent.db"
            with self.assertRaises(RuntimeError):
                restore.check_database(db)
            self.assertFalse(db.exists())

if __name__ == "__main__":
    unittest.main()
