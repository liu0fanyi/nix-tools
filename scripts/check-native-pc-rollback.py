#!/usr/bin/env python3
"""Read-only rollback merge rehearsal; requires PyYAML and podman-compose. Synthetic state only."""
import sys, json, subprocess, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tests'))
from test_native_pc_snapshot import OfflineSnapshot
fixture=OfflineSnapshot('test_new_private_snapshot_preserves_state_and_rollback_writes')
fixture.setUp()
try:
    fixture.prepare()
    source=Path('/data/project/tag-all/deploy/pc/compose.pc.yaml')
    base=yaml.safe_load(source.read_text())
    # Replace ONLY the credential file with synthetic input; never read production env.
    base['services']['tag-server']['env_file']=[str(fixture.env)]
    for service in base['services'].values():
        for index, volume in enumerate(service.get('volumes', [])):
            if volume.startswith('./'):
                left,right=volume.split(':',1)
                service['volumes'][index]=str(source.parent/left)+':'+right
    path=fixture.root/'base.yaml'; path.write_text(yaml.safe_dump(base))
    overlay=fixture.dest/'config/container-rollback.json'
    result=subprocess.run(['podman-compose','--podman-path','/run/current-system/sw/bin/true','-f',str(path),'-f',str(overlay),'--profile','peer-discovery','config'],text=True,capture_output=True)
    if result.returncode: raise RuntimeError('Compose parser failed; captured output withheld')
    merged=yaml.safe_load(result.stdout)
    services=merged['services']
    def volumes(name):
        return {(item.split(':')[1] if isinstance(item,str) else item['target']): (item.split(':')[0] if isinstance(item,str) else item['source']) for item in services[name]['volumes']}
    assert services['tag-server']['command'][1]=='/data/core.db'
    assert volumes('tag-server')['/data']==str(fixture.dest/'data')
    assert volumes('peer-discovery')['/data']==str(fixture.dest/'data')
    assert volumes('peer-gateway')['/data']==str(fixture.dest/'peer-caddy')
    assert volumes('tag-server')['/workspace']=='/home/liou/dufs-lan'
    assert volumes('tag-server')['/workspace/project']=='/data/project'
    assert services['tag-server']['image']==services['peer-discovery']['image']=='sha256:fixture'
    assert set(services)=={'caddy','peer-gateway','dufs','tag-server','peer-discovery'}
    for name in ['caddy','dufs']:
        assert services[name]['image']==base['services'][name]['image']
    with __import__('sqlite3').connect(fixture.dest/'data/core.db') as db:
        db.execute("INSERT INTO fixture VALUES ('new-write-before-rollback')")
    with __import__('sqlite3').connect(volumes('tag-server')['/data']+'/core.db') as db:
        assert db.execute('SELECT count(*) FROM fixture').fetchone()[0]==2
    report={'compose_parser':'podman-compose 1.6.0','actual_pc_template':str(source),'synthetic_credentials_and_state_only':True,'merged_service_count':5,'core_and_discovery_share_new_state':True,'peer_gateway_uses_copied_ca':True,'workspace_mappings_preserved':True,'native_period_write_visible_to_fallback':True,'production_credentials_read':False,'containers_started':False,'activated':False}
    print(json.dumps(report,indent=2))
finally:
    fixture.doCleanups()
