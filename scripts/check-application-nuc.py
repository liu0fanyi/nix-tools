#!/usr/bin/env python3
"""Build and verify the opt-in NUC candidate; never reads/activates live state."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import application_nuc_ingress as entry
ROOT=Path(__file__).resolve().parents[1]
TAG=Path(sys.argv[1]).resolve()
DUFS=Path(sys.argv[2]).resolve()
WHISPER=sys.argv[3]
OUT=TAG/'.devenv'
CADDY='/nix/store/z7n5vmb63i55f9xzish6fhyxlmwy6mrf-caddy-2.11.4/bin/caddy'
proof=json.loads((OUT/'application-entry-package-results.json').read_text())
for name,sha in proof['source_manifest'].items():
    assert hashlib.sha256((TAG/name).read_bytes()).hexdigest()==sha,name
binary=Path(proof['package'])/'libexec/tag-server-workspace'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof['binary_sha256']

def transport_runtime(adapted, temporary, env):
    """Exercise the actual proxy handlers; auth/socket backends are explicit stubs."""
    import base64, copy, http.client, http.server, socket, socketserver, threading, time
    class Backend(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if self.server.role=='auth':
                valid=self.path.startswith('/authelia/') and 'api/authz/' not in self.path
                valid=valid or self.headers.get('Cookie')=='synthetic-session'
                self.send_response(200 if valid else 401)
                if valid:
                    self.send_header('Remote-User','verified-user')
                    self.send_header('Remote-Groups','admins')
                self.send_header('Content-Length','0');self.end_headers();return
            body=json.dumps({'role':self.server.role,'headers':dict(self.headers),'path':self.path}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    servers=[];process=None;threads=[];cases=[]
    class UnixServer(socketserver.ThreadingMixIn,socketserver.UnixStreamServer): daemon_threads=True
    try:
        for role in ['private-web','private-peer','readonly-web','auth']:
            server=(http.server.ThreadingHTTPServer(('127.0.0.1',0),Backend) if role=='auth' else UnixServer(str(temporary/(role+'.sock')),Backend))
            server.role=role;servers.append(server)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();threads.append(thread)
        config=copy.deepcopy(adapted)
        config.pop('admin',None);config['admin']={'disabled':True}
        config['apps'].pop('tls',None)
        routes=copy.deepcopy(next(server for server in config['apps']['http']['servers'].values() if ':5009' in server['listen']))
        for server in config['apps']['http']['servers'].values():
            if ':5443' in server['listen'] and ':5009' not in server['listen']:
                routes['routes'].extend(copy.deepcopy(server['routes']))
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
        routes['listen']=['127.0.0.1:'+str(port)]
        routes.pop('tls_connection_policies',None);routes['automatic_https']={'disable':True}
        config['apps']['http']['servers']={'synthetic':routes}
        text=json.dumps(config).replace('authelia:9091','127.0.0.1:'+str(servers[-1].server_address[1]))
        for role in ['private-web','private-peer','readonly-web']:
            text=text.replace('unix//run/tag-native/'+role+'.sock','unix/'+str(temporary/(role+'.sock')))
        runtime=temporary/'runtime.json';runtime.write_text(text);runtime.chmod(0o600)
        log=(temporary/'runtime.log').open('w')
        process=subprocess.Popen([CADDY,'run','--config',str(runtime)],env=env,stdout=log,stderr=log)
        def request(path='/',host='nuc.local:5009',headers=None):
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            try:
                conn.request('GET',path,headers={'Host':host,**(headers or {})});response=conn.getresponse();body=response.read()
                return response.status,json.loads(body) if response.status==200 and body else {}
            finally: conn.close()
        for attempt in range(100):
            try: request();break
            except (ConnectionError,OSError):
                if process.poll() is not None: raise RuntimeError((temporary/'runtime.log').read_text())
                time.sleep(.05)
        else: raise RuntimeError('Owned proxy did not become ready')
        forged={name:'forged' for name in entry.UNTRUSTED}
        status,_=request(headers=forged)
        assert status in (401,302,303),status
        cases.append('actual_proxy_forged_identity_without_session_rejected')
        status,body=request('/note.md',headers={**forged,'Cookie':'synthetic-session','Authorization':'Basic forged'})
        assert status==200 and body['role']=='private-web'
        headers={k.lower():v for k,v in body['headers'].items()}
        assert headers['remote-user']=='verified-user' and headers['remote-groups']=='admins'
        assert 'authorization' not in headers
        for name in entry.UNTRUSTED:
            if not name.startswith('Remote-'): assert name.lower() not in headers
        cases.append('actual_proxy_only_verified_authelia_identity_reaches_web_socket')
        for path in ['/device-api/v1/music','/tag-api/v1/peers/identity']:
            status,body=request(path,headers={**forged,'Authorization':'Bearer synthetic-device'})
            assert status==200 and body['role']=='private-peer'
            headers={k.lower():v for k,v in body['headers'].items()}
            assert headers['authorization']=='Bearer synthetic-device'
            assert all(name.lower() not in headers for name in entry.UNTRUSTED)
            assert body['path']==path
        cases.append('actual_proxy_peer_and_device_headers_stripped_bearer_and_api_prefix_retained')
        status,body=request('/note.md',host='work.wttliou.top:5443',headers=forged)
        assert status==401,(status,body)
        basic='Basic '+base64.b64encode(b'synthetic:synthetic-only').decode()
        status,body=request('/note.md',host='work.wttliou.top:5443',headers={**forged,'Authorization':basic})
        assert status==200 and body['role']=='readonly-web'
        headers={k.lower():v for k,v in body['headers'].items()}
        assert headers.get('remote-user')=='synthetic',headers
        assert headers.get('remote-groups','')==''
        assert 'authorization' not in headers
        assert all(name.lower() not in headers for name in entry.UNTRUSTED if not name.startswith('Remote-'))
        cases.append('actual_proxy_readonly_basic_required_identity_not_forgeable')
        status,_=request('/authelia/',headers=forged)
        assert status==200,status
        cases.append('actual_proxy_login_portal_remains_accessible')
        # A spoofed forwarding header cannot satisfy the original remote_ip guard.
        process.terminate();process.wait(timeout=10)
        def deny_source(value):
            if isinstance(value,dict):
                if 'remote_ip' in value: value['remote_ip']['ranges']=['192.0.2.0/24']
                for child in value.values(): deny_source(child)
            elif isinstance(value,list):
                for child in value: deny_source(child)
        restricted=json.loads(text);deny_source(restricted)
        runtime.write_text(json.dumps(restricted))
        process=subprocess.Popen([CADDY,'run','--config',str(runtime)],env=env,stdout=log,stderr=log)
        for attempt in range(100):
            try:
                status,_=request('/tag-api/v1/peers/identity',headers={**forged,'X-Forwarded-For':'192.0.2.1'})
                break
            except (ConnectionError,OSError): time.sleep(.05)
        else: raise RuntimeError('Owned restricted proxy did not become ready')
        assert status==404,status
        cases.append('actual_proxy_nonlan_peer_denied_despite_forged_forwarded_source')
        return cases
    finally:
        if process is not None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill();process.wait(timeout=5)
            log.close()
        for server in servers: server.shutdown();server.server_close()
        for thread in threads: thread.join(timeout=3)

cases=[]
def run(args,name):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
    if result.returncode:
        print((result.stdout+result.stderr)[-6000:]);raise SystemExit(result.returncode)
    return result.stdout
run([sys.executable,'-m','unittest','discover','-s','deploy/tests','-p','test_*nuc_ingress.py'],'application-entry-nuc-ingress-tests')
cases.append('application_candidate_and_legacy_ingress_negative_tests')
for application,name in [(True,'application-entry-nuc-candidate'),(False,'application-entry-nuc-legacy')]:
    run(['nix-build',str(ROOT/'tests/native-nuc-candidate.nix'),'--argstr','tagAll',str(TAG),'--argstr','dufsPlus',str(DUFS),'--argstr','whisperPackage',WHISPER,'--arg','applicationEntry',str(application).lower(),'--out-link',str(OUT/name)],name+'-build')
candidate=(OUT/'application-entry-nuc-candidate').resolve()
legacy=(OUT/'application-entry-nuc-legacy').resolve()
units=candidate/'lib/systemd/user'
assert len(list(units.iterdir()))==7
assert len(list((legacy/'lib/systemd/user').iterdir()))==8
assert not (units/'tag-nuc-bridge.service').exists()
assert not (candidate/'bridge.Caddyfile').exists()
for role,workspace,port in [('private','/home/liou/dufs-lan',5006),('readonly','/home/liou/dufs',18182)]:
    core=(units/f'tag-nuc-{role}-core.service').read_text()
    files=(units/f'tag-nuc-{role}-files.service').read_text()
    tools=(units/f'tag-nuc-{role}-tools.service').read_text()
    config=tomllib.loads((candidate/f'{role}-entry.toml').read_text())
    assert f"--addr '[::]:{port}'" in core
    assert proof['package']+'/bin/tag-all-core' in core
    assert f'Requires=tag-nuc-{role}-files.service' in core
    assert f'BindsTo=tag-nuc-{role}-tools.service' in core
    assert 'bridge.service' not in core
    assert 'tag-all-tools.service' not in core
    assert '--allow-archive' in files and '--allow-symlink' in files
    assert 'UMask=0077' in files and 'stat -c' in Path(files.split('ExecStartPre=',1)[1].splitlines()[0]).read_text()
    assert '--workspace-entry-auth-file' in core
    assert config['lan'] is True
    assert f'nuc.local:{5006 if role=="private" else 5008}' in config['authorities']
    assert config['external_socket'].endswith(f'/{role}-web.sock')
    assert '127.0.0.0/8' in config['allowed_sources'] and '::1/128' in config['allowed_sources']
    assert '$2a$' not in core+tools+str(config)
    if role=='private':
        assert '--workspace-entry-read-only false' in core and '--allow-all' in files
        assert '--sync-mode configured' in core
        assert config['peer_write_delegation'] and config['peer_devices'] and config['peer_on_lan']
        assert 'nas.wttliou.top' in config['peer_authorities']
        assert 'https://nas.wttliou.top' in config['external_origins']
        assert config['external_admin_groups']==['admins']
        assert 'DUFS_WHISPER_CLI=' in core and 'git-home/.ssh' in core
        assert config['terminal_socket']=='/run/user/1000/ttyd/ttyd.sock'
        expected=['devices','transcriptions','recorder-bean','bevy-game','bevy-sketch','project-planner','quick-note']
        assert [app['name'] for app in config['applications']]==expected
        for app in config['applications']:
            assert f'{workspace}/dist/{app["name"]}:{app["root"]}' in core
            assert not Path(app['root']).is_relative_to(workspace)
    else:
        assert '--workspace-entry-read-only true' in core and '--allow-all' not in files
        assert '--sync-mode isolated' in core
        assert f'ReadOnlyPaths={workspace}' in files and f'ReadOnlyPaths={workspace}' in core
        assert not config['peer_on_lan'] and config['device_profile']=='disabled'
        assert not config['external_admin_groups']
        assert 'https://work.wttliou.top:5008' in config['external_origins']
        for name in ['applications','peer_socket','terminal_socket']: assert name not in config
        assert 'DUFS_WHISPER' not in core and 'git-home' not in core
        assert config['allowed_sources']==['10.89.50.0/24','127.0.0.0/8','::1/128']
cases.append('generated_dual_instances_auth_readonly_dependencies_apps_and_secrets_isolation')
systemd = Path(subprocess.check_output(['readlink','-f','/run/current-system/sw/bin/systemd-analyze'],text=True).strip())
unit_defaults = systemd.parent.parent/'example/systemd/user'
assert (unit_defaults/'basic.target').is_file()
run(['env','SYSTEMD_UNIT_PATH='+str(units)+':'+str(unit_defaults),str(systemd),'--user','verify',*[str(p) for p in units.iterdir()]],'application-entry-nuc-unit-verify')
cases.append('generated_seven_user_units_systemd_verify_no_activation')
config=tomllib.loads((ROOT/'deploy/instances/home.toml').read_text())
original=entry.render.render_caddy(config,('synthetic','$2a$14$synthetic-test-only'))
ingress,contract=entry.candidate_ingress(original,config)
profile=entry.candidate_profile((ROOT/'deploy/compose.home-ipv6-cdn.yaml').read_text())
transport=entry.candidate_readonly_transport((ROOT/'deploy/haproxy.readonly.cfg').read_text())
# Never load production credentials or use the default Caddy autosave/CA directory.
with tempfile.TemporaryDirectory(prefix='e3c-caddy-',dir=OUT) as name:
    temp=Path(name);temp.chmod(0o700)
    auth=temp/'basic.entries';auth.write_text('synthetic '+subprocess.check_output([CADDY,'hash-password','--algorithm','bcrypt','--plaintext','synthetic-only'],text=True).strip()+'\n');auth.chmod(0o600)
    env={**os.environ,'XDG_CONFIG_HOME':str(temp/'config'),'XDG_DATA_HOME':str(temp/'data')}
    caddy=temp/'Caddyfile';caddy.write_text(ingress.replace('/run/secrets/caddy_lan_basic_auth',str(auth)))
    result=subprocess.run([CADDY,'adapt','--config',str(caddy),'--adapter','caddyfile'],env=env,capture_output=True,text=True)
    (OUT/'application-entry-nuc-caddy-adapt.log').write_text(result.stderr)
    assert result.returncode==0,result.stderr
    adapted=json.loads(result.stdout)
    text=json.dumps(adapted)
    servers=adapted['apps']['http']['servers']
    listens={port for server in servers.values() for port in server['listen']}
    assert ':5006' not in listens and ':5008' not in listens
    assert ':5009' in listens and ':5443' in listens
    for socket in ['private-web','private-peer','readonly-web']: assert 'unix//run/tag-native/'+socket+'.sock' in text
    assert 'authelia:9091' in text and 'trusted_proxies' in text
    assert '{http.auth.user.id}' in text
    assert 'tag-server:8081' not in text and 'dufs:5000' not in text
    # Compare global source policy and all unowned server routes, not merely presence.
    old=temp/'old.Caddyfile';old.write_text(original)
    previous=json.loads(subprocess.check_output([CADDY,'adapt','--config',str(old),'--adapter','caddyfile'],env=env,stderr=subprocess.DEVNULL,text=True))
    assert adapted.get('admin')==previous.get('admin')
    assert adapted['apps']['tls']==previous['apps']['tls']
    for server in servers.values():
        if not set(server['listen']) & {':5009',':5443'}:
            assert server in previous['apps']['http']['servers'].values()
        else:
            oldserver=next(s for s in previous['apps']['http']['servers'].values() if s['listen']==server['listen'])
            for key in ['trusted_proxies','client_ip_headers','trusted_proxies_strict','tls_connection_policies']:
                assert server.get(key)==oldserver.get(key),key
    cases.extend(transport_runtime(adapted,temp,env))
    # Store no adapted JSON containing a credential, even a synthetic hash.
(OUT/'application-entry-nuc.Caddyfile').write_text(ingress)
(OUT/'application-entry-nuc-profile.yaml').write_text(profile)
(OUT/'application-entry-nuc-haproxy.cfg').write_text(transport)
cases.append('actual_caddy_adaptation_preserves_tls_authelia_source_policy_and_unowned_servers')
cases.append('dual_protocol_5008_transport_preserved_no_lan_port_collision')
owned=['packages/native-nuc-candidate.nix','tests/native-nuc-candidate.nix','scripts/application_nuc_ingress.py','scripts/check-application-nuc.py','deploy/tests/test_application_nuc_ingress.py']
report={'stage':'E3.c','candidate':str(candidate),'legacy_candidate':str(legacy),'package':proof['package'],'binary_sha256':proof['binary_sha256'],'tester_image_id':proof['tester_image_id'],'full_tester_reused_from':proof['full_tester_reused_from'],'cases':cases,'contract':contract,'source_manifest':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in owned},'runtime_backend_scope':'Actual Caddy handlers; synthetic authentication and fixed Unix backends, HTTP transport only. Final real Authelia/TLS/Tagall combination is E4.','host_lock_sha256':hashlib.sha256((ROOT/'flake.lock').read_bytes()).hexdigest(),'dual_stack':json.loads((OUT/'application-entry-dual-stack-results.json').read_text())['cases'],'activated':False,'production_database_access':False,'limitations':['E3.d must prepare runtime-only configuration, application bind targets and exact merged Compose inputs.','E4 must verify actual Authelia/TLS/HAProxy routing, OPTIONS compatibility, OS readonly namespaces, terminal and independent applications using the final installed combination.','No production service has been changed; no production secret, database, CA or frontend was read or copied.']}
(OUT/'application-entry-nuc-results.json').write_text(json.dumps(report,indent=2)+'\n')
print('E3.c generated candidate gates passed; no production activation',flush=True)
