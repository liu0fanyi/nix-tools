import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "nuc-backup.py"
if not SCRIPT.exists():
    SCRIPT = Path(__file__).with_name("nuc-backup.py")
spec = importlib.util.spec_from_file_location("nuc_backup", SCRIPT)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)

class BackupTests(unittest.TestCase):
    def test_business_scope_is_bounded(self):
        sources = backup.BUSINESS_REQUIRED + backup.BUSINESS_OPTIONAL
        self.assertIn("/home/liou/dufs", sources)
        self.assertIn("/home/liou/dufs-lan", sources)
        self.assertIn("/home/liou/.local/share/caddy", sources)
        self.assertIn("/media/liou/project/me/nix-tools/deploy", sources)
        for broad in ["/home/liou", "/etc", "/root", "/var/lib/containers",
                      "/home/liou/.local/share/containers", "/home/liou/.local/state/syncthing"]:
            self.assertNotIn(broad, sources)

    def test_business_requires_both_databases(self):
        with patch.object(backup.Path, "is_dir", return_value=True), patch.object(backup.Path, "is_symlink", return_value=False), patch.object(backup.Path, "is_file", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "database missing"):
                backup.select_sources("business")

    def test_fresh_copy_checksums_only_on_verification(self):
        self.assertNotIn("--checksum", backup.copy_args(["/source"], Path("/new")))
        self.assertIn("--checksum", backup.copy_args(["/source"], Path("/new"), verify=True))

    def test_root_podman_rejects_user_executable(self):
        with patch.object(backup.Path, "resolve", return_value=Path("/home/liou/bin/podman")):
            with self.assertRaises(RuntimeError):
                backup.root_podman()

    def test_root_check_uses_absolute_binary(self):
        from subprocess import CompletedProcess
        binary = "/nix/store/test-podman/bin/podman"
        def fake_run(args, **kwargs):
            if "is-active" in args:
                return CompletedProcess(args, 3, "inactive\n", "")
            return CompletedProcess(args, 0, "", "")
        with patch.object(backup, "root_podman", return_value=binary), patch.object(backup, "capture", return_value=""), patch.object(backup.subprocess, "run", side_effect=fake_run) as run:
            backup.require_quiet()
            self.assertTrue(any(c.args[0] == [binary, "ps", "-q"] for c in run.call_args_list))

    def test_only_special_notices_are_ignored(self):
        skipped, diff = backup.classify_verification('skipping non-regular file "socket"\n>fc.t...... /data/db\nrsync: error\n')
        self.assertEqual(len(skipped), 1)
        self.assertEqual(len(diff), 2)

    def test_empty_verification(self):
        self.assertEqual(backup.classify_verification("\n"), ([], []))

    def test_previous_path_rejected(self):
        for name in ["../old", "/tmp/old", "", "latest"]:
            with self.assertRaises(RuntimeError):
                backup.previous_root(name, [])

    def test_incremental_is_non_destructive(self):
        args = backup.copy_args(["/source"], Path("/new"), previous=Path("/old/rootfs"))
        self.assertIn("--checksum", args)
        self.assertIn("--link-dest=/old/rootfs", args)
        for option in ["--inplace", "--delete", "--append"]:
            self.assertNotIn(option, args)
        verify = backup.copy_args(["/source"], Path("/new"), verify=True)
        self.assertIn("--dry-run", verify)
        self.assertFalse(any(x.startswith("--link-dest") for x in verify))

if __name__ == "__main__":
    unittest.main()
