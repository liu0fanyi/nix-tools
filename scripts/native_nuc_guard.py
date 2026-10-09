"""Pure mutual-start guard; complete inventory and statuses mandatory. No process control."""
from pathlib import Path
import json
import os
from native_pc_snapshot import private_file
from native_nuc_plan import PREFIX,REPLACE,KEEP
from native_nuc_bundle import UNITS


def validate(mode,root,records,units,*,source_images=None):
    root=Path(root)
    expected={PREFIX+name+'_1' for name in REPLACE+KEEP}
    if set(records)!=expected or set(units)!=set(UNITS):raise ValueError('Full container and unit inventory required')
    for name,item in records.items():
        if item['Name'].lstrip('/')!=name or item['Config']['Labels'].get('io.podman.compose.project')!='dufs-plus':
            raise ValueError('Container ownership mismatch')
        if not isinstance(item['State']['Running'],bool):raise ValueError('Running state must be explicit')
    if source_images is None:
        private_file(root/'backup/source-images.json');source_images=json.loads((root/'backup/source-images.json').read_text())
    if set(source_images)!=expected:raise ValueError('All pinned source images required')
    if any(item['Image'].removeprefix('sha256:')!=source_images[name].removeprefix('sha256:') for name,item in records.items()):raise ValueError('Container image changed')
    stopped={'inactive','failed','unknown'}
    if mode=='snapshot':
        if any(records[PREFIX+name+'_1']['State']['Running'] for name in REPLACE):raise ValueError('Old application writers must all stop')
        if any(value not in stopped for value in units.values()):raise ValueError('All native units must stop')
        return
    if root.is_symlink() or root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o777!=0o700:raise ValueError('Private owned snapshot root required')
    ready=root/'ready';marker=root/'container-mode'
    private_file(ready)
    if ready.is_symlink() or not ready.is_file() or ready.read_text()!='offline-double-snapshot-complete\n':
        raise ValueError('Complete double snapshot required')
    if mode=='native':
        if marker.exists() or marker.is_symlink():raise ValueError('Container mode blocks native startup')
        if any(records[PREFIX+name+'_1']['State']['Running'] for name in REPLACE):raise ValueError('Old application writer still running')
    elif mode=='container':
        private_file(marker)
        if marker.is_symlink() or not marker.is_file() or marker.read_text()!='explicit-container-fallback\n':raise ValueError('Explicit container fallback required')
        if any(value not in stopped for value in units.values()):raise ValueError('All native units must stop before fallback')
        for role,service in [('private','tag-server'),('readonly','tag-server-readonly'),('private','tag-peer-discovery')]:
            item=records[PREFIX+service+'_1']
            mounts={m['Destination']:m['Source'] for m in item['Mounts'] if m['Type']=='bind'}
            if mounts.get('/data')!=str(root/role/'state'):raise ValueError('Fallback must use new state')
            if service!='tag-peer-discovery' and '/data/core.db' not in ' '.join(item['Config']['Cmd']):raise ValueError('Fallback command must open new core.db')
    else:raise ValueError('Unknown guard mode')
