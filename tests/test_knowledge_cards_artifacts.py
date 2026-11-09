import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('cards_deploy', Path(__file__).resolve().parents[1] / 'scripts/deploy-knowledge-cards.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class KnowledgeCardArtifactTests(unittest.TestCase):
    def test_fixed_renderer_fonts_and_scripts_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'assets').mkdir()
            (root / 'index.html').write_text('fixture')
            for suffix in ['js', 'css', 'wasm', 'woff', 'woff2', 'ttf']:
                (root / 'assets' / ('fixture.' + suffix)).write_bytes(b'fixture')
            self.assertEqual(len(module.frontend_files(root)), 7)
            for relative in ['secret.json', 'assets/arbitrary.html', 'assets/program.sh']:
                unexpected = root / relative
                unexpected.write_text('fixture')
                with self.assertRaises(AssertionError):
                    module.frontend_files(root)
                unexpected.unlink()
            (root / 'assets/link.js').symlink_to(root / 'index.html')
            with self.assertRaises(AssertionError):
                module.frontend_files(root)

    def test_shared_helix_runtime_is_an_exact_allowlist(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('fixture')
            for name in ['helix/index.html', 'helix/terminal.bundle.js', 'helix/pkg/helix_web_bg.wasm', 'helix/pkg/LICENSE', 'helix/pkg/DUFS-HOST.json']:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'fixture')
            self.assertEqual(len(module.frontend_files(root)), 6)
            for name in ['helix/secret.json', 'helix/pkg/credential.json', 'helix/arbitrary.html', 'helix/pkg/program.sh']:
                p = root / name
                p.write_text('fixture')
                with self.assertRaises(AssertionError):
                    module.frontend_files(root)
                p.unlink()
            (root / 'helix/pkg/link.js').symlink_to(root / 'index.html')
            with self.assertRaises(AssertionError):
                module.frontend_files(root)

if __name__ == '__main__':
    unittest.main()
