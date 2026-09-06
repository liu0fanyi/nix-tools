import importlib.util
from pathlib import Path
import unittest

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

install = module("host_install", "host-install.py")
backup = module("nuc_backup", "nuc-backup.py")

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"hostname": "nuc", "product": "NUC8i5BEH", "disk": "/dev/disk/by-id/test", "disk_bytes": 123,
                        "installation_enabled": True, "reason": "not approved"}
        self.report = {"hostname": "nuc", "arch": "x86_64", "product": "NUC8i5BEH", "disk_bytes": "123",
                       "uefi": True, "efi_writable": True, "root": True, "kexec_disabled": "0", "lockdown": "[none]",
                       "wired": [{"carrier": "1", "ipv4": "2: eno1 inet 192.168.1.12/24 scope global"}],
                       "ssh_connection": "192.168.1.3 12345 192.168.1.12 22"}
    def test_matching_device(self):
        self.assertEqual(install.assess(self.profile, self.report), [])
    def test_wrong_disk(self):
        self.report["disk_bytes"] = ""
        self.assertTrue(any("disk" in s for s in install.assess(self.profile, self.report)))
    def test_wifi_ssh_even_with_wired_link(self):
        self.report["ssh_connection"] = "192.168.1.3 12 192.168.1.99 22"
        self.assertTrue(any("SSH" in s for s in install.assess(self.profile, self.report)))
    def test_wrong_host(self):
        self.report["hostname"] = "liu-bigpc"
        self.assertTrue(install.assess(self.profile, self.report))
    def test_no_automatic_approval(self):
        self.profile["installation_enabled"] = False
        self.assertIn("not approved", install.assess(self.profile, self.report))
    def test_no_privilege(self):
        self.report["root"] = False
        self.assertTrue(any("sudo" in s for s in install.assess(self.profile, self.report)))
    def test_backup_never_deletes_or_follows_links(self):
        cmd = backup.copy_args(["/home/liou"], Path("/tmp/test"))
        self.assertNotIn("--delete", cmd)
        self.assertNotIn("--copy-links", cmd)
        self.assertIn("--relative", cmd)
        self.assertIn("--checksum", backup.copy_args(["/home/liou"], Path("/tmp/test"), True))
    def test_backup_symlink_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "link"
            p.symlink_to("/tmp")
            with self.assertRaises(RuntimeError):
                backup.safe_directory(p / "snapshot")

if __name__ == "__main__":
    unittest.main()
