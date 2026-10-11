import copy
from pathlib import Path
import sys
import tomllib
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import application_nuc_ingress as entry

class EntryTests(unittest.TestCase):
    def setUp(self):
        self.config = tomllib.loads((ROOT / 'deploy/instances/home.toml').read_text())
        self.original = entry.render.render_caddy(self.config, ('synthetic', '$2a$14$synthetic-test-only'))
    def test_unowned_sites_preserved_and_business_removed(self):
        extra = '\nhttps://unrelated.invalid {\nrespond `unrelated {text}` 200\n}\n'
        candidate, result = entry.candidate_ingress(self.original + extra, self.config)
        self.assertIn(extra.strip(), candidate)
        for block in entry.blocks(self.original):
            header = block.split('{',1)[0].strip()
            if header not in ('http://:5006','http://:5008') and not header.startswith('https://nuc.local:5009,') and ':5443' not in header:
                self.assertIn(block, candidate)
        self.assertEqual(result['external_socket_roles'], ['private-web','private-peer','readonly-web'])
        self.assertIn('forward_auth', candidate)
        self.assertIn('trusted_proxies', candidate)
        self.assertNotIn('uri strip_prefix /tag-api', candidate)
        self.assertNotIn('file_server', candidate)
        self.assertNotIn('$2a$', candidate)
    def test_missing_duplicate_and_already_converted_fail_closed(self):
        candidate, _ = entry.candidate_ingress(self.original, self.config)
        for text in (candidate, self.original.replace('http://:5006','http://:5106'), self.original + '\nhttp://:5006 { respond 200 }'):
            with self.subTest(text=text[-40:]), self.assertRaises(ValueError):
                entry.candidate_ingress(text, self.config)
    def test_unknown_profile_ports_or_missing_auth_rejected(self):
        for section,key,value in [('deployment','profile','vps-direct'),('ports','lan',5106),('features','authelia',False),('features','readonly',False),('domains','public','unexpected.invalid'),('security','container_subnet','10.99.0.0/24')]:
            config=copy.deepcopy(self.config);config[section][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): entry.candidate_ingress(self.original, config)
    def test_unexpected_business_reference_rejected(self):
        with self.assertRaises(ValueError): entry.candidate_ingress(self.original+'\nhttp://unrelated.invalid { reverse_proxy tag-server:8081 }', self.config)
    def test_malformed_block_rejected(self):
        for text in ('http://a {', 'http://a { respond `broken }', 'http://a { respond 200 }}'):
            with self.assertRaises(ValueError): list(entry.blocks(text))
    def test_dual_protocol_transport_preserves_tls_and_public_port(self):
        original=(ROOT/'deploy/haproxy.readonly.cfg').read_text()
        candidate=entry.candidate_readonly_transport(original)
        self.assertEqual(candidate.replace('server native_http host.containers.internal:18182 check','server caddy_http caddy:5008 check'),original)
        profile=(ROOT/'deploy/compose.home-ipv6-cdn.yaml').read_text()
        candidate=entry.candidate_profile(profile)
        self.assertNotIn('LAN_PUBLISH_PORT',candidate)
        self.assertIn('READONLY_ORIGIN_PUBLISH_PORT:-5008',candidate)
        self.assertIn('MAIN_ORIGIN_PUBLISH_PORT:-5009',candidate)
        self.assertIn('host.containers.internal:host-gateway',candidate)
        for function,text in [(entry.candidate_readonly_transport,candidate),(entry.candidate_profile,candidate)]:
            with self.assertRaises(ValueError): function(text)

if __name__ == '__main__': unittest.main()
