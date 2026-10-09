#!/usr/bin/env python3
"""Run the complete scoped NUC ingress in its fixed Caddy container, synthetic auth only."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import socketserver
import subprocess
import sys
import tempfile
import threading
import tomllib
from http.server import BaseHTTPRequestHandler

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy/scripts'));import render
sys.path.insert(0,str(ROOT/'scripts'));from native_nuc_ingress import adapt_ingress
sys.path.insert(0,'/data/project/tag-all/scripts');from native_tool_runtime import runtime
CADDY='/nix/store/9v0131sch36inqjr4qsl7swa9385xjmq-caddy-2.11.4/bin/caddy'
IMAGE='2d8b1708bf8008935c0e2a9b6564f7f080cf9a73af3b27718f286230449b7101'

class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):daemon_threads=True


def main():
    parent=Path('/data/project/tag-all/.devenv')
    requests=[];servers=[];threads=[];cases=[]
    with tempfile.TemporaryDirectory(prefix='ni-',dir=parent) as temp:
        root=Path(temp);root.chmod(0o700)
        try:
            for role in ['private-api','readonly-api','private-files','readonly-files','auth']:
                def handler(selected):
                    class Handler(BaseHTTPRequestHandler):
                        def do_GET(self):self.respond()
                        def do_POST(self):self.respond()
                        def do_PUT(self):self.respond()
                        def respond(self):
                            requests.append((selected,self.command,self.path))
                            if selected=='auth':
                                self.send_response(204 if self.headers.get('X-Test-Allow')=='yes' else 401);self.end_headers();return
                            self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'role':selected,'path':self.path}).encode())
                        def log_message(self,*args):pass
                    return Handler
                srv=Server(str(root/(role+'.sock')),handler(role));servers.append(srv)
                thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start();threads.append(thread)
            config=tomllib.loads((ROOT/'deploy/instances/home.toml').read_text())
            password='synthetic-ingress-only'
            hashed=subprocess.run([CADDY,'hash-password','--plaintext',password,'--algorithm','bcrypt','--bcrypt-cost','4'],capture_output=True,text=True,check=True).stdout.strip()
            source=root/'Caddyfile';source.write_text(adapt_ingress(render.render_caddy(config,('fixture',hashed)))[0])
            obj=json.loads(subprocess.run([CADDY,'adapt','--config',str(source),'--adapter','caddyfile'],capture_output=True,text=True,check=True).stdout)
            # Keep the full route chains; only scope listener ports/TLS and auth upstream for this isolated HTTP gate.
            servers_config=obj['apps']['http']['servers']
            selected={}
            for server in servers_config.values():
                old=server['listen']
                if old in [[':5006'],[':5008'],[':5009']]:
                    port={':5006':18006,':5008':18008,':5009':18009}[old[0]]
                    server['listen']=['127.0.0.1:'+str(port)]
                    server.pop('tls_connection_policies',None);server['automatic_https']={'disable':True}
                    selected['port'+str(port)]=server
            obj['apps']['http']['servers']=selected
            obj['apps'].pop('tls',None)
            text=json.dumps(obj).replace('authelia:9091','unix//run/tag-native/auth.sock')
            ingress=root/'ingress.json';ingress.write_text(text);ingress.chmod(0o644)
            archive=root/'caddy.tar'
            subprocess.run(['podman','--remote','--url','unix:///run/user/1000/podman/podman.sock','save','--output',str(archive),IMAGE],check=True,capture_output=True,timeout=120)
            with runtime(root,archive,IMAGE) as connection:
                engine=['podman','--remote','--url',connection]
                name='nuc-ingress-'+root.name
                try:
                    subprocess.run(engine+['run','-d','--name',name,'--network=none','--read-only','--tmpfs','/data:rw,noexec,nosuid,size=8m','--tmpfs','/config:rw,noexec,nosuid,size=8m','--cap-drop=ALL','--cap-add=NET_BIND_SERVICE','--security-opt=no-new-privileges','--user','0:0','--mount','type=bind,src='+str(root)+',dst=/run/tag-native,ro','--entrypoint','/usr/bin/caddy',IMAGE,'run','--config','/run/tag-native/ingress.json'],check=True,capture_output=True,timeout=30)
                    basic=base64.b64encode(('fixture:'+password).encode()).decode()
                    def get(port,path,auth=True,method='GET',allow=False):
                        cmd=engine+['exec',name,'/bin/busybox','wget','-S','-O','-','--timeout=5']
                        if auth:cmd+=['--header','Authorization: Basic '+basic]
                        if allow:cmd+=['--header','X-Test-Allow: yes']
                        if port==18009:cmd+=['--header','Host: '+config['domains']['public']]
                        if method=='POST':cmd+=['--post-data','{}']
                        cmd+=['http://127.0.0.1:'+str(port)+path]
                        return subprocess.run(cmd,capture_output=True,text=True,timeout=10)
                    import time
                    for _ in range(100):
                        r=get(18006,'/tag-api/tags')
                        if r.returncode==0:break
                        time.sleep(.05)
                    else:raise RuntimeError(subprocess.run(engine+['logs',name],capture_output=True,text=True).stderr[-1500:])
                    assert json.loads(r.stdout)['role']=='private-api'
                    assert get(18006,'/tag-api/tags',auth=False).returncode!=0
                    cases.append('container readonly socket mount connects; LAN Basic auth required')
                    r=get(18008,'/tag-api/tags');assert r.returncode==0 and json.loads(r.stdout)['role']=='readonly-api'
                    assert get(18008,'/tag-api/tags',auth=False).returncode!=0
                    count=len([r for r in requests if r[0]=='readonly-api'])
                    r=get(18008,'/tag-api/tags',method='POST');assert r.returncode!=0 and '405' in r.stderr
                    assert len([r for r in requests if r[0]=='readonly-api'])==count
                    cases.append('readonly password gate and mutation 405 before upstream')
                    r=get(18009,'/tag-api/tags',auth=False);assert r.returncode!=0
                    r=get(18009,'/tag-api/tags',auth=False,allow=True)
                    assert r.returncode==0 and json.loads(r.stdout)['role']=='private-api',(r.stdout,r.stderr)
                    assert any(r[0]=='auth' for r in requests)
                    cases.append('full external origin routes deny unauthenticated and forward through auth gate')
                    # Private device/transcription ingress and terminal rules remain in the exact original adapted JSON.
                    assert '/terminal/ws' in text and 'unix//run/host-ttyd/ttyd.sock' in text
                    assert '2408:873d::/32' in text
                    cases.append('terminal and EdgeOne trusted proxy rules retained')
                finally:
                    subprocess.run(engine+['rm','-f',name],check=True,capture_output=True,timeout=30)
        finally:
            for srv in servers:srv.shutdown();srv.server_close()
            for thread in threads:thread.join(timeout=5)
    report={'caddy_image':IMAGE,'cases':cases,'container_socket_access_verified':True,
            'auth_fixture':'synthetic auth service; real Authelia production unchanged',
            'tls_handshake_verified':False,'production_services_changed':False,'owned_container_and_runtime_cleaned':True}
    (ROOT/'.devenv/native-nuc-container-ingress-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
