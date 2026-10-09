import importlib.util
from pathlib import Path
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy/scripts'))
import render
spec = importlib.util.spec_from_file_location('native_nuc_ingress', ROOT / 'scripts/native_nuc_ingress.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class IngressTests(unittest.TestCase):
    def setUp(self):
        config = tomllib.loads((ROOT / 'deploy/instances/home.toml').read_text())
        self.original = render.render_caddy(config, ('synthetic', '$2a$14$synthetic-test-only'))

    def test_complete_existing_routes_retained(self):
        candidate, counts = module.adapt_ingress(self.original)
        self.assertEqual(set(module.UPSTREAMS), set(counts))
        restored = candidate
        for upstream, socket in module.UPSTREAMS.items(): restored = restored.replace(socket, upstream)
        self.assertEqual(self.original, restored)
        self.assertIn('Read-only tag service', candidate)
        self.assertIn('basic_auth', candidate)
        self.assertIn('unix//run/host-ttyd/ttyd.sock', candidate)
        self.assertNotIn('reverse_proxy tag-server:8081', candidate)

    def test_incomplete_pc_gateway_rejected(self):
        with self.assertRaises(ValueError): module.adapt_ingress('reverse_proxy tag-server:8081\n')

    def test_unexpected_reference_rejected(self):
        with self.assertRaises(ValueError): module.adapt_ingress(self.original+'\n# tag-server:8081\n')

    def test_already_adapted_candidate_rejected(self):
        candidate, _ = module.adapt_ingress(self.original)
        with self.assertRaises(ValueError): module.adapt_ingress(candidate)

if __name__ == '__main__': unittest.main()
