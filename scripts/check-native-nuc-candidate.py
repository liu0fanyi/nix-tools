#!/usr/bin/env python3
"""Validate an uninstalled candidate with synthetic loopback upstreams and private sockets."""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path): super().__init__('localhost', timeout=3); self.path = path
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); self.sock.settimeout(3); self.sock.connect(self.path)


def check(candidate, whisper, caddy):
    units = candidate / 'lib/systemd/user'
    names = ['tag-native-nuc.target', 'tag-nuc-bridge.service'] + ['tag-nuc-'+role+'-'+kind+'.service' for role in ['private','readonly'] for kind in ['core','tools','files']]
    assert set(names) == {p.name for p in units.iterdir()}
    for role in ['private','readonly']:
        core = (units / ('tag-nuc-'+role+'-core.service')).read_text()
        assert 'tag-all-tools.service' not in core
        assert 'tag-nuc-'+role+'-tools.service' in core
        assert '/'+role+'/state' in core and '/'+role+'/tools/runtime.sock' in core
    ro = (units/'tag-nuc-readonly-core.service').read_text()
    assert '--sync-mode isolated' in ro and 'ReadOnlyPaths=/home/liou/dufs' in ro
    assert 'writing-git' not in ro and 'DUFS_WHISPER_CLI' not in ro
    private = (units/'tag-nuc-private-core.service').read_text()
    assert '--sync-mode configured' in private and 'writing-git:' in private and 'DUFS_WHISPER_CLI=' in private
    assert '--allow-all' not in (units/'tag-nuc-readonly-files.service').read_text()
    subprocess.run([str(whisper/'bin/whisper-cli'),'--help'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=20)
    cli_hash = hashlib.sha256((whisper/'libexec/whisper-cli').read_bytes()).hexdigest()
    assert cli_hash == '3cba995f23d06abfb91fd93a34f05abd841adc0998e81aa188f1d17072b2e003'
    source = Path('/nix/store/6fqry14ldg45lvxkh4y7wsfgc60zzpa4-tag-private-tested-artifacts')
    for directory in ['lib','usr/lib']:
        for original in (source/directory).iterdir():
            copied = whisper/'lib'/original.name
            if original.is_symlink():
                import os
                assert copied.is_symlink() and os.readlink(copied)==os.readlink(original)
            else:
                assert hashlib.sha256(copied.read_bytes()).digest()==hashlib.sha256(original.read_bytes()).digest()
    configuration = json.loads((candidate/'bridge.json').read_text())
    listeners = [s['listen'] for s in configuration['apps']['http']['servers'].values()]
    assert all(len(v)==1 and v[0].startswith('unix//') for v in listeners)
    servers=[];threads=[];process=None
    with tempfile.TemporaryDirectory(prefix='nuc-bridge-') as temp:
        try:
            for role in ['private','readonly']:
                def handler(selected):
                    class Handler(BaseHTTPRequestHandler):
                        def do_GET(self):
                            self.send_response(200); self.end_headers(); self.wfile.write(selected.encode())
                        def log_message(self,*args): pass
                    return Handler
                srv = ThreadingHTTPServer(('127.0.0.1',0),handler(role)); servers.append(srv)
                thread = threading.Thread(target=srv.serve_forever,daemon=True);thread.start();threads.append(thread)
                item=next(s for s in configuration['apps']['http']['servers'].values() if role+'-api.sock' in s['listen'][0])
                item['listen']=['unix/'+temp+'/'+role+'.sock']
                item['routes'][0]['handle'][0]['upstreams'][0]['dial']='127.0.0.1:'+str(srv.server_port)
            config=Path(temp)/'bridge.json';config.write_text(json.dumps(configuration))
            with (Path(temp)/'caddy.log').open('w') as log:
                process=subprocess.Popen([str(caddy),'run','--config',str(config)],stdout=log,stderr=log)
                for _ in range(100):
                    if all((Path(temp)/(role+'.sock')).exists() for role in ['private','readonly']): break
                    if process.poll() is not None: raise AssertionError('Bridge exited: '+(Path(temp)/'caddy.log').read_text())
                    time.sleep(.03)
                for role in ['private','readonly']:
                    client=UnixHTTP(temp+'/'+role+'.sock')
                    try:
                        client.request('GET','/synthetic-identity'); response=client.getresponse()
                        assert response.status==200 and response.read().decode()==role
                    finally:client.close()
        finally:
            if process is not None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            for srv in servers: srv.shutdown();srv.server_close()
            for thread in threads:thread.join(timeout=5)
    return {'candidate':str(candidate),'whisper_package':str(whisper),'whisper_cli_sha256':cli_hash,
            'checks':['eight unit files and instance dependencies','separate DB/tool states',
                      'readonly OS protection and disabled sync','private-only Git/Whisper selection',
                      'exact Whisper CLI, musl libraries and real help','Unix-only bridge listeners','real private and readonly Unix HTTP routing'],
            'production_services_changed':False,'real_model_inference_verified':False,
            'container_socket_access_verified':False,'activated':False,'cutover_ready':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['candidate','whisper','caddy']:parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(check(args.candidate,args.whisper,args.caddy),ensure_ascii=False,indent=2))
