#!/usr/bin/env python3
"""Signed native peers through scoped complete NUC Caddy routes and Unix bridges."""
import importlib.util
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
PRODUCT=Path('/data/project/tag-all')
sys.path.insert(0,str(ROOT/'deploy/scripts'));import render
sys.path.insert(0,str(ROOT/'scripts'));from native_nuc_ingress import adapt_ingress
sys.path.insert(0,str(PRODUCT/'scripts'));from native_tool_runtime import runtime
CADDY='/nix/store/9v0131sch36inqjr4qsl7swa9385xjmq-caddy-2.11.4/bin/caddy'

def main():
    spec=importlib.util.spec_from_file_location('owned_peers',PRODUCT/'scripts/check-native-peers.py')
    peers=importlib.util.module_from_spec(spec);spec.loader.exec_module(peers)
    package=json.loads((PRODUCT/'.devenv/native-workspace-results.json').read_text())
    for key in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ.pop(key,None)
    processes=[]
    with tempfile.TemporaryDirectory(prefix='nuc-tls-',dir=PRODUCT/'.devenv') as temp:
        root=Path(temp);root.chmod(0o700)
        with runtime(root,Path(package['tool_archive']),package['image_id']) as connection:
            def executors(name,node):
                env={}
                for kind in ['PDF','ARCHIVE','AUDIO_VIDEO','EPUB']:
                    env.update({'TAG_NATIVE_'+kind+'_IMAGE':package['image_id'],
                        'TAG_NATIVE_'+kind+'_STATE':str(root/(name+'-'+kind)),
                        'TAG_NATIVE_'+kind+'_CONNECTION':connection})
                return env
            def proxy(name,node,certs):
                private=root/name;private.mkdir(mode=0o700)
                cfg=tomllib.loads((ROOT/'deploy/instances/home.toml').read_text())
                cfg['security']['lan_cidrs']=['127.0.0.1/32']
                hashed=subprocess.run([CADDY,'hash-password','--plaintext','synthetic-only','--bcrypt-cost','4'],capture_output=True,text=True,check=True).stdout.strip()
                source=private/'Caddyfile';source.write_text(adapt_ingress(render.render_caddy(cfg,('fixture',hashed)))[0])
                env=dict(os.environ,TAG_PEER_ADMIN_TOKEN=node['token'],XDG_CONFIG_HOME=str(private/'config'),XDG_DATA_HOME=str(private/'data'))
                obj=json.loads(subprocess.run([CADDY,'adapt','--config',str(source),'--adapter','caddyfile'],env=env,capture_output=True,text=True,check=True).stdout)
                peer_port=peers.free_port();browser_port=peers.free_port()
                servers={}
                for key,server in obj['apps']['http']['servers'].items():
                    if server['listen'] not in [[':5006'],[':5009']]:continue
                    tls=server['listen']==[':5009']
                    server['listen']=['127.0.0.1:'+str(peer_port if tls else browser_port)]
                    server['automatic_https']={'disable':True}
                    if tls:server['tls_connection_policies']=[{}]
                    else:server.pop('tls_connection_policies',None)
                    servers[key]=server
                socket=str(private/'api.sock')
                servers['owned-unix-bridge']={'listen':['unix/'+socket],
                    'routes':[{'handle':[{'handler':'reverse_proxy','upstreams':[{'dial':'127.0.0.1:'+str(node['core_port'])}]}]}],
                    'automatic_https':{'disable':True}}
                obj['apps']['http']['servers']=servers
                obj['apps']['tls']={'certificates':{'load_files':[{'certificate':str(certs/'tls.pem'),'key':str(certs/'tls.key')}]}}
                obj['apps'].pop('pki',None)
                obj['storage']={'module':'file_system','root':str(private/'storage')}
                text=json.dumps(obj).replace('unix//run/tag-native/private-api.sock','unix/'+socket)
                # Scope dead external auth only; preserve all peer exemption and routing chains.
                text=text.replace('authelia:9091','127.0.0.1:1')
                obj=json.loads(text)
                def dedup(value):
                    if isinstance(value,dict):
                        if 'host' in value and isinstance(value['host'],list):value['host']=list(dict.fromkeys(value['host']))
                        for child in value.values():dedup(child)
                    elif isinstance(value,list):
                        for child in value:dedup(child)
                dedup(obj);obj['admin']={'disabled':True};text=json.dumps(obj)
                config=private/'gateway.json';config.write_text(text);config.chmod(0o600)
                with (private/'gateway.log').open('wb') as log:
                    process=subprocess.Popen([CADDY,'run','--config',str(config)],env=env,stdout=log,stderr=log)
                processes.append(process)
                base='https://localhost:'+str(peer_port);context=ssl.create_default_context(cafile=str(certs/'ca.pem'))
                def get(path):
                    try:r=urllib.request.urlopen(base+path,context=context,timeout=3)
                    except urllib.error.HTTPError as error:r=error
                    with r:return r.status,r.read()
                code='no HTTP response'
                for _ in range(150):
                    if process.poll() is not None:raise RuntimeError('Owned NUC gateway exited: '+(private/'gateway.log').read_text()[-1200:])
                    try:
                        code,body=get('/tag-api/v1/peers/identity')
                        if code==200:assert json.loads(body)['node_id']==node['node'];break
                    except OSError:pass
                    time.sleep(.1)
                else:raise RuntimeError('Owned NUC TLS gateway not ready; last HTTP='+str(code))
                assert get('/tag-api/v1/sync/changes')[0]==401
                assert get('/tag-api/tags')[0]!=200
                return base
            try:
                output=PRODUCT/'.devenv/native-nuc-peer-results.json'
                peers.main(package_report=package,executor_environment=executors,proxy_factory=proxy,result_path=output,exercise_requests=True)
                result=json.loads(output.read_text());result.update(actual_caddy_peer_gateway_tested=True,actual_nuc_complete_gateway_routes=True,actual_unix_bridge=True,
                    production_services_changed=False,actual_authelia_login_verified=False,activated=False)
                output.write_text(json.dumps(result,indent=2)+'\n')
            finally:
                for process in processes:
                    if process.poll() is None:process.terminate();process.wait(timeout=15)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
