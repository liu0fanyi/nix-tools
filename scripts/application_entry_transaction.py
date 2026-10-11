"""Offline, configuration-only handover primitives; never restore a state backup."""
from contextlib import ExitStack, closing, contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tarfile
import uuid


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def private(path, directory=False):
    path = Path(path)
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600):
        raise ValueError('Owned private directory/file required')
    return path


def atomic(path, data, mode=0o600):
    path = Path(path)
    if path.is_symlink() or (path.exists() and path.stat().st_uid != os.getuid()):
        raise ValueError('Unsafe replacement destination')
    temporary = path.with_name(path.name + '.pending-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data.encode() if isinstance(data, str) else data)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if temporary.exists(): temporary.unlink()


def create_lock(path):
    path = Path(path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
    except FileExistsError:
        pass
    private(path)


@contextmanager
def exclusive(path):
    private(path)
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally: os.close(fd)


@contextmanager
def offline_states(states, ensure_stopped):
    ensure_stopped()
    with ExitStack() as stack:
        for path in states:
            private(path, True)
            stack.enter_context(exclusive(Path(path) / 'instance.lock'))
        ensure_stopped()
        yield
        ensure_stopped()


def backup_state(source, destination):
    """Called under offline_states; copy current DB including WAL via SQLite backup."""
    source = private(source, True)
    destination = Path(destination); destination.mkdir(mode=0o700)
    database = private(source / 'core.db')
    original_inode = database.stat().st_ino
    # mode=ro honors a remaining WAL. immutable=1 would incorrectly ignore it.
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as incoming:
        with closing(sqlite3.connect(destination / 'core.db')) as outgoing, outgoing:
            incoming.backup(outgoing)
            if outgoing.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Offline SQLite backup integrity failed')
    (destination / 'core.db').chmod(0o600)
    archive = destination / 'state.tar'
    with tarfile.open(archive, 'x', dereference=False) as out:
        for path in sorted(source.iterdir()):
            if path.name in {'core.db', 'core.db-wal', 'core.db-shm', 'instance.lock', 'backups'}: continue
            # Do not follow symlinks. Tar preserves references, not external contents.
            members = [path, *path.rglob('*')] if path.is_dir() and not path.is_symlink() else [path]
            if any(not (p.is_file() or p.is_dir() or p.is_symlink()) for p in members):
                raise ValueError('State backup refuses special files')
            out.add(path, arcname=path.name, recursive=True)
    archive.chmod(0o600)
    for path in [destination / 'core.db', archive]:
        with path.open('rb') as stream: os.fsync(stream.fileno())
    if database.stat().st_ino != original_inode: raise ValueError('Source database replaced during backup')
    return {'database_inode': original_inode, 'database_backup_sha256': digest(destination / 'core.db'),
            'metadata_archive_sha256': digest(archive), 'sqlite_integrity': True, 'restore_on_rollback': False}


class ConfigurationTransaction:
    """Durable journal for an exact allowlist of files and unit symlinks."""
    def __init__(self, directory, allowed):
        self.directory = Path(directory)
        self.allowed = {str(Path(p)) for p in allowed}
        self.journal = self.directory / 'journal.json'

    def create(self, replacements):
        if set(map(str, replacements)) != self.allowed: raise ValueError('Exact replacement allowlist required')
        self.directory.mkdir(mode=0o700)
        (self.directory / 'before').mkdir(mode=0o700)
        records = {}
        for index, (name, desired) in enumerate(sorted(replacements.items(), key=lambda p: str(p[0]))):
            path = Path(name)
            if desired.get('kind') not in {'file', 'symlink', 'absent'}: raise ValueError('Unknown replacement kind')
            if path.is_symlink(): before = {'kind': 'symlink', 'target': os.readlink(path)}
            elif path.exists():
                if not path.is_file() or path.stat().st_uid != os.getuid(): raise ValueError('Unexpected existing destination')
                saved = self.directory / 'before' / str(index)
                atomic(saved, path.read_bytes())
                before = {'kind': 'file', 'saved': saved.name, 'sha256': digest(saved), 'mode': stat.S_IMODE(path.stat().st_mode)}
            else: before = {'kind': 'absent'}
            records[str(path)] = {'before': before, 'after': desired}
        self.save({'phase': 'prepared', 'records': records, 'state_restore_allowed': False})

    def save(self, value): atomic(self.journal, json.dumps(value, sort_keys=True, indent=2) + '\n')
    def load(self):
        value = json.loads(private(self.journal).read_text())
        if set(value['records']) != self.allowed or value.get('state_restore_allowed') is not False:
            raise ValueError('Journal scope changed')
        return value
    def phase(self, name):
        value = self.load(); value['phase'] = name; self.save(value)
    def verify_before(self):
        value = self.load()
        for name, record in value['records'].items():
            path = Path(name); before = record['before']
            if before['kind'] == 'file':
                if path.is_symlink() or not path.is_file() or digest(path) != before['sha256'] or stat.S_IMODE(path.stat().st_mode) != before['mode']:
                    raise ValueError('Pre-backup input changed')
            elif before['kind'] == 'symlink':
                if not path.is_symlink() or os.readlink(path) != before['target']: raise ValueError('Pre-backup unit changed')
            elif before['kind'] == 'absent':
                if path.exists() or path.is_symlink(): raise ValueError('Unexpected pre-backup destination')
            else: raise ValueError('Unknown pre-backup kind')

    def verify_after(self, overrides=None):
        for name, record in self.load()['records'].items():
            path = Path(name); after = (overrides or {}).get(name, record['after'])
            if after['kind'] == 'file':
                if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) != after.get('mode', 0o600) or digest(path) != after['sha256']: raise ValueError('Installed configuration changed')
            elif after['kind'] == 'symlink':
                if not path.is_symlink() or os.readlink(path) != after['target']: raise ValueError('Installed unit changed')
            elif after['kind'] == 'absent':
                if path.exists() or path.is_symlink(): raise ValueError('Removed destination returned')
            else: raise ValueError('Unknown installed kind')

    def install(self, rollback=False):
        value = self.load()
        for name, record in value['records'].items():
            path = Path(name); desired = record['before' if rollback else 'after']
            if desired['kind'] == 'file':
                source = self.directory / 'before' / desired['saved'] if rollback else Path(desired['source'])
                if digest(source) != desired['sha256']: raise ValueError('Replacement bytes changed')
                if path.is_symlink(): raise ValueError('File destination became a symlink')
                atomic(path, source.read_bytes(), desired.get('mode', 0o600))
            elif desired['kind'] == 'symlink':
                if path.exists() and not path.is_symlink(): raise ValueError('Unit destination became a regular file')
                temporary = path.with_name(path.name + '.pending-' + uuid.uuid4().hex)
                temporary.symlink_to(desired['target']); os.replace(temporary, path)
            elif desired['kind'] == 'absent':
                if path.exists() or path.is_symlink():
                    # Delete only this exact reviewed file/symlink; never a directory.
                    if path.is_dir() and not path.is_symlink(): raise ValueError('Refusing directory removal')
                    path.unlink()
            else: raise ValueError('Unknown journal kind')
        self.phase('configuration-restored' if rollback else 'configuration-installed')
