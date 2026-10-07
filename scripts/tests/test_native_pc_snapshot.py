import importlib.util
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
from native_pc_snapshot import offline_snapshot, basic_entries
from native_pc_config import serialize_configuration


class OfflineSnapshot(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / 'old-data'; self.data.mkdir()
        with closing(sqlite3.connect(self.data / 'pc.db')) as database, database:
            database.execute('CREATE TABLE fixture (name TEXT)')
            database.execute("INSERT INTO fixture VALUES ('existing')")
        (self.data / 'metadata').mkdir(); (self.data / 'metadata/identity.json').write_text('opaque-fixture')
        (self.data / 'other-state').write_text('retain')
        self.workspace = self.root / 'files'; self.workspace.mkdir()
        self.certs = self.root / 'certs'; self.certs.mkdir(); (self.certs / 'peer.crt').write_text('fixture-cert')
        self.pki = self.root / 'old-caddy'; self.pki.mkdir(); (self.pki / 'opaque-key').write_text('synthetic-only')
        self.config = self.root / 'node.toml'
        self.config.write_text(serialize_configuration({'node': {'id': 'fixture'}, 'locations': [{'id': 'loc_fixture', 'path': '/workspace'}], 'pairing': {'trusted_ca_files': ['/etc/tag-server/certs/peer.crt']}, 'discovery': {'enabled': False}, 'sync': {'peers': []}}))
        self.caddy = self.root / 'Caddyfile'; self.caddy.write_text('basic_auth {\n fixture $2a$10$' + 'a' * 53 + '\n}\n')
        self.env = self.root / 'auth.env'; self.env.write_text('SYNTHETIC=yes'); self.env.chmod(0o600)
        self.dest = self.root / 'new-native'
        self.mounts = {'/data': str(self.data), '/workspace': str(self.workspace), '/etc/tag-server/certs': str(self.certs)}

    def prepare(self):
        return offline_snapshot(self.dest, self.mounts, self.config, [], self.caddy, self.env, self.pki,
                                ['--database', '/data/pc.db', '--metadata-dir', '/data/metadata'], 'sha256:fixture')

    def test_new_private_snapshot_preserves_state_and_rollback_writes(self):
        original = (self.data / 'pc.db').read_bytes()
        self.prepare()
        self.assertEqual((self.data / 'pc.db').read_bytes(), original)
        self.assertEqual((self.dest / 'data/metadata/identity.json').read_text(), 'opaque-fixture')
        self.assertEqual((self.dest / 'data/other-state').read_text(), 'retain')
        with closing(sqlite3.connect(self.dest / 'data/core.db')) as database, database:
            self.assertEqual(database.execute('SELECT name FROM fixture').fetchone()[0], 'existing')
            database.execute("INSERT INTO fixture VALUES ('native-write')")
        rollback = json.loads((self.dest / 'config/container-rollback.json').read_text())
        self.assertEqual(rollback['services']['tag-server']['command'][1], '/data/core.db')
        self.assertEqual(rollback['services']['tag-server']['volumes'], [str(self.dest / 'data') + ':/data:rw'])
        config = tomllib.loads((self.dest / 'config/node.toml').read_text())
        self.assertEqual(config['locations'][0]['id'], 'loc_fixture')
        self.assertEqual(config['pairing']['trusted_ca_files'], [str(self.dest / 'certs/peer.crt')])
        for path in self.dest.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)
        with self.assertRaises(ValueError): self.prepare()

    def test_symlink_or_unsafe_credentials_refused_before_publication(self):
        (self.pki / 'link').symlink_to(self.env)
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.dest.exists())
        (self.pki / 'link').unlink(); self.env.chmod(0o644)
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.dest.exists())

    def test_snapshot_inside_workspace_refused(self):
        self.dest = self.workspace / 'private'
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(self.dest.exists())

    def test_auth_import_and_plaintext_refused(self):
        for text in ['basic_auth {\n import other\n}', 'basic_auth {\n fixture plaintext\n}']:
            with self.assertRaises(ValueError): basic_entries(text)

    def test_writer_restart_before_publish_refuses_snapshot(self):
        calls = []
        def stopped():
            calls.append(True)
            if len(calls) == 2: raise ValueError('source writer restarted')
        with self.assertRaises(ValueError):
            offline_snapshot(self.dest, self.mounts, self.config, [], self.caddy, self.env, self.pki,
                             ['--database', '/data/pc.db'], 'sha256:fixture', ensure_offline=stopped)
        self.assertEqual(len(calls), 2)
        self.assertFalse(self.dest.exists())
        self.assertEqual(list(self.root.glob('new-native.pending-*')), [])

    def test_new_destination_created_before_publish_is_never_overwritten(self):
        calls = []
        def stopped():
            calls.append(True)
            if len(calls) == 2: self.dest.mkdir()
        with self.assertRaises(FileExistsError):
            offline_snapshot(self.dest, self.mounts, self.config, [], self.caddy, self.env, self.pki,
                             ['--database', '/data/pc.db'], 'sha256:fixture', ensure_offline=stopped)
        self.assertTrue(self.dest.is_dir())
        self.assertEqual(list(self.dest.iterdir()), [])
        self.assertEqual(list(self.root.glob('new-native.pending-*')), [])

    def test_serialization_preserves_nested_unicode_and_dates(self):
        import datetime
        value = {'a': {'date': datetime.date(2026, 10, 7), 'tables': [{'a': '中文\n"\\'}]}, 'empty': []}
        self.assertEqual(tomllib.loads(serialize_configuration(value)), value)


if __name__ == '__main__': unittest.main()
