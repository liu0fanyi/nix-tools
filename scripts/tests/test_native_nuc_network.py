import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from native_nuc_network import adapt_network

class Network(unittest.TestCase):
    def setUp(self):
        self.peers=[{'identity':{'node_id':'pc'},'url':'https://liu-bigpc.local:5009'}]
    def test_approved_target_and_alias_survive_without_signature_policy_change(self):
        source={'node':{'id':'nuc'},'sync':{'require_signatures':False}}
        new,hosts=adapt_network(source,self.peers,['liu-bigpc.local:192.168.1.100'],'127.0.0.1 localhost\n')
        self.assertEqual(new['sync']['peer_nodes'],{'pc':'https://liu-bigpc.local:5009'})
        self.assertFalse(new['sync']['require_signatures']);self.assertNotIn('peer_nodes',source['sync'])
        self.assertIn('192.168.1.100 liu-bigpc.local',hosts)
    def test_conflicting_routes_and_hosts_are_refused(self):
        with self.assertRaises(ValueError):adapt_network({'sync':{'peer_nodes':{'pc':'https://elsewhere:5009'}}},self.peers,['liu-bigpc.local:192.168.1.100'],'')
        with self.assertRaises(ValueError):adapt_network({},self.peers,['liu-bigpc.local:192.168.1.100'],'192.168.1.9 liu-bigpc.local\n')
    def test_unapproved_or_unmapped_peer_is_not_broadcast_target(self):
        new,_=adapt_network({},[],['liu-bigpc.local:192.168.1.100'],'');self.assertEqual(new['sync']['peer_nodes'],{})
        new,_=adapt_network({},self.peers,[],'');self.assertEqual(new['sync']['peer_nodes'],{})
