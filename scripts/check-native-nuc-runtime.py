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
import urllib.request
import urllib.error

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
        config.write_text('[node]\nid="synthetic-'+role+'-'+uuid.uuid4().hex+'"\n[discovery]\nenabled=false\n[sync]\nenabled=false\n[pairing]\nenabled='+("true" if role=="private" else "false")+'\n')
        config.chmod(0o600)
        env=state/role/'config/service.env';env.write_text('TAG_PEER_ADMIN_TOKEN='+uuid.uuid4().hex+'\n' if role=='private' else '');env.chmod(0o600)
    (root/'private/media').mkdir();(root/'media').mkdir();(root/'models').mkdir();(root/'writing-git').mkdir(mode=0o700)
    (state/'sockets').mkdir(mode=0o700)
    model=Path('/data/project/tag-all/.devenv/nuc-model-check/model.bin')
    model_hash=hashlib.sha256(model.read_bytes()).hexdigest()
    assert model_hash=='ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb'
    shutil.copyfile(model,root/'models/ggml-small-q5_1.bin');(root/'models/ggml-small-q5_1.bin').chmod(0o400)
    # Generated speech only; no recording path is accepted by this gate.
    run(['/nix/store/hqdalp6vsk179jd2ysxb33q7vyy3sisz-espeak-ng-1.52.0.1-unstable-2025-09-09/bin/espeak-ng',
         '-v','cmn','-s','130','-w',str(root/'voice.wav'),'你好，这是本地语音识别测试。今天我们测试文件上传。'])
    voice=(root/'voice.wav').read_bytes()
    legacy=Path('/nix/store/6fqry14ldg45lvxkh4y7wsfgc60zzpa4-tag-private-tested-artifacts/app/tag-server')
    legacy_hash=hashlib.sha256(legacy.read_bytes()).hexdigest()
    assert legacy_hash=='d729c3a764ca182cf2fd1aa01bf15f2f59f71a8f60df8abfdc3e833d8d66fa51'
    fallback=None
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
        for _ in range(1200):
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
        status,data=request('private','api','/pdf/render?path=book.pdf&page=1&width=120');assert status==200 and data[:2]==b'\xff\xd8',(status,data[:800])
        status,data=request('private','api','/v1/epub/page?path=book.epub&layout=mupdf_v1&spine_index=0&chapter_page=1');assert status==200 and data[:2]==b'\xff\xd8',(status,data[:800])
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
        base='http://127.0.0.1:'+str(private_port)
        def http(path, body=None, headers=None):
            req=urllib.request.Request(base+path,body,headers or {})
            with urllib.request.urlopen(req,timeout=90) as response:return response.status,json.loads(response.read())
        caps=http('/v1/capabilities')[1]['capabilities']
        assert caps['transcription_local']['ready'],caps['transcription_local']
        _,session=http('/device-sessions',json.dumps({'label':'synthetic-nuc-http','scopes':['transcriptions']}).encode(),
                       {'Content-Type':'application/json','x-dufs-device-provisioning':'1'})
        boundary=uuid.uuid4().hex
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="idempotency_key"\r\n\r\n{boundary}\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="synthetic.wav"\r\n'
              'Content-Type: application/octet-stream\r\n\r\n').encode()+voice+f'\r\n--{boundary}--\r\n'.encode()
        headers={'Content-Type':'multipart/form-data; boundary='+boundary,'Authorization':'Bearer '+session['token']}
        status,data=http('/v1/device/transcriptions',body,headers);assert status==202
        job=data['job'];deadline=time.monotonic()+240
        while True:
            job=http('/v1/device/transcriptions/'+job['id'],headers={'Authorization':headers['Authorization']})[1]['job']
            if job['status'] in ['done','failed']:break
            assert time.monotonic()<deadline,'Synthetic device transcription timed out'
            time.sleep(.5)
        assert job['status']=='done' and job['text'].strip(),job
        originals=list((state/'private/state/metadata/transcriptions/audio').glob(job['id']+'.*'))
        assert len(originals)==1 and originals[0].read_bytes()==voice
        assert hashlib.sha256(model.read_bytes()).hexdigest()==model_hash
        cases.append('authenticated device HTTP uses selected PCM worker and real Whisper/model; synthetic source preserved')
        for role in ['private','readonly']:
            status,_=request(role,'api','/tags',{'name':'new-'+role+'-rollback'},'POST');assert status==201
        run(['systemctl','--user','stop',*names.values()],timeout=300)
        for name in names.values():assert run(['systemctl','--user','is-active',name],False).stdout.strip() not in ['active','activating','deactivating']
        for role in ['private','readonly']:
            metadata=state/role/'state/metadata'
            identity={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in metadata.glob('peer-identity*')}
            assert bool(identity)==(role=='private'),'Private identity must exist; readonly must not gain pairing'
            legacy_port=port()
            with (root/('legacy-'+role+'.log')).open('wb') as log:
                fallback=subprocess.Popen([str(legacy),'--database',str(state/role/'state/core.db'),
                    '--metadata-dir',str(metadata),'--workspace',str(root/role),'--config',str(state/role/'config/node.toml'),
                    '--disable-sync','--addr','127.0.0.1:'+str(legacy_port)],stdout=log,stderr=log)
            for _ in range(150):
                assert fallback.poll() is None,'Owned legacy CLI exited'
                try:
                    with urllib.request.urlopen('http://127.0.0.1:'+str(legacy_port)+'/tags',timeout=3) as response:
                        data=response.read()
                    if ('new-'+role+'-rollback').encode() in data:break
                except OSError:pass
                time.sleep(.1)
            else:raise RuntimeError('Legacy failed to reopen new '+role+' state')
            fallback.terminate();assert fallback.wait(timeout=15)==0;fallback=None
            assert identity=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in metadata.glob('peer-identity*')}
        cases.append('fixed legacy CLI reopens BOTH new databases and retains native tags and identities after all native units stop')
    finally:
        if fallback is not None and fallback.poll() is None:fallback.terminate();fallback.wait(timeout=15)
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
    return {'candidate':str(candidate),'cases':cases,'owned_units_and_state_cleaned':True,'production_services_changed':False,'activated':False,'real_model_inference_verified':True,'device_transcription_http_verified':True,'synthetic_voice_only':True,'model_sha256':model_hash,'legacy_binary_sha256':legacy_hash,'both_new_databases_reopened':True,'container_socket_access_verified':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('candidate',type=Path);args=parser.parse_args()
    print(json.dumps(exercise(args.candidate),indent=2))
