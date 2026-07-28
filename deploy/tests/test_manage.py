from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


DEPLOY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPLOY_DIR / "scripts"))

import manage


class BackupRetentionTests(unittest.TestCase):
    def test_prune_backups_keeps_latest_timestamped_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            names = [
                "20260726-100000-000000001",
                "20260726-110000-000000002",
                "20260726-120000-000000003",
                "notes",
            ]
            for name in names:
                (root / name).mkdir()

            removed = manage.prune_backups(root, 2)

            self.assertEqual(
                [path.name for path in removed],
                ["20260726-100000-000000001"],
            )
            self.assertFalse((root / names[0]).exists())
            self.assertTrue((root / names[1]).is_dir())
            self.assertTrue((root / names[2]).is_dir())
            self.assertTrue((root / "notes").is_dir())

    def test_zero_retention_limit_disables_pruning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            backup = root / "20260726-100000-000000001"
            backup.mkdir()

            self.assertEqual(manage.prune_backups(root, 0), [])
            self.assertTrue(backup.is_dir())


if __name__ == "__main__":
    unittest.main()
