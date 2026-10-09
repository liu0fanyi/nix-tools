#!/usr/bin/env python3
"""PC entry points: NUC infrastructure, or Aliyun public application stack."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shlex
import subprocess
import tarfile
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    'nuc': ('liou@nuc.local', '/media/liou/project/me/nix-tools', 'home', '/home/liou/.local/share/dufs-plus/runtime/home', 'podman'),
    'aliyun': ('root@47.93.153.102', '/root/nix-tools', 'aliyun', '/root/nix-tools/deploy/.generated/aliyun', 'docker'),
}


class Release:
    def __init__(self, target: str, dry_run: bool = False, tag_packaging: str = 'alpine'):
        if tag_packaging not in ('alpine', 'nix') or (tag_packaging == 'nix' and target != 'nuc'):
            raise ValueError('Nix packaging is only supported for private NUC tag-server')
        self.tag_packaging = tag_packaging
        self.tag_artifact = None
        self.target = target
        self.remote, self.root, self.profile, self.output, self.engine = TARGETS[target]
        self.dry_run = dry_run
        self.build_profile = 'private' if target == 'nuc' else 'public'
        self.config = tomllib.loads((ROOT / f'deploy/instances/{self.profile}.toml').read_text())

    def run(self, argv, cwd=None, capture=False, input=None):
        argv = [str(a) for a in argv]
        print('+ ' + (f'(cd {cwd}) ' if cwd else '') + shlex.join(argv), flush=True)
        if self.dry_run:
            return 'dry-run'
        result = subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=capture, input=input)
        return result.stdout.strip() if capture else ''

    def remote_run(self, argv, capture=False):
        return self.run(['ssh', self.remote, shlex.join([str(a) for a in argv])], capture=capture)

    def manage(self, *args):
        self.remote_run(['python3', f'{self.root}/deploy/scripts/manage.py', '--config',
                         f'{self.root}/deploy/instances/{self.profile}.toml', '--output', self.output, *args])

    def sync_config(self):
        self.run(['rsync', '-az', '--exclude=secrets', '--exclude=.generated', '--exclude=__pycache__',
                  str(ROOT / 'deploy') + '/', f'{self.remote}:{self.root}/deploy/'])

    def apply_config(self):
        self.manage('up', '--confirm')
        self.manage('recreate', 'caddy')

    def podman(self):
        url = os.environ.get('TAG_PODMAN_URL')
        return ['podman', '--remote', '--url', url] if url else ['podman']

    def transfer(self, image):
        if self.tag_artifact and self.tag_artifact['image_tag'] == image:
            return self.transfer_nix(image)
        local_id = self.run([*self.podman(), 'image', 'inspect', image, '--format', '{{.Id}}'], capture=True)
        command = (f'{shlex.join(self.podman())} save {shlex.quote(image)} | zstd -T0 -3 -c | ssh {shlex.quote(self.remote)} '
                   + shlex.quote(f'bash -o pipefail -c {shlex.quote("zstd -d | " + self.engine + " load")}'))
        self.run(['bash', '-o', 'pipefail', '-c', command])
        remote_id = self.remote_run([self.engine, 'image', 'inspect', image, '--format', '{{.Id}}'], capture=True)
        local_id = local_id.removeprefix('sha256:')
        remote_id = remote_id.removeprefix('sha256:')
        if local_id != remote_id:
            # Docker 29's containerd store reports a manifest ID, whereas Podman
            # reports the config digest. Verify the actual exported config bytes
            # (which bind the layer diff IDs), not a tag or version string.
            if self.engine != 'docker' or self.docker_config_digest(image) != local_id:
                raise RuntimeError('Transferred image ID/config digest differs from workstation image')
            print('Verified Docker config digest; runtime manifest ID is ' + remote_id)
        return remote_id

    def read_nix_artifact(self, source, image):
        report = json.loads((source / '.devenv/nix-private-report.json').read_text())
        archive = Path(report['image_output'])
        expected = report['candidate_id'].removeprefix('sha256:')
        if report.get('image_tag') != image or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise RuntimeError('Nix report does not identify this release')
        if not archive.is_file() or not archive.resolve().is_relative_to('/nix/store'):
            raise RuntimeError('Nix archive must be a fixed store artifact')
        with archive.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != report['archive_sha256']:
            raise RuntimeError('Nix archive checksum differs from verified report')
        with tarfile.open(archive) as exported:
            manifest = json.load(exported.extractfile('manifest.json'))
            if len(manifest) != 1 or manifest[0].get('RepoTags') != [image]:
                raise RuntimeError('Nix archive does not contain this release tag')
            config = exported.extractfile(manifest[0]['Config']).read()
            if hashlib.sha256(config).hexdigest() != expected:
                raise RuntimeError('Nix archive config digest differs from verified report')
        if not report.get('full_isolated_probe') or not report.get('pdf_worker_probe') or report.get('model_packaged') is not False:
            raise RuntimeError('Nix report lacks complete private verification')
        return report

    def transfer_nix(self, image):
        artifact = self.tag_artifact
        if not self.dry_run:
            # Recheck immediately before sending; do not import into or migrate PC storage.
            artifact = self.read_nix_artifact(Path(artifact['source']), image)
        archive = artifact['image_output']
        expected = artifact['candidate_id'].removeprefix('sha256:')
        command = (f'gzip -dc {shlex.quote(archive)} | zstd -T0 -3 -c | ssh {shlex.quote(self.remote)} '
                   + shlex.quote(f'bash -o pipefail -c {shlex.quote("zstd -d | podman load")}'))
        self.run(['bash', '-o', 'pipefail', '-c', command])
        remote_id = self.remote_run(['podman', 'image', 'inspect', image, '--format', '{{.Id}}'], capture=True).removeprefix('sha256:')
        if not self.dry_run and remote_id != expected:
            raise RuntimeError('Transferred Nix image config digest differs from verified archive')
        return remote_id

    def docker_config_digest(self, image):
        code = '''import hashlib,json,sys,tarfile
digests={}
manifest=None
with tarfile.open(fileobj=sys.stdin.buffer,mode="r|*") as archive:
    for member in archive:
        if member.isfile() and member.size <= 1048576:
            data=archive.extractfile(member).read()
            digests[member.name]=hashlib.sha256(data).hexdigest()
            if member.name == "manifest.json":
                manifest=json.loads(data)
assert manifest is not None and len(manifest)==1, "Expected one exported image"
print(digests[manifest[0]["Config"]])
'''
        command = f'docker save {shlex.quote(image)} | python3 -c {shlex.quote(code)}'
        return self.remote_run(['bash', '-o', 'pipefail', '-c', command], capture=True)

    def runtime_images(self):
        names = ('caddy', 'dufs') if self.target == 'aliyun' else ('caddy', 'dufs', 'readonly_gateway', 'authelia', 'ddns_go')
        for name in names:
            image = self.config['images'][name]
            try:
                self.run([*self.podman(), 'pull', '--authfile', ROOT / 'deploy/public-registry-auth.json', image])
            except subprocess.CalledProcessError:
                # These are public runtime images. An expired Docker Hub login
                # must not block an anonymous pull; transfer still checks IDs.
                print(f'Authenticated pull failed for {image}; retrying anonymously', flush=True)
                self.run([*self.podman(), 'pull', image])
            self.transfer(image)

    def build_frontend(self, source):
        # Build only. Product deploy recipes target NUC and must not be called here.
        self.run(['devenv', 'shell', '--', 'just', 'build', self.build_profile], cwd=source)

    def frontend(self, source, app=None):
        dist = source / 'apps' / app if app else source / 'dist'
        destination = self.config['paths']['dist'] + (f'/{app}' if app else '')
        if not self.dry_run and not (dist / 'index.html').is_file():
            raise RuntimeError('Frontend index.html missing')
        self.backup_frontend()
        self.remote_run(['mkdir', '-p', destination])
        dest = f'{self.remote}:{destination}/'
        # Preserve unowned app directories and old hashed assets for open clients.
        filters = ['--exclude=/bevy-sketch/', '--exclude=/bevy-game/', '--exclude=/project-planner/']
        self.run(['rsync', '-az', '--delay-updates', *filters, '--exclude=index.html', str(dist) + '/', dest])
        self.run(['rsync', '-az', '--delay-updates', *filters, '--include=*/', '--include=index.html', '--exclude=*', str(dist) + '/', dest])
        difference = self.run(['rsync', '-rcn', '--out-format=%i %n', *filters, str(dist) + '/', dest], capture=True)
        if not self.dry_run and difference:
            raise RuntimeError('Published frontend differs from local artifacts: ' + difference)
        if not self.dry_run and self.target == 'aliyun':
            expected = hashlib.sha256((dist / 'index.html').read_bytes()).hexdigest()
            host = self.config['domains']['aliases'][0] if self.config['domains']['aliases'] else self.config['domains']['public']
            request = urllib.request.Request(f'https://{host}/index.html?release={expected}', headers={'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(request, timeout=30) as response:
                actual = hashlib.sha256(response.read()).hexdigest()
            if actual != expected:
                raise RuntimeError('Public CDN index differs from local build')

    def backup_frontend(self):
        # Keep a recoverable static snapshot, separate from business-data backup.
        directory = self.config['paths']['dist']
        script = ('set -eu; test -d "$1"; mkdir -p "$HOME/.local/state/dufs-plus/frontend-backups"; '
                  'backup=$(mktemp "$HOME/.local/state/dufs-plus/frontend-backups/frontend-XXXXXXXX.tar"); '
                  'tar --exclude=./bevy-sketch --exclude=./bevy-game --exclude=./project-planner '
                  '-C "$1" -cf "$backup" .; echo "Frontend backup: $backup"')
        self.remote_run(['bash', '-c', script, 'frontend-backup', directory])

    def build_tag(self, source):
        image = 'localhost/tag-server:release-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        local_arch = self.run([*self.podman(), 'info', '--format', '{{.Host.Arch}}'], capture=True)
        remote_arch = self.remote_run(['uname', '-m'], capture=True)
        aliases = {'x86_64': 'amd64', 'aarch64': 'arm64'}
        if aliases.get(local_arch, local_arch) != aliases.get(remote_arch, remote_arch):
            raise RuntimeError('Workstation and target architectures differ')
        if self.tag_packaging == 'nix':
            self.run(['devenv', 'shell', '--', 'just', 'build-nix', 'private', image.split(':', 1)[1]], cwd=source)
            if self.dry_run:
                print('Verify fresh Nix report, archive SHA256, release tag and config digest before backup/transfer', flush=True)
                self.tag_artifact = {'image_tag': image, 'image_output': '<verified Nix store archive>',
                                     'candidate_id': 'dry-run', 'source': str(source)}
            else:
                self.tag_artifact = {**self.read_nix_artifact(source, image), 'source': str(source)}
        else:
            self.run(['devenv', 'shell', '--', 'just', 'build', self.build_profile, image], cwd=source)
        return image

    def activate_tag(self, image):
        expected = self.transfer(image)
        services = ['tag-server'] + (['tag-server-readonly'] if self.config['features']['readonly'] else [])
        if self.config['features'].get('tag_peer_discovery', False):
            services.append('tag-peer-discovery')
        argv = ['python3', '-', self.root, self.profile, self.output, self.engine,
                image, expected, self.config['images']['tag_server'], self.smoke_url(), *services]
        self.run(['ssh', self.remote, shlex.join(argv)],
                 input=(ROOT / 'deploy/scripts/activate_tag.py').read_text())

    def smoke_url(self):
        return 'https://nas.wttliou.top:5009' if self.target == 'nuc' else 'http://wttliou.top'

    def smoke(self):
        url = self.smoke_url()
        self.manage('smoke', '--base-url', url, '--resolve-address', '127.0.0.1', '--wait-seconds', '30')

    def execute(self, component, frontend, tag, app=None):
        if self.tag_packaging == 'nix' and component not in ('tag-server', 'all'):
            raise ValueError('--tag-packaging nix requires tag-server or all')
        if app and (self.target != 'nuc' or component != 'frontend'):
            raise ValueError('--frontend-app is only supported for nuc frontend')
        if self.target == 'nuc' and component in {'infra','tag-server','all'}:
            self.remote_run(['python3','-c',
                'from pathlib import Path; p=Path("/home/liou/.local/share/dufs-plus/runtime/home/native-nuc-control"); '
                'assert not (p.exists() or p.is_symlink()), "Native NUC is managed by the native cutover controller; legacy activation refused"'])
        if component == 'runtime-images':
            self.runtime_images()
            return
        if component in ('all', 'frontend') and not app:
            self.build_frontend(frontend)
        image = self.build_tag(tag) if component in ('all', 'tag-server') else None
        # Back up using installed control plane before replacing configuration.
        if component != 'frontend':
            self.manage('backup', '--keep-last', '0')
        if component in ('all', 'infra'):
            self.sync_config()
            self.runtime_images()
            self.manage('preflight')
        if image:
            self.activate_tag(image)
        if component in ('all', 'infra'):
            self.apply_config()
        if component in ('all', 'frontend'):
            self.frontend(frontend, app)
        self.smoke()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, choices=TARGETS)
    parser.add_argument('component', nargs='?', choices=('all', 'infra', 'frontend', 'tag-server', 'runtime-images'))
    parser.add_argument('--dry-run', action='store_true', help='Print commands without building, connecting or publishing')
    parser.add_argument('--frontend-source', type=Path, default=Path('/data/project/dufs-plus'))
    parser.add_argument('--tag-source', type=Path, default=Path('/data/project/tag-all'))
    parser.add_argument('--frontend-app', choices=('devices', 'transcriptions', 'recorder-bean'))
    parser.add_argument('--tag-packaging', choices=('alpine', 'nix'), default='alpine')
    args = parser.parse_args(argv)
    component = args.component or 'infra'
    try:
        Release(args.target, args.dry_run, args.tag_packaging).execute(component, args.frontend_source, args.tag_source, args.frontend_app)
    except (OSError, ValueError, KeyError, tarfile.TarError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Release failed: {error}')
        return 1
    return 0
