import sys,tempfile,unittest,fcntl,os,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_tool_boot_guard import prepare
A='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';B='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
class BootGuard(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.root.chmod(0o700)
  (self.root/'runtime.lock').touch(mode=0o600)
  for name in ['run','libpod','xdg','storage']:
   p=self.root/name;p.mkdir(mode=0o700);(p/'sentinel').write_text(name)
 def tearDown(self):self.tmp.cleanup()
 def test_new_epoch_archives_only_ephemeral_state(self):
  inode=(self.root/'storage/sentinel').stat().st_ino;lock=(self.root/'runtime.lock').stat().st_ino
  value=prepare(self.root,A);archive=Path(value['archive'])
  self.assertEqual((self.root/'storage/sentinel').stat().st_ino,inode);self.assertEqual((self.root/'runtime.lock').stat().st_ino,lock)
  for name in ['run','libpod','xdg']:self.assertEqual((archive/name/'sentinel').read_text(),name);self.assertFalse((self.root/name/'sentinel').exists())
 def test_same_epoch_preserves_new_runtime_and_next_boot_archives(self):
  prepare(self.root,A);(self.root/'run/new').write_text('new state');self.assertFalse(prepare(self.root,A)['changed']);self.assertEqual((self.root/'run/new').read_text(),'new state')
  value=prepare(self.root,B);self.assertEqual((Path(value['archive'])/'run/new').read_text(),'new state')
 def test_running_runtime_lock_refuses_recovery(self):
  with (self.root/'runtime.lock').open('r+') as f:
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):prepare(self.root,A)
  self.assertTrue((self.root/'run/sentinel').exists());self.assertFalse((self.root/'boot-epoch.json').exists())
 def test_symlink_refused_before_any_rotation(self):
  (self.root/'xdg/sentinel').unlink();(self.root/'xdg').rmdir();(self.root/'xdg').symlink_to(self.root/'storage')
  with self.assertRaises(ValueError):prepare(self.root,A)
  self.assertTrue((self.root/'run/sentinel').exists());self.assertTrue((self.root/'storage/sentinel').exists())
if __name__=='__main__':unittest.main()
