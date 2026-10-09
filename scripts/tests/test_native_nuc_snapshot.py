import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import tomllib
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]))
from native_nuc_snapshot import snapshot,parse_environment,environment_text
from native_nuc_plan import PREFIX,REPLACE,KEEP

class DoubleSnapshot(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.roles={}
        for role in ['private','readonly']:
            source=self.root/(role+'-source');source.mkdir();work=self.root/(role+'-files');work.mkdir()
            with closing(sqlite3.connect(source/'tag_all.db')) as db,db:
                db.execute('CREATE TABLE fixture (name TEXT)');db.execute('INSERT INTO fixture VALUES (?)',(role,))
            metadata=source/'metadata';metadata.mkdir();(metadata/'identity').write_text(role+'-identity')
            (metadata/'certs').mkdir();(metadata/'certs/pc-root.crt').write_text('synthetic-cert')
            self.roles[role]={'mounts':{'/data':str(source),'/workspace':str(work)}}
        self.dest=self.root/'native';self.config=self.root/'node.toml'
        self.config.write_text('[node]\nid="nuc"\n[pairing]\nenabled=true\ntrusted_ca_files=["/data/metadata/certs/pc-root.crt"]\n[discovery]\nenabled=true\nexternal_agent=true\nadvertise_url="https://nuc.local:5009"\n')
        self.args=['--node-id','nuc','--metadata-dir','/data/metadata','--advertise-url','https://nuc.local:5009','--advertise-ip','192.168.1.12','--interface','wlan0']
        self.env=self.root/'env';self.env.write_text("TAG_PEER_ADMIN_TOKEN='synthetic-only-token-123456789012345678'\nEXAMPLE='has $literal and spaces'\n");self.env.chmod(0o600)
        self.caddy=self.root/'Caddyfile';self.caddy.write_text('original full ingress')
        self.pki=self.root/'pki';self.pki.mkdir();(self.pki/'root.key').write_text('synthetic-ca')
    def prepare(self,check=lambda:None):
        return snapshot(self.dest,self.roles,source_config=self.config,discovery_args=self.args,environment_files=[self.env],
            caddyfile=self.caddy,pki=self.pki,whisper_package='/nix/store/test-whisper',models='/home/liou/models',source_images={PREFIX+n+'_1':'a'*64 for n in REPLACE+KEEP},ensure_offline=check)
    def test_double_state_identity_ca_and_new_writes_preserved(self):
        originals={r:(Path(e['mounts']['/data'])/'tag_all.db').read_bytes() for r,e in self.roles.items()}
        result=self.prepare();self.assertTrue(result['both_sqlite_integrity'])
        for role,entry in self.roles.items():
            self.assertEqual((Path(entry['mounts']['/data'])/'tag_all.db').read_bytes(),originals[role])
            db=self.dest/role/'state/core.db'
            with closing(sqlite3.connect(db)) as conn,conn:
                self.assertEqual(conn.execute('SELECT name FROM fixture').fetchone()[0],role)
                conn.execute("INSERT INTO fixture VALUES ('native-new-write')")
            self.assertEqual((self.dest/role/'state/metadata/identity').read_text(),role+'-identity')
        private=tomllib.loads((self.dest/'private/config/node.toml').read_text())
        self.assertEqual(private['pairing']['trusted_ca_files'],[str(self.dest/'private/state/metadata/certs/pc-root.crt')])
        self.assertFalse(private['discovery']['external_agent']);self.assertEqual(private['discovery']['interfaces'],['wlan0'])
        readonly=tomllib.loads((self.dest/'readonly/config/node.toml').read_text());self.assertEqual(readonly['node']['id'],'nuc');self.assertFalse(readonly['sync']['enabled'])
        self.assertNotIn('TAG_PEER_ADMIN_TOKEN',(self.dest/'readonly/config/service.env').read_text())
        self.assertEqual((self.dest/'backup/pki/root.key').read_text(),'synthetic-ca')
        for p in self.dest.rglob('*'):self.assertEqual(p.stat().st_mode&0o777,0o700 if p.is_dir() else 0o600)
        with self.assertRaises(ValueError):self.prepare()
    def test_active_writer_refused_before_any_copy(self):
        def active():raise ValueError('writer still running')
        with self.assertRaises(ValueError):self.prepare(active)
        self.assertFalse(self.dest.exists());self.assertEqual(list(self.root.glob('native.pending-*')),[])
    def test_writer_restart_refused_before_publish(self):
        calls=[]
        def restarted():
            calls.append(True)
            if len(calls)==2:raise ValueError('writer restarted')
        with self.assertRaises(ValueError):self.prepare(restarted)
        self.assertFalse(self.dest.exists());self.assertEqual(list(self.root.glob('native.pending-*')),[])
    def test_ca_rotation_refused_and_sources_unchanged(self):
        calls=[]
        def rotated():
            calls.append(True)
            if len(calls)==2:(self.pki/'root.key').write_text('rotated synthetic key')
        with self.assertRaises(ValueError):self.prepare(rotated)
        self.assertFalse(self.dest.exists())
    def test_existing_empty_destination_never_overwritten(self):
        calls=[]
        def race():
            calls.append(True)
            if len(calls)==2:self.dest.mkdir()
        with self.assertRaises(OSError):self.prepare(race)
        self.assertEqual(list(self.dest.iterdir()),[])
    def test_symlink_data_and_unsafe_credentials_rejected(self):
        (Path(self.roles['private']['mounts']['/data'])/'link').symlink_to(self.env)
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse(self.dest.exists())
    def test_environment_never_executes_expansion_or_commands(self):
        for text in ['TOKEN=$(echo bad)','TOKEN=`echo bad`','TOKEN=foo;echo bad','TOKEN=$HOME','TOKEN=x\nTOKEN=y']:
            with self.assertRaises(ValueError):parse_environment(text)
        self.assertEqual(parse_environment("TOKEN='literal $value'"),{'TOKEN':'literal $value'})
        self.assertEqual(parse_environment('TOKEN=literal#value'),{'TOKEN':'literal#value'})
        with self.assertRaises(ValueError):parse_environment('TOKEN=x # unsupported inline comment')
        self.assertIn('"has spaces"',environment_text({'TOKEN':'has spaces'}))

    def test_corrupt_database_never_publishes_partial_double_snapshot(self):
        source=Path(self.roles['readonly']['mounts']['/data'])/'tag_all.db'
        source.write_bytes(b'synthetic corrupted database')
        with self.assertRaises(sqlite3.DatabaseError):self.prepare()
        self.assertFalse(self.dest.exists());self.assertEqual(list(self.root.glob('native.pending-*')),[])
        self.assertEqual(source.read_bytes(),b'synthetic corrupted database')
    def test_bound_media_workspace_must_not_receive_private_snapshot(self):
        media=self.root/'media';media.mkdir()
        self.roles['private']['mounts']['/workspace/media']=str(media)
        self.dest=media/'private-state'
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse(self.dest.exists())
if __name__=='__main__':unittest.main()

