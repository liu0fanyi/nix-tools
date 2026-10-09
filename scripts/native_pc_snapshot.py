"""Offline copy helpers. Call only after proving all fixed source services stopped."""
import json
import ctypes
from contextlib import closing
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import tomllib
import uuid
from native_pc_config import adapt_configuration, serialize_configuration, adapt_peer_network


def regular_tree(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Expected a regular source directory')
    for path in root.rglob('*'):
        kind = path.lstat().st_mode
        if not (stat.S_ISREG(kind) or stat.S_ISDIR(kind)):
            raise ValueError('Offline snapshot refuses symlinks and special files')


def private_file(path):
    entry = Path(path).lstat()
    if not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.getuid() or stat.S_IMODE(entry.st_mode) != 0o600:
        raise ValueError('Runtime credentials must be regular owned files with mode 600')


def basic_entries(text):
    blocks = re.findall(r'\bbasic_auth\s*\{([^{}]*)\}', text)
    if len(blocks) != 1:
        raise ValueError('Expected one explicit legacy basic_auth block')
    entries = []
    for line in blocks[0].splitlines():
        line = line.split('#', 1)[0].strip()
        if not line: continue
        if not re.fullmatch(r'[A-Za-z0-9_.@-]+\s+\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}', line):
            raise ValueError('Expected literal bcrypt entries; no imports or unsupported credential syntax')
        entries.append(line)
    if not entries: raise ValueError('No Basic Auth credential entries')
    return '\n'.join(entries) + '\n'


def offline_snapshot(destination, mounts, source_config, discovery_args, source_caddy, source_environment, source_pki, source_command, source_image, ensure_offline=lambda: None, source_images=None, local_authentication="basic", extra_hosts=None):
    """No process control or activation. Publish only a complete new private directory."""
    ensure_offline()
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination must be new; never overwrite a previous snapshot')
    if destination.parent.is_symlink(): raise ValueError('Snapshot parent must not be a symlink')
    source_data = Path(mounts['/data'])
    regular_tree(source_data); regular_tree(source_pki)
    private_file(source_environment)
    for path in [Path(source_config), Path(source_caddy)]:
        if path.is_symlink() or not path.is_file(): raise ValueError('Source configuration must be regular files')
    config = tomllib.loads(Path(source_config).read_text())
    caddy_text = Path(source_caddy).read_text()
    if local_authentication == "basic":
        entries = basic_entries(caddy_text)
    elif local_authentication == "loopback":
        # Explicit preservation only: never infer anonymous from malformed auth.
        if re.search(r"\b(?:basic_auth|basicauth|import)\b", caddy_text):
            raise ValueError('Loopback migration refuses existing authentication or imported configuration')
        entries = ""
    else:
        raise ValueError('Unsupported local authentication mode')
    command = list(source_command)
    database = command[command.index('--database') + 1]
    if database != '/data/pc.db': raise ValueError('Unexpected fixed PC source database')
    database_file = source_data / 'pc.db'
    if database_file.is_symlink() or not database_file.is_file(): raise ValueError('Expected regular PC database')
    translated_mounts = dict(mounts)
    translated_mounts['/etc/tag-server/certs'] = str(destination / 'certs')
    candidate, layout = adapt_configuration(config, translated_mounts, discovery_args)
    hosts = None
    if extra_hosts is not None:
        trusted = source_data / 'metadata/paired-peers.json'
        approved = json.loads(trusted.read_text()) if trusted.exists() else []
        candidate, hosts = adapt_peer_network(candidate, approved, extra_hosts, Path('/etc/hosts').read_text())
    text = serialize_configuration(candidate)
    for workspace in [Path(layout['workspace']), *map(Path, layout['workspace_mounts'].values())]:
        if destination == workspace or workspace in destination.parents:
            raise ValueError('Private snapshot must be outside every served workspace')
    regular_tree(mounts['/etc/tag-server/certs'])
    temporary = destination.with_name(destination.name + '.pending-' + uuid.uuid4().hex)
    temporary.mkdir(mode=0o700)
    try:
        data = temporary / 'data'; data.mkdir(mode=0o700)
        with closing(sqlite3.connect(database_file.as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(data / 'core.db')) as target:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('SQLite backup integrity failed')
        for path in source_data.iterdir():
            if path.name in {'pc.db', 'pc.db-wal', 'pc.db-shm', 'instance.lock'}: continue
            if path.is_dir(): shutil.copytree(path, data / path.name)
            else: shutil.copyfile(path, data / path.name)
        shutil.copytree(source_pki, temporary / 'peer-caddy/caddy')
        shutil.copytree(mounts['/etc/tag-server/certs'], temporary / 'certs')
        runtime = temporary / 'config'; runtime.mkdir(mode=0o700)
        (runtime / 'node.toml').write_text(text)
        if hosts is not None: (runtime / 'hosts').write_text(hosts)
        (runtime / 'basic.entries').write_text(entries)
        shutil.copyfile(source_environment, runtime / 'peer-admin.env')
        # Container fallback uses NEW state and core.db, preserving native-period writes.
        command[command.index('--database') + 1] = '/data/core.db'
        rollback = {'services': {
            'tag-server': {'image': source_image, 'command': command, 'env_file': [str(destination / 'config/peer-admin.env')], 'volumes': [str(destination / 'data') + ':/data:rw', str(destination / 'certs') + ':/etc/tag-server/certs:ro']},
            'peer-discovery': {'image': source_image, 'volumes': [str(destination / 'data') + ':/data:rw']},
            'peer-gateway': {'volumes': [str(destination / 'peer-caddy') + ':/data:rw']}}}
        if source_images is not None:
            if set(source_images) != {'tag-server', 'peer-discovery', 'peer-gateway', 'caddy', 'dufs'} or any(not re.fullmatch(r'sha256:[0-9a-f]{64}', value) for value in source_images.values()):
                raise ValueError('Expected all five fixed source image digests')
            if source_images['tag-server'] != source_image:
                raise ValueError('Core source image must match the inspected snapshot source')
            for name, image in source_images.items():
                rollback['services'].setdefault(name, {})['image'] = image
        (runtime / 'container-rollback.json').write_text(json.dumps(rollback, indent=2) + '\n')
        (temporary / 'ready').write_text('offline-snapshot-complete\n')
        for path in temporary.rglob('*'):
            path.chmod(0o700 if path.is_dir() else 0o600)
        ensure_offline()
        # Linux renameat2 publishes atomically and refuses even an empty existing directory.
        libc = ctypes.CDLL(None, use_errno=True)
        if not hasattr(libc, 'renameat2'): raise RuntimeError('Atomic no-replace directory publish is unavailable')
        if libc.renameat2(-100, os.fsencode(temporary), -100, os.fsencode(destination), 1):
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return {'snapshot': str(destination), 'sqlite_integrity': True, 'source_database_overwritten': False,
            'ca_and_metadata_copied_offline': True, 'rollback_uses_new_database': True,
            'layout': layout, 'activated': False}
