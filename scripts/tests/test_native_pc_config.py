import importlib.util
from pathlib import Path
import unittest
from copy import deepcopy

spec = importlib.util.spec_from_file_location('native_pc_config', Path(__file__).parents[1] / 'native_pc_config.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfigurationAdaptation(unittest.TestCase):
    def setUp(self):
        self.config = {'node': {'id': 'fixture-pc', 'name': 'PC'},
            'locations': [{'id': 'loc_pc', 'node_id': 'fixture-pc', 'path': '/workspace', 'writable': True},
                          {'id': 'nested', 'path': '/workspace/project/中文 目录'}],
            'pairing': {'enabled': True, 'trusted_ca_files': ['/etc/tag-server/certs/remote.crt']},
            'sync': {'peers': [{'node_id': 'fixture-peer', 'url': 'https://peer.invalid:5009'}]},
            'discovery': {'enabled': True, 'external_agent': True, 'advertise_url': 'https://pc.invalid:5009'},
            'unknown': {'value': '/workspace/not-a-path-field'}}
        self.mounts = {'/workspace': '/home/fixture/files', '/workspace/project': '/data/fixture',
                       '/etc/tag-server/certs': '/home/fixture/certs'}
        self.args = ['--node-id', 'fixture-pc', '--metadata-dir', '/data/metadata',
                     '--advertise-url', 'https://pc.invalid:5009', '--advertise-ip', '192.168.1.100', '--interface', 'eno1']

    def test_preserves_identity_peers_and_source(self):
        before = deepcopy(self.config)
        candidate, layout = module.adapt_configuration(self.config, self.mounts, self.args)
        self.assertEqual(self.config, before)
        for field in ['node', 'sync', 'unknown']:
            self.assertEqual(candidate[field], before[field])
        self.assertEqual(candidate['locations'][0]['id'], 'loc_pc')
        self.assertEqual(candidate['locations'][1]['path'], '/data/fixture/中文 目录')
        self.assertEqual(candidate['pairing']['trusted_ca_files'], ['/home/fixture/certs/remote.crt'])
        self.assertEqual(layout, {'workspace': '/home/fixture/files', 'workspace_mounts': {'project': '/data/fixture'}})
        self.assertFalse(candidate['discovery']['external_agent'])
        self.assertEqual(candidate['discovery']['interfaces'], ['eno1'])

    def test_missing_mapping_or_unsafe_path_fails(self):
        for value in ['/unmapped/file', '/workspace/../secret', '/workspace/project/../../secret', 'relative', '/workspace/a\n']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.translate_path(value, self.mounts)

    def test_prefix_is_component_aware(self):
        with self.assertRaises(ValueError):
            module.translate_path('/workspace-other/file', self.mounts)

    def test_discovery_mismatch_and_unexpected_arguments_fail(self):
        for index, value in [(1, 'other'), (3, '/wrong'), (5, 'https://other.invalid'), (7, '127.0.0.1'), (7, '203.0.113.1'), (9, 'eno1\n')]:
            args = self.args.copy()
            args[index] = value
            with self.subTest(index=index), self.assertRaises(ValueError):
                module.adapt_configuration(self.config, self.mounts, args)
        for args in [self.args[:-2], self.args + ['--interface', 'eno2'], self.args + ['--unknown', 'x']]:
            with self.assertRaises(ValueError):
                module.adapt_configuration(self.config, self.mounts, args)

    def test_disabled_discovery_needs_no_agent(self):
        self.config['discovery']['enabled'] = False
        candidate, _ = module.adapt_configuration(self.config, self.mounts, [])
        self.assertEqual(candidate['discovery'], self.config['discovery'])

    def test_credentials_or_route_in_origin_rejected(self):
        for origin in ['http://pc.invalid', 'https://user@pc.invalid', 'https://pc.invalid/path', 'https://pc.invalid/?token=x']:
            self.config['discovery']['advertise_url'] = origin
            self.args[5] = origin
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                module.adapt_configuration(self.config, self.mounts, self.args)


if __name__ == '__main__':
    unittest.main()


class PeerNetwork(unittest.TestCase):
    def test_approved_origin_and_hosts_preserve_source_and_signature_policy(self):
        source = {'sync': {'require_signatures': False, 'peers': ['http://nuc.local:5006/tag-api']}}
        before = deepcopy(source)
        approved = [{'url': 'https://nuc.local:5009', 'identity': {'node_id': 'nuc'}}]
        target, hosts = module.adapt_peer_network(source, approved, ['nuc.local:192.168.1.12'], '127.0.0.1 localhost\n')
        self.assertEqual(source, before)
        self.assertEqual(target['sync'], {'require_signatures': False, 'peers': ['https://nuc.local:5009']})
        self.assertIn('192.168.1.12 nuc.local', hosts)

    def test_invalid_alias_and_conflict_refused(self):
        for aliases, hosts in [(['nuc.local:invalid'], ''), (['bad host:192.168.1.12'], ''), (['nuc.local:192.168.1.12'], '192.168.1.99 nuc.local')]:
            with self.assertRaises(ValueError): module.adapt_peer_network({}, [], aliases, hosts)

    def test_unapproved_and_credential_origins_unchanged(self):
        source = {'sync': {'peers': ['http://unapproved.local:5006', 'http://user:secret@nuc.local:5006']}}
        target, _ = module.adapt_peer_network(source, [{'url': 'https://nuc.local:5009', 'identity': {'node_id': 'nuc'}}], [], '')
        self.assertEqual(source, target)
