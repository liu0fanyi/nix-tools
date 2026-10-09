from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]))
from native_nuc_bundle import normalize_closure
class Closure(unittest.TestCase):
    def test_nix_v1_list_and_v2_mapping_match(self):
        entry={'path':'/nix/store/example','narHash':'sha256:fixture','narSize':12}
        mapped={'/nix/store/example':{'narHash':'sha256:fixture','narSize':12,'registrationTime':123}}
        self.assertEqual(normalize_closure([entry]),normalize_closure(mapped))
    def test_mutable_store_metadata_does_not_change_content_manifest(self):
        a={'/nix/store/example':{'narHash':'hash','narSize':12,'signatures':['one']}}
        b={'/nix/store/example':{'narHash':'hash','narSize':12,'signatures':['two'],'registrationTime':99}}
        self.assertEqual(normalize_closure(a),normalize_closure(b))
if __name__=='__main__':unittest.main()
