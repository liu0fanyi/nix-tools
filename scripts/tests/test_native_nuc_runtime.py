import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_nuc_runtime import adapt_environment

class RuntimeTests(unittest.TestCase):
    def adapt(self,source,role='private'):
        return adapt_environment(source,role=role,state_root='/private/state',models='/private/models',whisper_package='/nix/store/test-whisper')
    def test_private_secret_preservation_and_path_mapping(self):
        source={'TOKEN':'synthetic-secret','DUFS_WHISPER_MODEL':'/models/custom.bin'}
        result=self.adapt(source)
        self.assertEqual(result['TOKEN'],source['TOKEN'])
        self.assertEqual(result['DUFS_WHISPER_MODEL'],'/private/models/custom.bin')
        self.assertEqual(result['HOME'],'/private/state/private/git-home')
        self.assertNotIn('HOME',source)
    def test_defaults_and_already_host_model(self):
        self.assertEqual(self.adapt({})['DUFS_WHISPER_MODEL'],'/private/models/ggml-small-q5_1.bin')
        self.assertEqual(self.adapt({'DUFS_WHISPER_MODEL':'/private/models/custom.bin'})['DUFS_WHISPER_MODEL'],'/private/models/custom.bin')
    def test_readonly_preserves_source_without_adding_private_paths(self):
        self.assertEqual(self.adapt({'TOKEN':'synthetic-secret'},'readonly'),{'TOKEN':'synthetic-secret'})
    def test_unsafe_or_unreviewed_configuration_rejected(self):
        for source in [{'DUFS_WHISPER_MODEL':'/models/../secret'}, {'DUFS_WHISPER_CLI':'/custom/whisper'},
                       {'HOME':'/custom/home'}, {'GIT_SSH_COMMAND':'ssh -o StrictHostKeyChecking=no'},
                       {'TAG_NATIVE_PDF_IMAGE':'latest'}]:
            with self.assertRaises(ValueError):self.adapt(source)
        with self.assertRaises(ValueError):self.adapt({'HOME':'/root'},'readonly')

if __name__=='__main__':unittest.main()
