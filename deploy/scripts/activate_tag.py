#!/usr/bin/env python3
"""Sent over SSH by release_pc; activates either target without compiling there."""
from __future__ import annotations
from pathlib import Path
import shlex
import subprocess
import sys
import time


def run(argv):
    try:
        return subprocess.run(argv, check=True, text=True, capture_output=True).stdout.strip()
    except subprocess.CalledProcessError as error:
        print(error.stdout or '', file=sys.stderr)
        print(error.stderr or '', file=sys.stderr)
        raise


def activate(root, profile, output, engine, image, expected, production, url, services):
    project = next(shlex.split(line.partition('=')[2])[0]
                   for line in (Path(output) / 'compose.env').read_text().splitlines()
                   if line.startswith('COMPOSE_PROJECT_NAME='))
    command = ['python3', f'{root}/deploy/scripts/manage.py', '--config',
               f'{root}/deploy/instances/{profile}.toml', '--output', output]

    def container(service):
        ids = run([engine, 'ps', '-q', '--filter', f'label=com.docker.compose.project={project}',
                   '--filter', f'label=com.docker.compose.service={service}']).split()
        if len(ids) != 1:
            raise RuntimeError(f'Expected one running container for {service}, got {len(ids)}')
        return ids[0]

    def image_id(reference, image_only=False):
        args = [engine, 'image', 'inspect'] if image_only else [engine, 'inspect']
        field = '{{.Id}}' if image_only else '{{.Image}}'
        return run([*args, reference, '--format', field]).removeprefix('sha256:')

    def verify(wanted):
        for service in services:
            cid = container(service)
            if image_id(cid) != wanted:
                raise RuntimeError(f'{service} is not using the expected image')
            for attempt in range(30):
                try:
                    run([engine, 'exec', cid, 'wget', '-q', '-O', '/dev/null', 'http://127.0.0.1:8081/tags'])
                    break
                except subprocess.CalledProcessError:
                    if attempt == 29:
                        raise
                    time.sleep(2)

    expected = expected.removeprefix('sha256:')
    if image_id(image, True) != expected:
        raise RuntimeError('Loaded image does not match workstation')
    old_images = {image_id(container(service)) for service in services}
    if len(old_images) != 1:
        raise RuntimeError('Running tag services have different images; refusing activation')
    old = old_images.pop()
    rollback = image.replace(':release-', ':rollback-')
    run([engine, 'tag', old, rollback])
    print(f'Rollback image: {rollback} ({old})', flush=True)
    try:
        run([engine, 'tag', image, production])
        for service in services:
            run([*command, 'recreate', service])
        verify(expected)
        run([*command, 'smoke', '--base-url', url, '--resolve-address', '127.0.0.1', '--wait-seconds', '30'])
    except Exception:
        print('Activation failed; restoring previous image. Database backup is retained.', flush=True)
        run([engine, 'tag', rollback, production])
        for service in services:
            run([*command, 'recreate', service])
        verify(old)
        raise
    print(f'Deployed and verified {image}', flush=True)


if __name__ == '__main__':
    activate(*sys.argv[1:9], sys.argv[9:])
