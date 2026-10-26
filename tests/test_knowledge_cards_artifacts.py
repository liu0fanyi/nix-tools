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

if __name__ == '__main__':
    unittest.main()
