import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import activate_tag


class ActivationTests(unittest.TestCase):
    def simulate(self, engine, services, scenario):
        calls = []
        active = 'old'
        failed = False

        def run(args):
            nonlocal active, failed
            calls.append(args)
            if args[1] == 'ps':
                return args[-1].split('=')[-1]
            if args[1:3] == ['image', 'inspect']:
                return 'wrong' if scenario == 'mismatch' else 'sha256:new'
            if args[1] == 'inspect':
                if scenario == 'split-images' and args[2] == 'tag-server-readonly':
                    return 'different'
                return 'sha256:' + active
            if args[1] == 'tag' and args[-1] == 'production':
                active = 'old' if ':rollback-' in args[2] else 'new'
            if ('recreate' in args or 'smoke' in args) and not failed:
                if (scenario == 'recreate-failure' and 'recreate' in args) or (scenario == 'smoke-failure' and 'smoke' in args):
                    failed = True
                    raise subprocess.CalledProcessError(1, args)
            return ''

        with patch.object(activate_tag, 'run', side_effect=run), \
             patch.object(Path, 'read_text', return_value='COMPOSE_PROJECT_NAME="test-project"\n'), \
             contextlib.redirect_stdout(io.StringIO()):
            args = ('/repo', 'profile', '/output', engine, 'localhost/tag-server:release-test',
                    'new', 'production', 'http://example', services)
            if scenario == 'success':
                activate_tag.activate(*args)
                self.assertEqual(active, 'new')
            else:
                with self.assertRaises((RuntimeError, subprocess.CalledProcessError)):
                    activate_tag.activate(*args)
                self.assertEqual(active, 'old')
                if scenario in ('mismatch', 'split-images'):
                    self.assertFalse(any('recreate' in c or c[1] == 'tag' for c in calls))
                else:
                    recreated = [c[-1] for c in calls if 'recreate' in c]
                    self.assertEqual(recreated[-len(services):], services)

    def test_both_engines_success_mismatch_and_rollback(self):
        for engine, services in [('podman', ['tag-server', 'tag-server-readonly']), ('docker', ['tag-server'])]:
            for scenario in ('success', 'mismatch', 'recreate-failure', 'smoke-failure'):
                with self.subTest(engine=engine, scenario=scenario):
                    self.simulate(engine, services, scenario)

    def test_nuc_split_images_refused(self):
        self.simulate('podman', ['tag-server', 'tag-server-readonly'], 'split-images')
