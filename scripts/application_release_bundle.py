"""Immutable native components + real-combination evidence. No activation API."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIG_KEYS = {'schema','package','frontend','manager','file_server_package','backend_proof','frontend_proof','tag_source','dufs_source','browser_source'}
CASES = {'basic_manifest','basic_locations','unsigned_sync_rejected','anonymous_rejected','foreign_origin_rejected','served_assets','fresh','aliases_content_reload','progress_conflict','unknown_operation','shared_wasm','cleaned'}
PROTOCOLS = {'bundle':1,'api':1,'namespace':'canonical-v2','storage_receipt':'dufs-plus:workspace-namespace:v1','bridge':'fixed-shared-revision'}


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def record(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Regular explicit input required: '+str(path))
    return {'path':str(path.resolve()),'sha256':digest(path)}


def inside(path, root):
    path=Path(path).resolve(strict=True)
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Proof escaped its product specs')
    return path


def output(path):
    path=Path(path)
    if not re.fullmatch(r'/nix/store/[a-z0-9]{32}-[^/]+',str(path)) or not path.is_dir() or path.is_symlink():
        raise ValueError('Explicit immutable Nix output required')
    return path


def files(path):
    path=Path(path); found={}
    for p in sorted(path.rglob('*')):
        if p.is_symlink():raise ValueError('Symlink in frontend/component tree')
        if p.is_file():found[str(p.relative_to(path))]=digest(p)
        elif not p.is_dir():raise ValueError('Special file in component tree')
    if not found:raise ValueError('Empty component tree')
    return found


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
    return m


def backend(config):
    root=Path(config['tag_source']); proof=inside(config['backend_proof'],root/'specs');p=read(proof)
    if p.get('verification_kind')!='native-incremental-v1':
        raise ValueError('This initial lane requires the explicit 037 incremental package proof')
    if p['package']!=config['package'] or p.get('application_entry') is not True:
        raise ValueError('Backend package proof mismatch')
    evidence=inside(root/p['incremental_verification_from'],root/'specs')
    sys.path.insert(0,str(root/'scripts'))
    from release_policy import verify_incremental
    current=verify_incremental(root,read(evidence))
    sha=digest(Path(config['package'])/'libexec/tag-server-workspace')
    if sha!=p['binary_sha256'] or sha!=current['binary_sha256']:
        raise ValueError('Packaged backend differs from verified CLI')
    return {'package_proof':record(proof),'verification':record(evidence),'binary_sha256':sha}


def frontend(config):
    root=Path(config['dufs_source']);proof=inside(config['frontend_proof'],root/'specs');p=read(proof)
    if p.get('frontend')!=config['frontend'] or not p.get('source_sha256') or not p.get('built_artifacts_sha256'):
        raise ValueError('Frontend proof must bind source and selected built assets')
    for name,sha in p['source_sha256'].items():
        if digest(inside(root/name,root))!=sha:raise ValueError('Frontend source drift: '+name)
    for name,sha in p['built_artifacts_sha256'].items():
        if digest(inside(Path(config['frontend'])/name,config['frontend']))!=sha:
            raise ValueError('Frontend artifact drift: '+name)
    f=files(config['frontend'])
    if 'index.html' not in f or not any(n.endswith('.wasm') for n in f):raise ValueError('Real frontend HTML/WASM required')
    return {'proof':record(proof),'files':f,'declared_assets':p['built_artifacts_sha256']}


def shared(config):
    b=Path(config['browser_source']); d=Path(config['dufs_source'])
    guard=module('bundle_shared_guard',b/'scripts/check-shared-core.py')
    bridge=b/'rust/tag-core-bridge'
    revision=guard.consumer_revision(bridge/'Cargo.toml',bridge/'Cargo.lock')
    if revision!=guard.consumer_revision(d/'Cargo.toml',d/'Cargo.lock'):
        raise ValueError('Shared consumer revision mismatch')
    built=bridge/'target/wasm32-unknown-unknown/release/tag_browser_tag_core_bridge.wasm'
    installed=b/'assets/tag-browser-tag-core.wasm'
    if digest(built)!=digest(installed):raise ValueError('Shared bridge asset not built from selected consumer')
    return {'revision':revision,'wasm':record(installed),'inputs':[record(p) for p in [guard.__file__,bridge/'Cargo.toml',bridge/'Cargo.lock',d/'Cargo.toml',d/'Cargo.lock',b/'src/firefox/tag-browser/TagBrowserTagCore.mjs']],'bridge_sources':files(bridge/'src')}


def controls():
    return [record(ROOT/p) for p in ['scripts/application_release_bundle.py','scripts/check_application_bundle.py','scripts/application-bundle.browser.cjs','justfile']]


def create(config_file):
    config_file=Path(config_file).resolve();c=read(config_file)
    if set(c)!=CONFIG_KEYS or c['schema']!=1 or any(not isinstance(c[k],str) or not Path(c[k]).is_absolute() for k in CONFIG_KEYS-{'schema'}):
        raise ValueError('Explicit bundle-v1 configuration required')
    for k in ['package','frontend','manager','file_server_package']:output(c[k])
    result={'schema':1,'kind':'native-application-bundle-v1','config':record(config_file),'configuration':c,'protocols':PROTOCOLS,
            'backend':backend(c),'frontend':frontend(c),'shared':shared(c),'controls':controls(),
            'manager':{'launcher':record(Path(c['manager'])/'bin/tag-native-release'),'files':files(Path(c['manager'])/'libexec')},
            'file_server':record(Path(c['file_server_package'])/'bin/dufs')}
    root=Path(c['tag_source'])/'scripts'
    result['fixture_inputs']=[record(p) for p in sorted(root.glob('workspace_namespace*.py'))]+[record(Path(c['browser_source'])/'scripts/tag-browser-workspaces.py')]
    result['bundle_id']=identity(result)
    return result


def verify(bundle):
    expected=create(bundle['config']['path'])
    if expected!=bundle:raise ValueError('Bundle inputs, components or controls changed; recreate and recheck')
    return expected


def result_check(bundle, result):
    verify(bundle)
    if result.get('kind')!='native-bundle-check-v1' or result.get('bundle_id')!=bundle['bundle_id'] or result.get('controls')!=bundle['controls'] or result.get('passed') is not True or set(result.get('cases',[]))!=CASES or result.get('cleaned') is not True:
        raise ValueError('Current complete combination result required')
    if not result.get('logs'):raise ValueError('Missing runtime logs')
    if any(result.get(k) is not v for k,v in {'production_access':False,'daily_profile_used':False,'actual_rust_cli':True,'actual_frontend':True,'api_mocked':False}.items()):
        raise ValueError('Actual isolated combination evidence required')
    for item in result['logs']:
        if record(item['path'])!=item:raise ValueError('Runtime evidence log changed')


def prepare(bundle,result,scope, *, perform=False, run=subprocess.run):
    result_check(bundle,result)
    c=bundle['configuration'];args=[c['manager']+'/bin/tag-native-release','--scope',scope,'--package',c['package'],'--frontend',c['frontend']]
    if scope not in ['pc','nuc']:raise ValueError('Fixed native scope required')
    if perform:args.append('--prepare')
    return run(args,check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('create');p.add_argument('config');p.add_argument('--output',required=True)
    p=sub.add_parser('check');p.add_argument('bundle');p.add_argument('--result',required=True)
    p=sub.add_parser('prepare');p.add_argument('scope',choices=['pc','nuc']);p.add_argument('bundle');p.add_argument('--result',required=True);p.add_argument('--prepare',action='store_true')
    a=parser.parse_args()
    if a.action=='create':
        bundle=create(a.config);Path(a.output).write_text(json.dumps(bundle,indent=2)+'\n');print(bundle['bundle_id'])
    elif a.action=='check':
        from check_application_bundle import check
        check(read(a.bundle),Path(a.result))
    else:prepare(read(a.bundle),read(a.result),a.scope,perform=a.prepare)

if __name__=='__main__':main()
