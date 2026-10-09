import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).parents[1]))
import test_native_pc_snapshot as fixtures
from native_pc_mode_guard import NAMES, UNITS, validate
from native_pc_snapshot import offline_snapshot


class StartupGuard(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OfflineSnapshot()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        ca = f.pki / 'pki/authorities/local'; ca.mkdir(parents=True)
        for name in ['root.crt', 'root.key', 'intermediate.crt', 'intermediate.key']:
            (ca / name).write_text('synthetic-ca-metadata-only')
        self.images = {name.removeprefix('dufs-plus-pc_').removesuffix('_1'): 'sha256:' + 'a' * 64 for name in NAMES}
        self.images['peer-discovery'] = 'sha256:' + 'c' * 64
        offline_snapshot(f.dest, f.mounts, f.config, [], f.caddy, f.env, f.pki,
                         ['--database', '/data/pc.db'], self.images['tag-server'], source_images=self.images)
        self.saved = json.loads((f.dest / 'config/container-rollback.json').read_text())
        self.records = {}
        for name in NAMES:
            service = name.removeprefix('dufs-plus-pc_').removesuffix('_1')
            mounts = {}
            if service in {'tag-server', 'dufs'}:
                mounts.update({'/workspace': '/home/liou/dufs-lan', '/workspace/project': '/data/project'})
            if service in {'tag-server', 'peer-discovery'}: mounts['/data'] = str(f.dest / 'data')
            if service == 'peer-gateway': mounts['/data'] = str(f.dest / 'peer-caddy')
            if service == 'tag-server': mounts['/etc/tag-server/certs'] = str(f.dest / 'certs')
            self.records[name] = {'Name': name, 'Image': self.images[service],
                'Config': {'Labels': {'io.podman.compose.project': 'dufs-plus-pc'}, 'Cmd': self.saved['services'][service].get('command', [])},
                'State': {'Running': False},
                'Mounts': [{'Destination': target, 'Source': source, 'Type': 'bind'} for target, source in mounts.items()]}
        self.units = dict.fromkeys(UNITS, 'inactive')

    def container_mode(self):
        marker = self.fixture.dest / 'container-mode'
        marker.write_text('explicit-container-fallback\n'); marker.chmod(0o600)

    def test_native_accepts_only_all_stopped_and_no_container_mode(self):
        validate('native', self.fixture.dest, self.records)
        for name in NAMES:
            records = copy.deepcopy(self.records); records[name]['State']['Running'] = True
            with self.assertRaises(ValueError): validate('native', self.fixture.dest, records)
        self.container_mode()
        with self.assertRaises(ValueError): validate('native', self.fixture.dest, self.records)

    def test_container_requires_all_native_units_stopped(self):
        self.container_mode()
        validate('container', self.fixture.dest, self.records, self.units)
        for name in UNITS:
            for state in ['active', 'activating', 'deactivating', 'unknown', '']:
                with self.subTest(name=name, state=state):
                    units = self.units | {name: state}
                    if name == 'tag-all-tools.service' and state == 'unknown':
                        # The optional tools unit is absent in the legacy core-only candidate.
                        validate('container', self.fixture.dest, self.records, units)
                    else:
                        with self.assertRaises(ValueError): validate('container', self.fixture.dest, self.records, units)

    def test_old_database_ca_workspace_or_command_is_refused(self):
        self.container_mode()
        for name in NAMES:
            for entry in self.records[name]['Mounts']:
                records = copy.deepcopy(self.records)
                match = next(m for m in records[name]['Mounts'] if m['Destination'] == entry['Destination'])
                match['Source'] = '/unexpected/old-state'
                with self.assertRaises(ValueError): validate('container', self.fixture.dest, records, self.units)
        records = copy.deepcopy(self.records)
        records[NAMES[0]]['Config']['Cmd'] = ['--database', '/data/pc.db']
        with self.assertRaises(ValueError): validate('container', self.fixture.dest, records, self.units)

    def test_other_project_missing_container_or_changed_image_is_refused(self):
        self.container_mode()
        for name in NAMES:
            for field in ['image', 'project', 'missing']:
                records = copy.deepcopy(self.records)
                if field == 'image': records[name]['Image'] = 'sha256:' + 'b' * 64
                if field == 'project': records[name]['Config']['Labels']['io.podman.compose.project'] = 'other-project'
                if field == 'missing': records.pop(name)
                with self.assertRaises(ValueError): validate('container', self.fixture.dest, records, self.units)

    def test_incomplete_or_nonprivate_snapshot_is_refused(self):
        ready = self.fixture.dest / 'ready'; ready.chmod(0o644)
        with self.assertRaises(ValueError): validate('native', self.fixture.dest, self.records)
        ready.chmod(0o600); ready.unlink(); ready.symlink_to(self.fixture.env)
        with self.assertRaises(ValueError): validate('native', self.fixture.dest, self.records)

    def test_missing_or_unsafe_ca_cannot_trigger_new_identity(self):
        key = self.fixture.dest / 'peer-caddy/caddy/pki/authorities/local/root.key'
        key.chmod(0o644)
        with self.assertRaises(ValueError): validate('native', self.fixture.dest, self.records)
        key.chmod(0o600); key.unlink()
        with self.assertRaises(FileNotFoundError): validate('native', self.fixture.dest, self.records)

    def test_manifest_pins_all_five_images_and_new_credentials(self):
        self.assertEqual(set(self.saved['services']), set(self.images))
        for name, value in self.images.items(): self.assertEqual(self.saved['services'][name]['image'], value)
        self.assertEqual(self.saved['services']['tag-server']['env_file'], [str(self.fixture.dest / 'config/peer-admin.env')])


if __name__ == '__main__': unittest.main()
