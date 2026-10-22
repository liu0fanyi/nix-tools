"""Check default browser guard and unrelated association preservation."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("mimeapps", Path(__file__).resolve().parents[1] / "scripts/sync-mimeapps.py")
mimeapps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mimeapps)

class MimeDefaultsTests(unittest.TestCase):
    def test_browser_and_other_anchors_survive_external_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home.nix"
            config = root / "mimeapps.list"
            home.write_text('xdg.mimeApps = { defaultApplications = {\n "text/html" = [ "tag-browser.desktop" ];\n}; };')
            config.write_text('[Default Applications]\ntext/html=other.desktop;\nx-scheme-handler/codex=wrong.desktop;\napplication/pdf=reader.desktop;\n')
            with patch.object(mimeapps, "HOME_NIX", home), patch.object(mimeapps, "MIMEAPPS_PATH", config), patch("sys.argv", ["sync-mimeapps.py", "--apply"]), contextlib.redirect_stdout(io.StringIO()):
                mimeapps.main()
                actual = mimeapps.parse_home_nix_defaults()
            for mime, desktop in mimeapps.LOCKED_ANCHORS.items():
                self.assertEqual(actual[mime], desktop)
            self.assertEqual(actual["application/pdf"], "reader.desktop")

if __name__ == "__main__":
    unittest.main()
