import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).parents[1] / "../config/agent-rules/skills/work-progress/scripts/overview.py"
spec = importlib.util.spec_from_file_location("overview", source.resolve())
overview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overview)


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "specs/001-demo").mkdir(parents=True)
        (self.root / "specs/001-demo/tasks.md").write_text("- [ ] 已确认的下一步")
        (self.root / "README.md").write_text("repo")
        self.text = "# Demo\n[计划](001-demo/tasks.md) · [仓库](../README.md)\n## 最近变化\n" + overview.START + "\n" + overview.END + "\n"
        (self.root / "specs/README.md").write_text(self.text)
        self.git("add", ".")
        self.git("commit", "-qm", "修复编辑器跳动", "-m", "SYNTHETIC_SECRET_BODY")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def test_recent_uses_subjects_only_filters_maintenance_and_escapes_markup(self):
        for i in range(10):
            self.git("commit", "--allow-empty", "-qm", f"feat: 变化 {i}")
        self.git("commit", "--allow-empty", "-qm", "docs: 更新总纲")
        self.git("commit", "--allow-empty", "-qm", "feat: [unsafe](https://example.invalid)")
        result = overview.refreshed(self.root, self.text)
        self.assertEqual(len([line for line in result.splitlines() if line.startswith("- ")]), 8)
        self.assertNotIn("更新总纲", result)
        self.assertNotIn("SYNTHETIC_SECRET_BODY", result)
        self.assertIn(r"\[unsafe\]", result)
        self.assertIn("已确认的下一步", (self.root / "specs/001-demo/tasks.md").read_text())

    def test_entry_relocates_links_and_rejects_missing_and_escape(self):
        entry = overview.reading_entry(self.root, self.text)
        self.assertIn("](specs/001-demo/tasks.md)", entry)
        self.assertIn("](README.md)", entry)
        for bad in ["../../outside.md", "missing.md"]:
            with self.assertRaises(ValueError):
                overview.reading_entry(self.root, f"[bad]({bad})")
        (self.root / "specs/link").symlink_to("/etc/hosts")
        with self.assertRaises(ValueError):
            overview.reading_entry(self.root, "[bad](link)")

    def test_dry_run_changes_neither_local_source_nor_remote(self):
        src = self.root / "specs/README.md"
        before = src.read_bytes()
        subprocess.run(["python3", str(source.resolve()), "--repo", str(self.root), "--write", "--dry-run"], check=True, capture_output=True)
        self.assertEqual(src.read_bytes(), before)
        with patch.object(overview.subprocess, "run") as run:
            overview.publish(self.root, self.text, "/home/liou/dufs-lan/todos/demo", True)
            run.assert_not_called()

    def test_publish_is_one_file_no_delete_and_checks_checksum(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            if command[0] == "rsync":
                self.assertEqual(Path(command[-2]).read_text(), overview.reading_entry(self.root, self.text))
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        with patch.object(overview.subprocess, "run", side_effect=run):
            overview.publish(self.root, self.text, "/home/liou/dufs-lan/todos/demo", False)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][-1], "liou@nuc.local:/home/liou/dufs-lan/todos/demo/README.md")
        self.assertIn("--checksum", calls[1])
        self.assertIn("--dry-run", calls[2])
        self.assertTrue(all("--delete" not in call for call in calls))

    def test_rejects_shared_roots_wrong_area_and_symlink_source(self):
        for dest in ["/home/liou/dufs-lan/todos", "/home/liou/dufs-lan/todos/..", "/home/liou/dufs/demo", "/tmp/demo"]:
            with patch.object(overview.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    overview.publish(self.root, self.text, dest, False)
                run.assert_not_called()
        src = self.root / "specs/README.md"
        src.unlink()
        src.symlink_to(self.root / "README.md")
        with self.assertRaises(ValueError):
            overview.repository(self.root)
