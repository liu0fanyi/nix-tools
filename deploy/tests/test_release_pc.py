import contextlib
import io
import shutil
import subprocess
import sys
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
