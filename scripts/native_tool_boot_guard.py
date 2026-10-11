"""Archive only owned ephemeral tool directories after a boot epoch change."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import uuid


def owned(path, directory=False):
    info=path.lstat()
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=(0o700 if directory else 0o600):
        raise ValueError('Unsafe owned tool runtime entry')
    return path


def prepare(root, boot_id):
    root=Path(root)
    if not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id):raise ValueError('Invalid kernel boot ID')
    if not root.is_absolute() or root.resolve()!=root:raise ValueError('Canonical runtime required')
    owned(root,True)
    # Match the persistent runtime's existing lock; do not replace its inode.
    lock=root/'runtime.lock';owned(lock)
    fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if info.st_nlink!=1:raise ValueError('Unexpected hardlinked runtime lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        marker=root/'boot-epoch.json'
        previous=json.loads(owned(marker).read_text()) if marker.exists() or marker.is_symlink() else None
        if previous and previous.get('boot_id')==boot_id:return {'changed':False}
        for name in ['run','libpod','xdg']:owned(root/name,True)
        archive=root/('boot-recovery-'+uuid.uuid4().hex);archive.mkdir(mode=0o700)
        # Rename, never delete. storage/images, tasks, DB and executors are untouched.
        # Each rename is recoverable independently if interrupted before the marker.
        for name in ['run','libpod','xdg']:
            (root/name).rename(archive/name);(root/name).mkdir(mode=0o700)
        value={'boot_id':boot_id,'archive':str(archive),'storage_preserved':True}
        temporary=root/('boot-epoch.pending-'+uuid.uuid4().hex)
        with os.fdopen(os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'w') as out:
            out.write(json.dumps(value)+'\n');out.flush();os.fsync(out.fileno())
        os.replace(temporary,marker)
        return {'changed':True,'archive':str(archive),'storage_preserved':True}
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--state',required=True);args=parser.parse_args()
    if args.state!='/home/liou/.local/share/tag-all/pc-native/tools' or os.getuid()!=1000:raise ValueError('Fixed PC tools runtime only')
    result=prepare(args.state,Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    print('Tool boot guard: '+('owned ephemeral directories archived' if result['changed'] else 'same boot; unchanged'))


if __name__=='__main__':main()
