"""Bind transfer to the exact N3-tested package, units and tool archive. No activation."""
import hashlib
import json
from pathlib import Path
import re

PRODUCT=Path('/data/project/tag-all')
FEATURE=PRODUCT/'specs/025-native-nuc-rollout'
UNITS=tuple('tag-nuc-'+role+'-'+kind+'.service' for role in ['private','readonly'] for kind in ['core','tools','files'])+('tag-nuc-bridge.service','tag-native-nuc.target')

def digest(path):
    with Path(path).open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()

def build_manifest(candidate_report,runtime_report,peer_report,package_report):
    candidate=Path(candidate_report['candidate'])
    package=Path(package_report['package']);whisper=Path(candidate_report['whisper_package'])
    for path in [candidate,package,whisper,Path(package_report['tool_archive'])]:
        if not re.fullmatch(r'/nix/store/[a-z0-9]{32}-[A-Za-z0-9._+-]+',str(path)) or not path.exists():
            raise ValueError('Expected an existing immutable store artifact')
    if runtime_report['candidate']!=str(candidate) or not runtime_report.get('owned_units_and_state_cleaned'):
        raise ValueError('Runtime evidence must match the exact candidate')
    for key in ['device_transcription_http_verified','both_new_databases_reopened','real_model_inference_verified']:
        if runtime_report.get(key) is not True:raise ValueError('Missing runtime gate: '+key)
    if peer_report['package']!=str(package):raise ValueError('Peer package evidence differs')
    for key in ['signed_sync_and_tag_persistence','actual_tls_private_ca','actual_nuc_complete_gateway_routes','owned_cleanup']:
        if peer_report.get(key) is not True:raise ValueError('Missing peer gate: '+key)
    binary=digest(package/'libexec/tag-server-workspace')
    if binary!=package_report['binary_sha256'] or binary!=peer_report['binary_sha256']:
        raise ValueError('Tested native binary changed')
    archive=digest(package_report['tool_archive'])
    if archive!=package_report['archive_sha256']:raise ValueError('Tool archive changed')
    cli=digest(whisper/'libexec/whisper-cli')
    if cli!=candidate_report['whisper_cli_sha256']:raise ValueError('Whisper changed')
    units=candidate/'lib/systemd/user'
    if set(p.name for p in units.iterdir())!=set(UNITS):raise ValueError('Candidate unit set changed')
    # Preserve fixed state, role isolation and processing launch selections.
    for role in ['private','readonly']:
        text=(units/('tag-nuc-'+role+'-core.service')).read_text()
        if str(package) not in text or '/home/liou/.local/share/tag-all/nuc-native/'+role+'/state' not in text:
            raise ValueError('Unit package/state differs from the tested topology')
    return {'schema_version':1,'target':'nuc','candidate':str(candidate),'package':str(package),
        'whisper_package':str(whisper),'tool_archive':package_report['tool_archive'],
        'binary_sha256':binary,'archive_sha256':archive,'tool_image':package_report['image_id'],
        'whisper_cli_sha256':cli,'units':{name:digest(units/name) for name in UNITS},
        'bridge_sha256':digest(candidate/'bridge.Caddyfile'),'activated':False,
        'models_or_credentials_in_bundle':False}

def load_manifest():
    read=lambda path:json.loads(path.read_text())
    manifest=build_manifest(read(FEATURE/'candidate-results.json'),read(FEATURE/'runtime-results.json'),
        read(FEATURE/'peer-results.json'),read(PRODUCT/'.devenv/native-workspace-results.json'))
    manifest['source_images']={p['name']:p['image'].removeprefix('sha256:') for p in read(FEATURE/'topology-results.json')['containers']}
    return manifest


def normalize_closure(result):
    entries=[dict(value,path=key) for key,value in result.items()] if isinstance(result,dict) else result
    return {p['path']:{'narHash':p['narHash'],'narSize':p['narSize']} for p in entries}
