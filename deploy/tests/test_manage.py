from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


DEPLOY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPLOY_DIR / "scripts"))

import manage


class SecretPermissionTests(unittest.TestCase):
    def test_normalize_removes_group_and_world_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            secret_dir = Path(temp_name) / "secrets"
            secret_dir.mkdir(mode=0o775)
            secret_dir.chmod(0o775)
            secret = secret_dir / "token"
            secret.write_text("secret\n", encoding="utf-8")
            secret.chmod(0o664)
            readme = secret_dir / "README.md"
            readme.write_text("documentation\n", encoding="utf-8")
            readme.chmod(0o664)

            errors, changed = manage.normalize_secret_permissions(secret_dir)

            self.assertEqual(errors, [])
            self.assertEqual(changed, [secret_dir, secret])
            self.assertEqual(secret_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
            self.assertEqual(readme.stat().st_mode & 0o777, 0o664)

    def test_normalize_rejects_secret_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            secret_dir = root / "secrets"
            secret_dir.mkdir(mode=0o700)
            target = root / "target"
            target.write_text("secret\n", encoding="utf-8")
            target.chmod(0o664)
            link = secret_dir / "token"
            link.symlink_to(target)

            errors, changed = manage.normalize_secret_permissions(secret_dir)

            self.assertEqual(changed, [])
            self.assertEqual(
                errors,
                [f"secret path must not be a symbolic link: {link}"],
            )
            self.assertEqual(target.stat().st_mode & 0o777, 0o664)

    def test_normalize_does_not_take_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            secret_dir = Path(temp_name) / "secrets"
            secret_dir.mkdir(mode=0o775)
            secret_dir.chmod(0o775)

            with mock.patch.object(manage.os, "getuid", return_value=os.getuid() + 1):
                errors, changed = manage.normalize_secret_permissions(secret_dir)

            self.assertEqual(changed, [])
            self.assertEqual(
                errors,
                [f"secret directory is not owned by the current user: {secret_dir}"],
            )
            self.assertEqual(secret_dir.stat().st_mode & 0o777, 0o775)


class RequiredMountTests(unittest.TestCase):
    def test_wait_for_mounts_accepts_mounted_paths(self) -> None:
        self.assertEqual(manage.wait_for_mounts([Path("/")], wait_seconds=0), [])

    def test_wait_for_mounts_reports_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "not-mounted"
            path.mkdir()

            self.assertEqual(
                manage.wait_for_mounts([path], wait_seconds=0),
                [path],
            )


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
