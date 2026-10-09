#!/usr/bin/env python3
"""Run scoped copies of NUC candidate units against owned synthetic data only."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import importlib.util
_spec=importlib.util.spec_from_file_location("nuc_candidate",ROOT/"scripts/check-native-nuc-candidate.py")
_module=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_module)
UnixHTTP=_module.UnixHTTP


def run(args,check=True,timeout=300):
    r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if check and r.returncode:raise RuntimeError(r.stderr[-1800:])
    return r


def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


def exercise(candidate):
    parent=Path('/data/project/tag-all/.devenv');parent.mkdir(exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='nu-',dir=parent));root.chmod(0o700)
    state=root/'state';state.mkdir(mode=0o700)
    for role in ['private','readonly']:
        work=root/role;work.mkdir(mode=0o700);(work/'proof.md').write_text(role+' original\n')
        for rel in [role,role+'/state',role+'/config',role+'/git-home']:(state/rel).mkdir(mode=0o700)
        config=state/role/'config/node.toml'
        config.write_text('[node]\nid="synthetic-'+role+'-'+uuid.uuid4().hex+'"\n[discovery]\nenabled=false\n[sync]\nenabled=false\n')
        config.chmod(0o600)
        env=state/role/'config/service.env';env.write_text('');env.chmod(0o600)
    (root/'private/media').mkdir();(root/'media').mkdir();(root/'models').mkdir();(root/'writing-git').mkdir(mode=0o700)
    (state/'sockets').mkdir(mode=0o700)
    private_port,readonly_port=port(),port();assert private_port!=readonly_port
    mapping={'/home/liou/.local/share/tag-all/nuc-native':str(state),'/home/liou/.local/share/whisper.cpp/models':str(root/'models'),
             '/home/liou/.config/dufs-plus/secrets/writing-git':str(root/'writing-git'),
             '/home/liou/dufs-lan':str(root/'private'),'/home/liou/dufs':str(root/'readonly'),'/media/liou':str(root/'media'),
             '127.0.0.1:18181':'127.0.0.1:'+str(private_port),'127.0.0.1:18182':'127.0.0.1:'+str(readonly_port)}
    sys.path.insert(0,'/data/project/tag-all/scripts')
    from synthetic_pdf import synthetic_pdf
    from synthetic_epub import synthetic_epub
    import zipfile
    (root/'private/book.pdf').write_bytes(synthetic_pdf())
    (root/'private/book.epub').write_bytes(synthetic_epub())
    with zipfile.ZipFile(root/'private/extract.zip','w') as z:z.writestr('proof.md','synthetic extracted')
    prefix='nuc-gate-'+uuid.uuid4().hex[:10]+'-'
    originals=list((candidate/'lib/systemd/user').iterdir());names={p.name:prefix+p.name for p in originals}
    def scoped(text):
        text=re.sub('|'.join(re.escape(k) for k in sorted(mapping,key=len,reverse=True)),lambda m:mapping[m.group()],text)
        for old,new in names.items():text=text.replace(old,new)
        return text
    owned=root/'units';owned.mkdir();links=[];cases=[]
    try:
        for original in originals:
            text=scoped(original.read_text())
            # Scope immutable generated path guards/config, preserving all checks and directives.
            for store_path in set(re.findall(r'/nix/store/[A-Za-z0-9._+-]+',text)):
                p=Path(store_path)
                if p.is_file() and (p.name.endswith(".Caddyfile") or p.read_bytes().startswith(b"#!")):
                    content=p.read_text()
                    changed=scoped(content)
                    if changed!=content:
                        replacement=root/p.name;replacement.write_text(changed);replacement.chmod(0o700 if os.access(p,os.X_OK) else 0o600)
                        text=text.replace(store_path,str(replacement))
            text=re.sub(r'^WantedBy=.*$', '',text,flags=re.M)
            target=owned/names[original.name];target.write_text(text)
            link=Path('/run/user/'+str(os.getuid())+'/systemd/user')/target.name
            assert not link.exists() and not link.is_symlink()
            link.symlink_to(target);links.append((link,target))
        run(['systemctl','--user','daemon-reload'])
        run(['systemctl','--user','start',names['tag-native-nuc.target']],timeout=300)
        for _ in range(250):
            if all((state/'sockets'/(role+'-api.sock')).is_socket() for role in ['private','readonly']):
                try:
                    for role in ['private','readonly']:
                        c=UnixHTTP(str(state/'sockets'/(role+'-api.sock')));c.request('GET','/tags');r=c.getresponse();assert r.status==200;r.read();c.close()
                    break
                except (OSError,AssertionError):pass
            time.sleep(.1)
        else:
            logs=run(['journalctl','--user',*[x for n in names.values() for x in ['-u',n]],'-n','60','--no-pager'],False).stdout
            raise RuntimeError('Owned candidate did not become ready:\n'+logs[-6500:])
        for name in names.values():assert run(['systemctl','--user','is-active',name],False).stdout.strip()=='active',name
        cases.append('actual generated eight-unit target starts and both APIs respond')
        def request(role,kind,path,payload=None,method='GET'):
            c=UnixHTTP(str(state/'sockets'/(role+'-'+kind+'.sock')))
            c.connect();c.sock.settimeout(90)
            try:
                body=json.dumps(payload) if payload is not None else None
                c.request(method,path,body,{'Content-Type':'application/json'} if body else {})
                response=c.getresponse();return response.status,response.read()
            finally:c.close()
        for role in ['private','readonly']:
            status,data=request(role,'files','/proof.md');assert status==200 and data.decode()==role+' original\n'
        status,_=request('private','files','/made.md',method='PUT');assert status in [200,201]
        status,_=request('readonly','files','/made.md',method='PUT');assert status>=400 and not (root/'readonly/made.md').exists()
        cases.append('actual private DUFS writes; readonly DUFS rejects PUT and source remains')
        status,_=request('private','api','/tags',{'name':'nuc-runtime-persist'},'POST');assert status==201
        assert b'nuc-runtime-persist' not in request('readonly','api','/tags')[1]
        cases.append('private tags remain isolated from readonly DB')
        status,data=request('private','api','/v1/pdf/info?path=book.pdf');assert status==200 and json.loads(data)['total_pages']==1
        status,data=request('private','api','/pdf/render?path=book.pdf&page=1&width=120');assert status==200 and data[:2]==b'\xff\xd8'
        status,data=request('private','api','/v1/epub/page?path=book.epub&layout=mupdf_v1&spine_index=0&chapter_page=1');assert status==200 and data[:2]==b'\xff\xd8'
        status,data=request('private','api','/items/extract',{'path':'extract.zip'},'POST');assert status==200,(status,data)
        assert (root/'private/extract/proof.md').read_text()=='synthetic extracted'
        cases.append('actual selected PDF EPUB and archive worker processing')
        original=(root/'readonly/proof.md').read_bytes()
        status,data=request('readonly','api','/items/text/read',{'path':'proof.md','location_id':'default'},'POST');assert status==200,(status,data)
        revision=json.loads(data)['revision']
        status,_=request('readonly','api','/items/text/write',{'path':'proof.md','location_id':'default','text':'unsafe','expected_revision':revision},'POST')
        assert status>=400 and (root/'readonly/proof.md').read_bytes()==original
        cases.append('direct readonly API file write blocked by real OS namespace')
        run(['systemctl','--user','restart',names['tag-native-nuc.target']],timeout=300)
        for _ in range(150):
            try:
                status,data=request('private','api','/tags')
                if status==200 and b'nuc-runtime-persist' in data:break
            except OSError:pass
            time.sleep(.1)
        else:raise RuntimeError('Restart lost private state')
        cases.append('whole target restart preserves private new writes')
    finally:
        run(['systemctl','--user','stop',*names.values()],False)
        for name in names.values():assert run(['systemctl','--user','is-active',name],False).stdout.strip() not in ['active','activating','deactivating']
        run(['systemctl','--user','reset-failed',*names.values()],False)
        for link,target in links:
            assert link.is_symlink() and link.resolve()==target.resolve();link.unlink()
        run(['systemctl','--user','daemon-reload'])
        for role in ['private','readonly']:
            runtime=state/role/'tools'
            if (runtime/'storage').exists():
                engine=['podman','--remote=false','--root',str(runtime/'storage'),'--runroot',str(runtime/'run'),'--storage-driver=vfs','--tmpdir',str(runtime/'libpod')]
                ids=run(engine+['ps','-aq']).stdout.split()
                if ids:
                    records=json.loads(run(engine+['inspect',*ids]).stdout)
                    for item in records:
                        assert item['Image'].removeprefix('sha256:')=='12e714e09fafe1a4fba378f35eed1c68138691c129ccb52ac6ac239416ee82c4'
                        assert item['Name'].lstrip('/').startswith(('tag-pdf-','tag-epub-','tag-archive-','tag-audio-video-'))
                        assert all(Path(m['Source']).is_relative_to(root) for m in item.get('Mounts',[]) if m.get('Type')=='bind')
                    run(engine+['rm','-f',*ids])
                assert not run(engine+['ps','-aq']).stdout.strip()
                run(engine+['unshare',sys.executable,'-c','import pathlib,shutil,sys;p=pathlib.Path(sys.argv[1]);assert p.parent==pathlib.Path(sys.argv[2]) and p.name=="tools" and not p.is_symlink();shutil.rmtree(p)',str(runtime),str(runtime.parent)])
        shutil.rmtree(root)
    return {'candidate':str(candidate),'cases':cases,'owned_units_and_state_cleaned':True,'production_services_changed':False,'activated':False,'real_model_inference_verified':False,'container_socket_access_verified':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('candidate',type=Path);args=parser.parse_args()
    print(json.dumps(exercise(args.candidate),indent=2))
