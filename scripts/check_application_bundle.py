"""Actual packaged Rust + real fixed frontend; synthetic account/state only."""
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from application_release_bundle import CASES, digest, module, read, record, verify

PASSWORD='bundle-fixture-password'  # Public synthetic fixture only.
PASSWORD_HASH='$2a$14$Dl6w7usPIeiGYeLhnDonFeWNh2NC75plTVIezSgqiU.OeFAQ5qNsi'


def fixture_applications(frontend, register_learning_map=False):
    # Reserved application routes require their own configured root, including
    # when their unchanged static files are present in a private frontend bundle.
    if register_learning_map and not (Path(frontend)/'learning-map').is_dir():
        raise ValueError('Selected learning-map frontend root is missing')
    names = ('devices','transcriptions','recorder-bean') + (('learning-map',) if register_learning_map else ())
    return ''.join('[[applications]]\nname='+json.dumps(name)+'\nroot='+json.dumps(str(Path(frontend)/name))+'\n'
                   for name in names if (Path(frontend)/name).is_dir())


def check(bundle,result_path):
    verify(bundle);c=bundle['configuration'];result_path=Path(result_path).resolve()
    result_path.parent.mkdir(parents=True,exist_ok=True);result_path.unlink(missing_ok=True)
    cases=[];children=[];logs=[];failure=None;cleaned=False
    def passed(name):
        cases.append(name);print('PASS '+name,flush=True)
    def stop(p):
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
    with tempfile.TemporaryDirectory(prefix='native-bundle-') as tmp:
        root=Path(tmp);root.chmod(0o700)
        try:
            workspace=root/'workspace';runtime=root/'runtime';home=root/'home';state=root/'state';empty=root/'empty'
            for p in [workspace,runtime,home,state,empty]:p.mkdir(mode=0o700)
            for name in ['dufs','library']:(workspace/name).mkdir(mode=0o700)
            (workspace/'dufs/cards').mkdir();(workspace/'dufs/cards/a.md').write_text('# Synthetic card\n')
            (workspace/'library/book.md').write_text('# Synthetic original file\n')
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            base=f'http://127.0.0.1:{port}';auth='Basic '+base64.b64encode(('fixture:'+PASSWORD).encode()).decode()
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def request(path, *, authorized=True, origin=None):
                req=urllib.request.Request(base+path,headers={'Origin':origin or base,**({'Authorization':auth} if authorized else {})})
                try:
                    with opener.open(req,timeout=5) as response:return response.status,response.read()
                except urllib.error.HTTPError as e:return e.code,e.read()
            config=runtime/'node.toml';entry=runtime/'entry.toml';credentials=runtime/'basic.entries'
            credentials.write_text('fixture '+PASSWORD_HASH+'\n');credentials.chmod(0o600)
            def configure(path):
                config.write_text('[node]\nid="bundle-fixture"\n[[locations]]\nid="default"\nnode_id="bundle-fixture"\nname="Fixture"\npath='+json.dumps(str(path))+'\n[sync]\nenabled=true\nauto_broadcast=false\npoll_interval_secs=0\npeers=[]\nrequire_signatures=true\n[discovery]\nenabled=false\n[pairing]\nenabled=true\n');config.chmod(0o600)
            def entry_config(roots):
                entry.write_text('lan=true\nauthorities='+json.dumps([base.removeprefix('http://')])+'\nallowed_sources=["127.0.0.0/8"]\ncanonical_namespace='+('true' if roots else 'false')+'\n'+''.join('[[shared_roots]]\n'+''.join(k+'='+json.dumps(v)+'\n' for k,v in row.items()) for row in roots)+fixture_applications(c['frontend'], c.get('register_learning_map', False)));entry.chmod(0o600)
            sock=runtime/'files.sock';dufs=Path(c['file_server_package'])/'bin/dufs'
            def launch(args,name,environment=None):
                path=root/(name+'.log');logs.append(path)
                with path.open('ab') as log:p=subprocess.Popen(args,env=environment or {'HOME':str(home),'PATH':str(empty),'TAG_PEER_ADMIN_TOKEN':'synthetic-bundle-'+uuid.uuid4().hex,'RUST_LOG':'info'},stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                children.append(p);return p
            launch([str(dufs),str(workspace),'--bind',str(sock),'--allow-all'],'files')
            deadline=time.monotonic()+10
            while not sock.is_socket():
                if time.monotonic()>deadline:raise RuntimeError('Owned DUFS socket not ready')
                time.sleep(.05)
            binary=Path(c['package'])/'libexec/tag-server-workspace';db=state/'core.db'
            def start(path,name):
                p=launch([str(binary),'--workspace',str(path),'--database',str(db),'--metadata-dir',str(state/'metadata'),'--config',str(config),'--addr',base.removeprefix('http://'),'--workspace-entry-frontend',c['frontend'],'--workspace-entry-dufs-socket',str(sock),'--workspace-entry-config',str(entry),'--workspace-entry-auth-file',str(credentials)],name)
                deadline=time.monotonic()+30
                while time.monotonic()<deadline:
                    if p.poll() is not None:raise RuntimeError('Owned application exited; inspect fixture log')
                    try:
                        if request('/tag-api/tags')[0]==200:return p
                    except OSError:pass
                    time.sleep(.05)
                raise RuntimeError('Owned application not ready')
            configure(workspace/'dufs');entry_config([]);initial=start(workspace/'dufs','initial');stop(initial)
            sys.path.insert(0,str(Path(c['tag_source'])/'scripts'))
            from workspace_namespace_release import prepare,ports
            driver={'schema':1,'migration_id':'bundle-fixture','namespace_paths':{'default':str(workspace)},'retirements':{},'owner_paths':[],'identity_rebindings':[],
                'root_metadata_sources':[{'location_id':'default','path':n,'source':str(root/('.missing-'+n+'.tag'))} for n in ['dufs','library']],
                'transitions':[{'node_id':'bundle-fixture','location_id':'default','old_namespace':'legacy-v1','new_namespace':'canonical-v2','rules':[{'old_prefix':'media/library','new_root':'library'},{'old_prefix':'','new_root':'dufs'}]}],
                'endpoints':[{'origin':base,'default_location':'default'}]}
            plan={'product':prepare(db,driver)};apply,status=ports(db);apply(plan)
            if status(plan)!='applied-expected':raise ValueError('Synthetic namespace migration failed')
            helper=module('bundle_directory_fixture',Path(c['browser_source'])/'scripts/tag-browser-workspaces.py')
            roots=[helper.Directories.record(n,workspace/n,n,'fixture-'+n) for n in ['dufs','library']]
            configure(workspace);entry_config(roots);start(workspace,'canonical')
            code,raw=request('/tag-api/v1/workspace-namespace');manifest=json.loads(raw)
            if code!=200 or manifest['version']!=bundle['protocols']['namespace']:raise ValueError('Actual authenticated namespace bootstrap failed')
            passed('basic_manifest')
            if request('/tag-api/v1/locations')[0]!=200:raise ValueError('Actual authenticated locations failed')
            passed('basic_locations')
            if request('/tag-api/v1/sync/changes')[0]!=401:raise ValueError('Unsigned sync unexpectedly allowed')
            passed('unsigned_sync_rejected')
            if request('/tag-api/v1/workspace-namespace',authorized=False)[0]!=401:raise ValueError('Anonymous bootstrap unexpectedly allowed')
            passed('anonymous_rejected')
            if request('/tag-api/v1/workspace-namespace',origin='http://foreign.invalid')[0]!=403:raise ValueError('Foreign Origin unexpectedly allowed')
            passed('foreign_origin_rejected')
            for name,sha in bundle['frontend']['declared_assets'].items():
                code,raw=request('/'+('' if name=='index.html' else name))
                import hashlib
                if code!=200 or hashlib.sha256(raw).hexdigest()!=sha:raise ValueError(f'Actual served frontend mismatch: {name} status={code}')
            if request('/library/book.md')!=(200,b'# Synthetic original file\n'):raise ValueError('Canonical content request failed')
            passed('served_assets')
            fixture={'base':base,'username':'fixture','password':PASSWORD,'bundle_id':bundle['bundle_id'],'bridge':bundle['shared']['wasm']['path'],'bridge_module':str(Path(c['browser_source'])/'src/firefox/tag-browser/TagBrowserTagCore.mjs')}
            fixture_path=root/'browser.json';fixture_path.write_text(json.dumps(fixture));fixture_path.chmod(0o600)
            env={**os.environ};required=['NODE_PATH','CHROMIUM_PATH']
            if any(not env.get(k) for k in required):raise ValueError('Explicit existing Playwright and Chromium required')
            browser=launch(['node',str(Path(__file__).with_name('application-bundle.browser.cjs')),str(fixture_path)],'browser',environment=env)
            if browser.wait(timeout=120)!=0:raise RuntimeError('Owned browser gate failed; inspect browser log')
            for name in ['fresh','aliases_content_reload','progress_conflict','unknown_operation','shared_wasm']:passed(name)
        except Exception as error:failure=error
        finally:
            for p in reversed(children):stop(p)
            cleaned=all(p.poll() is not None for p in children)
            saved=[]
            for log in logs:
                if log.exists():
                    dest=result_path.with_name(result_path.stem+'-'+log.name);shutil.copyfile(log,dest);saved.append(record(dest))
    if cleaned:passed('cleaned')
    result={'kind':'native-bundle-check-v1','bundle_id':bundle['bundle_id'],'controls':bundle['controls'],'cases':cases,'logs':saved,'passed':failure is None and set(cases)==CASES,'cleaned':cleaned,'production_access':False,'daily_profile_used':False,'actual_rust_cli':True,'actual_frontend':True,'api_mocked':False}
    result_path.write_text(json.dumps(result,indent=2)+'\n')
    if failure:raise failure
    if not result['passed']:raise ValueError('Incomplete combination gate')
    verify(bundle);print(json.dumps({'bundle_id':bundle['bundle_id'],'passed':True,'cases':len(cases)}))
