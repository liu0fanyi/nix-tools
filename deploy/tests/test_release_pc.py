import contextlib
import io
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from release_pc import Release, main


class ReleaseTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('just'), 'just is not installed')
    def test_just_entrypoints_forward_target_component_and_dry_run(self):
        root = Path(__file__).resolve().parents[2]
        for target in ('nuc', 'aliyun'):
            result = subprocess.run(['just', '--', 'deploy', target, 'all', '--dry-run'],
                                    cwd=root, check=True, text=True, capture_output=True)
            profile = 'private' if target == 'nuc' else 'public'
            self.assertIn('devenv shell -- just build ' + profile, result.stdout)
        result = subprocess.run(['just', '--', 'deploy', 'nuc', 'infra', '--dry-run'],
                                cwd=root, check=True, text=True, capture_output=True)
        self.assertNotIn('just build', result.stdout)
        self.assertIn('recreate caddy', result.stdout)

    def test_old_config_component_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(['--target', 'nuc', 'config', '--dry-run'])
        self.assertEqual(caught.exception.code, 2)

    def plan(self, target, component):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('subprocess.run', side_effect=AssertionError('dry-run executed a command')):
            Release(target, True).execute(component, Path('/data/project/dufs-plus'), Path('/data/project/tag-all'))
        return output.getvalue()

    def test_nuc_config_only_remote_infrastructure(self):
        plan = self.plan('nuc', 'infra')
        self.assertIn('liou@nuc.local', plan)
        self.assertNotIn('47.93.153.102', plan)
        self.assertNotIn('podman build', plan)
        self.assertNotIn('just deploy', plan)
        self.assertLess(plan.index('backup'), plan.index('rsync'))
        self.assertIn('--exclude=secrets', plan)

    def test_nuc_applications_build_only_then_publish(self):
        plan = self.plan('nuc', 'all')
        self.assertEqual(plan.count('just build private'), 2)
        self.assertNotIn('nu redeploy.nu', plan)
        self.assertNotIn('just deploy', plan)
        self.assertIn('podman load', plan)
        self.assertIn('tag-server-readonly', plan)
        self.assertIn('frontend-backups', plan)
        self.assertNotIn('Containerfile', plan)
        self.assertNotIn('47.93.153.102', plan)

    def test_aliyun_never_deploys_to_nuc(self):
        plan = self.plan('aliyun', 'all')
        self.assertNotIn('nuc.local', plan)
        self.assertNotIn('just deploy', plan)
        self.assertNotIn('nu redeploy.nu', plan)
        self.assertIn('just build', plan)
        self.assertEqual(plan.count('just build public'), 2)
        self.assertIn('docker load', plan)
        self.assertNotIn('--delete', plan)

    def test_frontend_backup_and_bevy_protection(self):
        for target in ('nuc', 'aliyun'):
            plan = self.plan(target, 'frontend')
            self.assertLess(plan.index('frontend-backups'), plan.index('rsync'))
            self.assertIn('--exclude=/bevy-sketch/', plan)
            self.assertIn('--exclude=/bevy-game/', plan)
            self.assertIn('--exclude=/project-planner/', plan)
            self.assertNotIn('--delete', plan)
            self.assertNotIn('recreate', plan)

    def test_static_app_is_nuc_only(self):
        with self.assertRaises(ValueError):
            Release('aliyun', True).execute('frontend', Path('/frontend'), Path('/tag'), 'devices')
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('subprocess.run', side_effect=AssertionError):
            Release('nuc', True).execute('frontend', Path('/frontend'), Path('/tag'), 'devices')
        self.assertNotIn('build-dist.sh', output.getvalue())
        self.assertIn('/frontend/apps/devices/', output.getvalue())

    def test_public_runtime_image_retries_anonymous_pull_and_keeps_transfer(self):
        release = Release('aliyun')
        with patch.object(release, 'run', side_effect=[subprocess.CalledProcessError(125, 'pull'), '', '']) as run, \
             patch.object(release, 'transfer') as transfer:
            release.runtime_images()
        self.assertIn('--authfile', run.call_args_list[0].args[0])
        self.assertNotIn('--authfile', run.call_args_list[1].args[0])
        self.assertEqual(transfer.call_count, 2)

    def test_backup_failure_never_activates(self):
        release = Release('nuc')
        with patch.object(release, 'build_tag', return_value='image'), \
             patch.object(release, 'manage', side_effect=RuntimeError('backup failed')), \
             patch.object(release, 'activate_tag') as activate:
            with self.assertRaisesRegex(RuntimeError, 'backup failed'):
                release.execute('tag-server', Path('/frontend'), Path('/tag'))
            activate.assert_not_called()

    def test_architecture_mismatch_stops_build(self):
        release = Release('nuc')
        with patch.object(release, 'run', return_value='amd64') as run, \
             patch.object(release, 'remote_run', return_value='aarch64'):
            with self.assertRaisesRegex(RuntimeError, 'architectures'):
                release.build_tag(Path('/tag'))
            self.assertEqual(run.call_count, 1)

    def test_target_is_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(['all'])
        self.assertEqual(caught.exception.code, 2)

    def test_image_mismatch_is_rejected(self):
        release = Release('aliyun')
        with patch.object(release, 'run', side_effect=['aaa', '']), patch.object(release, 'remote_run', return_value='sha256:bbb'), patch.object(release, 'docker_config_digest', return_value='ccc'):
            with self.assertRaisesRegex(RuntimeError, 'image ID'):
                release.transfer('localhost/tag-server:example')

    def test_docker_manifest_id_requires_equal_exported_config(self):
        release = Release('aliyun')
        with patch.object(release, 'run', side_effect=['aaa', '']), \
             patch.object(release, 'remote_run', return_value='sha256:bbb'), \
             patch.object(release, 'docker_config_digest', return_value='aaa') as digest:
            self.assertEqual(release.transfer('image'), 'bbb')
            digest.assert_called_once_with('image')

    def test_podman_id_mismatch_never_uses_docker_fallback(self):
        release = Release('nuc')
        with patch.object(release, 'run', side_effect=['aaa', '']), \
             patch.object(release, 'remote_run', return_value='bbb'), \
             patch.object(release, 'docker_config_digest') as digest:
            with self.assertRaisesRegex(RuntimeError, 'image ID'):
                release.transfer('image')
            digest.assert_not_called()

    def test_nix_dry_run_uses_product_build_and_archive_without_commands(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('subprocess.run', side_effect=AssertionError('dry run executed')):
            self.assertEqual(main(['--target', 'nuc', 'tag-server', '--tag-packaging', 'nix', '--dry-run']), 0)
        plan = output.getvalue()
        self.assertIn('just build-nix private release-', plan)
        self.assertIn('gzip -dc', plan)
        self.assertIn('tag-peer-discovery', plan)
        self.assertNotIn('podman save', plan)
        self.assertNotIn('rsync', plan)
        self.assertNotIn('47.93.153.102', plan)
        self.assertLess(plan.index('backup'), plan.index('gzip -dc'))

    def test_nix_invalid_target_or_component_does_not_execute(self):
        for target, component in [('aliyun', 'tag-server'), ('nuc', 'infra'), ('nuc', 'frontend'), ('nuc', 'runtime-images')]:
            with contextlib.redirect_stdout(io.StringIO()), patch('subprocess.run', side_effect=AssertionError):
                self.assertEqual(main(['--target', target, component, '--tag-packaging', 'nix']), 1)

    def test_nix_artifact_binds_fresh_tag_archive_and_config(self):
        image = 'localhost/tag-server:release-test'
        config = b'{"config":{"User":"0:0"}}'
        expected = hashlib.sha256(config).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / '.devenv').mkdir()
            archive = source / 'image.tar.gz'
            with tarfile.open(archive, 'w:gz') as exported:
                for name, data in [('config.json', config), ('manifest.json', json.dumps([{'RepoTags': [image], 'Config': 'config.json'}]).encode())]:
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    exported.addfile(member, io.BytesIO(data))
            report = {'image_tag': image, 'image_output': str(archive), 'candidate_id': expected,
                      'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'full_isolated_probe': True, 'pdf_worker_probe': True, 'model_packaged': False}
            path = source / '.devenv/nix-private-report.json'
            release = Release('nuc', tag_packaging='nix')
            # Only the fixed store path is simulated; all archive bytes are real.
            with patch.object(Path, 'is_relative_to', return_value=True):
                path.write_text(json.dumps(report))
                self.assertEqual(release.read_nix_artifact(source, image)['candidate_id'], expected)
                for key, value in [('image_tag', 'old'), ('archive_sha256', '0' * 64),
                                   ('candidate_id', '1' * 64), ('full_isolated_probe', False)]:
                    path.write_text(json.dumps({**report, key: value}))
                    with self.subTest(key=key), self.assertRaises(RuntimeError):
                        release.read_nix_artifact(source, image)
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(RuntimeError, 'store artifact'):
                release.read_nix_artifact(source, image)

    def test_nix_transfer_rechecks_and_rejects_remote_digest(self):
        release = Release('nuc', tag_packaging='nix')
        artifact = {'image_tag': 'image', 'image_output': '/nix/store/fixed.tar.gz', 'candidate_id': 'a' * 64, 'source': '/tag'}
        release.tag_artifact = artifact
        with patch.object(release, 'read_nix_artifact', return_value=artifact) as verify, \
             patch.object(release, 'run') as run, patch.object(release, 'remote_run', return_value='b' * 64):
            with self.assertRaisesRegex(RuntimeError, 'config digest'):
                release.transfer('image')
            verify.assert_called_once_with(Path('/tag'), 'image')
            self.assertIn('gzip -dc /nix/store/fixed.tar.gz', run.call_args.args[0][-1])
