"""Offline double snapshot; never controls processes or restores a stale database."""
from contextlib import closing
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import tomllib
import uuid
from native_pc_snapshot import regular_tree,private_file
from native_pc_config import adapt_configuration,serialize_configuration
from native_nuc_runtime import adapt_environment
from native_nuc_plan import PREFIX,REPLACE,KEEP
from native_nuc_network import adapt_network


def parse_environment(text):
    """Accept literal shell assignments only; never execute/source a credentials file."""
    result={}
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        if line.startswith('export '):line=line[7:].lstrip()
        key,sep,value=line.partition('=')
        if not sep or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',key) or key in result:
            raise ValueError('Environment requires unique literal assignments')
        if ('$' in value or '`' in value) and not (value.startswith("'") and value.endswith("'")):
            raise ValueError('Environment expansion needs explicit review')
        if not value.startswith(("'",'"')) and any(c in value for c in ';|&<>'):
            raise ValueError('Environment commands are forbidden')
        words=shlex.split(line,comments=False,posix=True)
        if len(words)!=1 or not words[0].startswith(key+'='):
            raise ValueError('Environment assignment is not literal')
        result[key]=words[0].split('=',1)[1]
    return result


def environment_text(values):
    # systemd EnvironmentFile double quoting; dollar/backtick have no expansion here.
    return ''.join(key+'="'+value.replace('\\','\\\\').replace('"','\\"')+'"\n' for key,value in sorted(values.items()))


def tree_hashes(root):
    regular_tree(root)
    result={}
    for p in Path(root).rglob('*'):
        if p.is_file():
            with p.open('rb') as f:result[str(p.relative_to(root))]=hashlib.file_digest(f,'sha256').hexdigest()
    return result


def snapshot(destination,roles,*,source_config,discovery_args,environment_files,caddyfile,pki,
             whisper_package,models,source_images,ensure_offline):
    """All input roots explicit, fixed by the production caller; source files unchanged."""
    if set(source_images)!={PREFIX+name+'_1' for name in REPLACE+KEEP} or any(not re.fullmatch('[a-f0-9]{64}',v.removeprefix('sha256:')) for v in source_images.values()):
        raise ValueError('Exact nine source image IDs required')
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise ValueError('Snapshot destination must be new')
    if destination.parent.is_symlink():raise ValueError('Snapshot parent must be regular')
    if set(roles)!={'private','readonly'}:raise ValueError('Both roles must be snapshotted together')
    ensure_offline()
    for role,entry in roles.items():
        workspace=Path(entry['mounts']['/workspace'])
        served=[Path(v) for k,v in entry['mounts'].items() if k=='/workspace' or k.startswith('/workspace/')]
        if any(destination==p or p in destination.parents for p in served):raise ValueError('State must be outside all served mounts')
        regular_tree(entry['mounts']['/data'])
        database=Path(entry['mounts']['/data'])/'tag_all.db'
        if database.is_symlink() or not database.is_file():raise ValueError('Expected original tag_all.db')
    for p in [Path(source_config),Path(caddyfile)]:
        if p.is_symlink() or not p.is_file():raise ValueError('Configuration must be regular')
    for p in environment_files:private_file(p)
    pki_before=tree_hashes(pki)
    if not pki_before:raise ValueError('CA backup cannot be empty')
    original_config=Path(source_config).read_bytes();original_caddy=Path(caddyfile).read_bytes()
    values={}
    for p in environment_files:
        for key,value in parse_environment(Path(p).read_text()).items():
            if key in values and values[key]!=value:raise ValueError('Conflicting environment values')
            values[key]=value
    stage=destination.with_name(destination.name+'.pending-'+uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    try:
        backup=stage/'backup';backup.mkdir(mode=0o700)
        (backup/'source-images.json').write_text(json.dumps(source_images,sort_keys=True)+'\n')
        shutil.copytree(pki,backup/'pki')
        (backup/'Caddyfile').write_bytes(original_caddy)
        (backup/'tag-server.toml').write_bytes(original_config)
        for role,entry in roles.items():
            role_root=stage/role;role_root.mkdir(mode=0o700)
            target=role_root/'state';target.mkdir(mode=0o700)
            source=Path(entry['mounts']['/data'])
            with closing(sqlite3.connect((source/'tag_all.db').as_uri()+'?mode=ro',uri=True)) as origin:
                with closing(sqlite3.connect(target/'core.db')) as new:
                    origin.backup(new)
                    if new.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite snapshot integrity failed')
            for p in source.iterdir():
                if p.name in ['tag_all.db','tag_all.db-wal','tag_all.db-shm','instance.lock']:continue
                if p.is_dir():shutil.copytree(p,target/p.name)
                else:shutil.copyfile(p,target/p.name)
            cfgdir=role_root/'config';cfgdir.mkdir(mode=0o700)
            if role=='private':
                mounts=dict(entry['mounts']);mounts['/data']=str(destination/role/'state')
                config,layout=adapt_configuration(tomllib.loads(original_config.decode()),mounts,discovery_args)
                if layout['workspace']!=entry['mounts']['/workspace']:raise ValueError('Workspace translation changed')
                if entry.get('extra_hosts') is not None:
                    trusted=target/'metadata/paired-peers.json'
                    approved=json.loads(trusted.read_text()) if trusted.exists() else []
                    config,hosts=adapt_network(config,approved,entry['extra_hosts'],Path('/etc/hosts').read_text())
                    (cfgdir/'hosts').write_text(hosts)
                if config.get('node',{}).get('id')!='nuc':raise ValueError('Existing NUC identity must be preserved')
                if not values.get('TAG_PEER_ADMIN_TOKEN'):raise ValueError('Private admin token must be retained')
            else:
                # Legacy no-config readonly service defaults to node id nuc; keep it, with no sync/discovery/pairing.
                config={'node':{'id':'nuc'},'sync':{'enabled':False},'pairing':{'enabled':False},'discovery':{'enabled':False}}
            (cfgdir/'node.toml').write_text(serialize_configuration(config))
            role_env=values if role=='private' else {k:v for k,v in values.items() if k not in ['TAG_PEER_ADMIN_TOKEN','DUFS_WHISPER_CLI','DUFS_WHISPER_MODEL','HOME']}
            env=adapt_environment(role_env,role=role,state_root=str(destination),models=str(models),whisper_package=str(whisper_package))
            (cfgdir/'service.env').write_text(environment_text(env))
            (role_root/'git-home').mkdir(mode=0o700)
        (stage/'sockets').mkdir(mode=0o700)
        (stage/'ready').write_text('offline-double-snapshot-complete\n')
        for p in stage.rglob('*'):p.chmod(0o700 if p.is_dir() else 0o600)
        ensure_offline()
        if tree_hashes(pki)!=pki_before or Path(source_config).read_bytes()!=original_config or Path(caddyfile).read_bytes()!=original_caddy:
            raise ValueError('CA/config changed during backup; no publication')
        libc=ctypes.CDLL(None,use_errno=True)
        if not hasattr(libc,'renameat2'):raise RuntimeError('Atomic no-replace publish unavailable')
        if libc.renameat2(-100,os.fsencode(stage),-100,os.fsencode(destination),1):
            code=ctypes.get_errno();raise OSError(code,os.strerror(code))
    except BaseException:
        shutil.rmtree(stage);raise
    return {'both_sqlite_integrity':True,'original_database_overwritten':False,'ca_and_metadata_preserved':True,
        'readonly_pairing_disabled':True,'discovery_integrated_in_private_core':True,'activated':False}
