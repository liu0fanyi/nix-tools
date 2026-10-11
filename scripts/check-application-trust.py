#!/usr/bin/env python3
"""E4.a real TLS/Authelia/TOTP/HAProxy against frozen application, synthetic state only."""
from contextlib import ExitStack
import uuid
import base64,copy,hashlib,hmac,http.client,json,os,re,shutil,socket,ssl,struct,subprocess,sys,tempfile,time,tomllib
from pathlib import Path
from application_nuc_ingress import candidate_ingress,candidate_readonly_transport,UNTRUSTED,render
# A transient owned user unit sees real subordinate UID/GID maps; never migrate default Podman.
if '--owned-unit' not in sys.argv:
 unit='tag-entry-trust-'+uuid.uuid4().hex
 subprocess.run(['systemd-run','--user','--wait','--pipe','--collect','--unit='+unit,'--property=UMask=0077','--setenv=PATH=/run/wrappers/bin:'+os.environ.get('PATH',''),sys.executable,__file__,*sys.argv[1:],'--owned-unit'],check=True)
 sys.exit(0)
ROOT=Path(__file__).resolve().parents[1]
arguments=[arg for arg in sys.argv[1:] if arg!='--owned-unit'];TAG=Path(arguments[0]).resolve()
TOOLS=Path(arguments[1]).resolve() if len(arguments)>1 else Path(subprocess.check_output(['nix-build',str(ROOT/'tests/application-trust-tools.nix'),'--argstr','tagAll',str(TAG),'--out-link',str(TAG/'.devenv/entry-trust-tools')],text=True).strip());AUTHELIA=str(TOOLS/'bin/authelia');HAPROXY=str(TOOLS/'bin/haproxy')
CADDY='/nix/store/z7n5vmb63i55f9xzish6fhyxlmwy6mrf-caddy-2.11.4/bin/caddy'
DUFS='/nix/store/ph17xq80q9by2vmivfvm97a1729q4cgl-dufs-0.46.0/bin/dufs'
sys.path.insert(0,'/nix/store/iw39pw567acajnaf1iywnwz6fwcb6cxg-python3.14-pyyaml-6.0.3/lib/python3.14/site-packages');import yaml
proof=json.loads((TAG/'specs/027-application-entry-boundary/entry-update-results.json').read_text())
for n,h in proof['source_manifest'].items():
 if n!='scripts/application_nuc_ingress.py':assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
# Candidate ingress changed only here for E4.a OPTIONS; final source/output digest is recorded below.
candidate=Path(proof['nuc']['candidate']);package=Path(proof['application_packages']['nuc']['path'])
binary=package/'libexec/tag-server-workspace'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof['application_packages']['nuc']['binary_sha256']
sys.path.insert(0,str(TAG/'scripts'));from native_tool_runtime import runtime as isolated_runtime
stack=ExitStack();gateway_engine=None;gateway_name=None
root=Path(tempfile.mkdtemp(prefix='et-',dir='/tmp'));root.chmod(0o700);processes=[];cases=[];owned_sockets=[];apps={}
def run(args):
 r=subprocess.run(args,capture_output=True,text=True,timeout=90)
 if r.returncode:raise RuntimeError('Owned fixture command failed: '+r.stderr[-1500:])
 return r.stdout
ports=set()
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));v=s.getsockname()[1]
 assert v not in ports;ports.add(v);return v

def spawn(args,name):
 with (root/(name+'.log')).open('w') as log:
  p=subprocess.Popen(args,stdout=log,stderr=log,env={**os.environ,'TAG_PEER_ADMIN_TOKEN':'owned-test-only-'+os.urandom(24).hex(),'XDG_CONFIG_HOME':str(root/'xdg-config'),'XDG_DATA_HOME':str(root/'xdg-data')},start_new_session=True)
 processes.append(p);return p

def wait(fn,p):
 for _ in range(300):
  if p.poll() is not None:raise RuntimeError('Owned fixture exited '+str(p.returncode))
  try:
   if fn():return
  except (OSError,ValueError):pass
  time.sleep(.05)
 raise RuntimeError('Owned fixture did not become ready')

context=None;cookies={}
def request(port,path='/',host='nas.wttliou.top',tls=False,method='GET',data=None,headers=None,session=False,trust=None):
 conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5);conn.connect()
 if tls:conn.sock=(trust or context).wrap_socket(conn.sock,server_hostname=host.split(':')[0])
 hdr={'Host':host,**(headers or {})}
 if data is not None:hdr['Content-Type']='application/json';data=json.dumps(data)
 if session and cookies:hdr['Cookie']='; '.join(k+'='+v for k,v in cookies.items())
 try:
  conn.request(method,path,data,headers=hdr);r=conn.getresponse();body=r.read();reply=dict(r.getheaders())
  for n,v in r.getheaders():
   if n.lower()=='set-cookie' and session:
    key,value=v.split(';',1)[0].split('=',1);cookies[key]=value
  return r.status,body,reply
 finally:conn.close()

def private_write(path,text):path.write_text(text);path.chmod(0o600)
try:
 config=tomllib.loads((ROOT/'deploy/instances/home.toml').read_text())
 private_port,readonly_port,tls_port,readonly_tls_port,dual_port,auth_port=[port() for _ in range(6)]
 pw='synthetic-entry-password'
 hashed=run([CADDY,'hash-password','--algorithm','bcrypt','--bcrypt-cost','4','--plaintext',pw]).strip()
 (root/'credentials').mkdir(mode=0o700)
 basic=root/'credentials/basic.entries';private_write(basic,'synthetic '+hashed+'\n')
 auth_header={'Authorization':'Basic '+base64.b64encode(('synthetic:'+pw).encode()).decode()}
 forged={n:'forged' for n in UNTRUSTED}
 for role,p in [('private',private_port),('readonly',readonly_port)]:
  (root/role).mkdir(mode=0o700)
  for n in ['workspace','state','sockets','apps','config']:(root/role/n).mkdir(parents=True,mode=0o700)
  (root/role/'workspace/note.md').write_text(role+' original')
  node=root/role/'config/node.toml';private_write(node,'[node]\nid="trust-'+role+'"\n[discovery]\nenabled=false\n[sync]\nenabled=true\nauto_broadcast=false\npoll_interval_secs=0\n[pairing]\nenabled='+('true' if role=='private' else 'false')+'\n')
  entry=(candidate/(role+'-entry.toml')).read_text().replace('/home/liou/.local/share/tag-all/nuc-native/sockets',str(root/role/'sockets')).replace('/home/liou/.local/share/tag-all/nuc-native/'+role+'/apps',str(root/role/'apps')).replace('/run/user/1000/ttyd/ttyd.sock',str(root/role/'sockets/ttyd.sock'))
  for app in tomllib.loads(entry).get('applications',[]):Path(app['root']).mkdir(mode=0o700)
  if role=='private':
   terminal=socket.socket(socket.AF_UNIX);terminal.bind(str(root/role/'sockets/ttyd.sock'));terminal.listen();owned_sockets.append(terminal)
  ef=root/role/'config/entry.toml';private_write(ef,entry)
  fs=root/role/'sockets/files.sock'
  fp=spawn([DUFS,str(root/role/'workspace'),'--bind',str(fs),*(['--allow-all'] if role=='private' else ['--allow-search','--allow-archive'])],role+'-files');wait(fs.exists,fp)
  frontend=re.search(r'--workspace-entry-frontend (\S+)',(candidate/'lib/systemd/user'/('tag-nuc-'+role+'-core.service')).read_text()).group(1)
  cmd=[str(binary),'--workspace',str(root/role/'workspace'),'--database',str(root/role/'state/core.db'),'--metadata-dir',str(root/role/'state/metadata'),'--config',str(node),'--addr','127.0.0.1:'+str(p),'--workspace-entry-frontend',frontend,'--workspace-entry-dufs-socket',str(fs),'--workspace-entry-config',str(ef),'--workspace-entry-auth-file',str(basic)]
  if role=='readonly':cmd+=['--workspace-entry-read-only','--disable-sync']
  ap=spawn(cmd,role+'-app');apps[role]=(ap,cmd,ef)
  wait(lambda:(root/role/'sockets'/(role+'-web.sock')).exists(),ap)
  wait(lambda:request(p,'/note.md',host='nuc.local:'+str(5006 if role=='private' else 5008),headers=auth_header)[0]>0,ap)
  ready=request(p,'/note.md',host='nuc.local:'+str(5006 if role=='private' else 5008),headers=auth_header)
  assert ready[0]==200,(role,ready)
  assert request(p,'/note.md',host='nuc.local:'+str(5006 if role=='private' else 5008),headers=forged)[0]==401
  assert request(p,'/tag-api/tags',host='untrusted.invalid',headers=auth_header)[0]==403
 cases.append('real_application_lan_basic_and_host_forgery_denial')
 authelia_image=proof['retained_images']['authelia'].removeprefix('sha256:')
 info=json.loads(run(['podman','--remote','--url','unix:///run/user/1000/podman/podman.sock','image','inspect',authelia_image]))[0]
 assert info['Id'].removeprefix('sha256:')==authelia_image
 authelia_version=info['Config']['Labels']['org.opencontainers.image.version']
 assert 'v'+authelia_version+'-nixpkgs' in run([AUTHELIA,'--version'])
 del info
 # Use the actual rendered Authelia policy and two-factor requirement, with owned users/secrets/state only.
 authelia=yaml.safe_load(render.render_authelia(config))
 assert authelia['access_control']['default_policy']=='two_factor'
 authelia['server']['address']='tcp://127.0.0.1:'+str(auth_port)+'/authelia'
 authelia['authentication_backend']['file']['path']=str(root/'users.yml')
 authelia['session']['secret']='s'*64
 authelia['storage']['encryption_key']='e'*64
 authelia['storage']['local']['path']=str(root/'auth.db')
 authelia['notifier']['filesystem']['filename']=str(root/'notification.txt')
 authelia['identity_validation']={'reset_password':{'jwt_secret':'j'*64}}
 users={'users':{'synthetic':{'displayname':'Synthetic Administrator','password':hashed,'email':'synthetic@example.invalid','groups':['admins']},'reader':{'displayname':'Synthetic Reader','password':hashed,'email':'reader@example.invalid','groups':['users']}}}
 private_write(root/'users.yml',yaml.safe_dump(users));acf=root/'authelia.yml';private_write(acf,yaml.safe_dump(authelia))
 auth=spawn([AUTHELIA,'--config',str(acf)],'authelia');wait(lambda:request(auth_port,'/authelia/api/health',host='nas.wttliou.top')[0]==200,auth)
 secret=base64.b32encode(b'synthetic-owned-totp-secret-bytes').decode().rstrip('=')
 for user in users['users']:run([AUTHELIA,'storage','user','totp','generate',user,'--secret',secret,'--config',str(acf)])
 original=render.render_caddy(config,('synthetic',hashed));ingress,_=candidate_ingress(original,config)
 cf=root/'Caddyfile';private_write(cf,ingress.replace('/run/secrets/caddy_lan_basic_auth',str(basic)))
 adapted=json.loads(run([CADDY,'adapt','--config',str(cf),'--adapter','caddyfile']))
 # Preserve complete owned routes/TLS/issuers/source handling; remap only listeners and private fixture upstreams.
 servers={}
 for name,server in adapted['apps']['http']['servers'].items():
  if ':5009' in server['listen'] or ':5443' in server['listen']:
   assert len(server['listen'])==1
   server['listen']=['127.0.0.1:'+str(tls_port if ':5009' in server['listen'] else readonly_tls_port)]
   server['automatic_https']={'disable_redirects':True};servers[name]=server
 adapted['apps']['http']['servers']=servers;adapted['admin']={'disabled':True}
 for policy in adapted['apps']['tls']['automation']['policies']:
  policy['issuers']=[{'module':'internal'}] # Isolated owned CA, no ACME or production certificate store.
 text=json.dumps(adapted).replace('authelia:9091','127.0.0.1:'+str(auth_port))
 for role in ['private-web','private-peer','readonly-web']:
  folder='readonly' if role.startswith('readonly') else 'private'
  text=text.replace('unix//run/tag-native/'+role+'.sock','unix/'+str(root/folder/'sockets'/(role+'.sock')))
 runtime=root/'caddy.json';private_write(runtime,text)
 cp=spawn([CADDY,'run','--config',str(runtime)],'caddy')
 ca=root/'xdg-data/caddy/pki/authorities/local/root.crt';wait(ca.exists,cp)
 context=ssl.create_default_context(cafile=str(ca));wait(lambda:request(tls_port,'/authelia/api/health',tls=True)[0]==200,cp)
 try:request(tls_port,'/authelia/api/health',tls=True,trust=ssl.create_default_context())
 except ssl.SSLCertVerificationError:pass
 else:raise AssertionError('Untrusted owned CA unexpectedly accepted')
 cases.append('real_caddy_tls_owned_ca_trusted_and_untrusted_ca_denied')
 status,_,_=request(tls_port,'/note.md',tls=True,headers=forged)
 assert status in (401,302,303),status
 def login(user):
  cookies.clear()
  s,b,_=request(tls_port,'/authelia/api/firstfactor',tls=True,method='POST',data={'username':user,'password':pw,'keepMeLoggedIn':False,'targetURL':'https://nas.wttliou.top/note.md'},session=True,headers={'Origin':'https://nas.wttliou.top'})
  assert s==200,(s,b)
  s,_,_=request(tls_port,'/note.md',tls=True,session=True);assert s in (401,302,303),s
  counter=int(time.time())//30;value=hmac.new(base64.b32decode(secret+'='*((-len(secret))%8)),struct.pack('>Q',counter),hashlib.sha1).digest();offset=value[-1]&15
  token=str((struct.unpack('>I',value[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
  s,b,_=request(tls_port,'/authelia/api/secondfactor/totp',tls=True,method='POST',data={'token':token,'targetURL':'https://nas.wttliou.top/note.md'},session=True,headers={'Origin':'https://nas.wttliou.top'})
  assert s==200,(s,b)
 login('synthetic')
 assert request(tls_port,'/note.md',tls=True,session=True,headers=forged)[:2]==(200,b'private original')
 status,body,_=request(tls_port,'/tag-api/tags',tls=True,session=True,method='POST',data={'name':'tls-admin-write'},headers={'Origin':'https://nas.wttliou.top',**forged});assert status==201,(status,body)
 admin_management=request(tls_port,'/tag-api/v1/peers/approvals',tls=True,session=True,headers=forged)
 assert admin_management[0]==200,admin_management
 cases.append('real_authelia_password_plus_totp_required_verified_admin_identity_and_write')
 login('reader')
 assert request(tls_port,'/note.md',tls=True,session=True,headers=forged)[0]==200
 reader_result=request(tls_port,'/tag-api/v1/peers/approvals',tls=True,session=True,headers=forged)
 assert reader_result[0] in (401,403),reader_result
 cases.append('real_authelia_nonadmin_cannot_forge_admin_groups_for_management')
 # Exact HAProxy TCP discriminator from the candidate, only endpoint addresses/ports relocated.
 haproxy=candidate_readonly_transport((ROOT/'deploy/haproxy.readonly.cfg').read_text()).replace('bind :5008','bind 127.0.0.1:'+str(dual_port)).replace('host.containers.internal:18182','127.0.0.1:'+str(readonly_port)).replace('caddy:5443','127.0.0.1:'+str(readonly_tls_port))
 hpfile=root/'haproxy.cfg';private_write(hpfile,haproxy);run([HAPROXY,'-c','-f',str(hpfile)])
 gateway_image=proof['retained_images']['readonly-gateway'].removeprefix('sha256:')
 archive=root/'gateway.tar'
 run(['podman','--remote','--url','unix:///run/user/1000/podman/podman.sock','save','--output',str(archive),gateway_image])
 connection=stack.enter_context(isolated_runtime(root,archive,gateway_image))
 gateway_engine=['podman','--remote','--url',connection];gateway_name='trust-'+root.name
 run(gateway_engine+['run','-d','--name',gateway_name,'--network=host','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','0:0','--memory=64m','--cpus=1','--pids-limit=64','--mount','type=bind,src='+str(hpfile)+',dst=/tmp/entry-haproxy.cfg,ro','--entrypoint','/usr/local/sbin/haproxy',gateway_image,'-db','-f','/tmp/entry-haproxy.cfg'])
 wait(lambda:request(dual_port,'/note.md',host='nuc.local:5008',headers=auth_header)[0]==200,cp)
 assert request(dual_port,'/note.md',host='nuc.local:5008',headers=forged)[0]==401
 assert request(dual_port,'/note.md',host='work.wttliou.top:5008',tls=True,headers=auth_header)[:2]==(200,b'readonly original')
 assert request(dual_port,'/note.md',host='work.wttliou.top:5008',tls=True,headers=forged)[0]==401
 for tls,host,origin in [(False,'nuc.local:5008','http://nuc.local:5008'),(True,'work.wttliou.top:5008','https://work.wttliou.top:5008')]:
  s,b,_=request(dual_port,'/tag-api/tags',host=host,tls=tls,headers={**auth_header,'Origin':origin},method='POST',data={'name':'readonly-denied'});assert s==405,(s,b)
 cases.append('real_haproxy_http_and_tls_same_port_authentication_and_readonly_mutation_denial')
 assert request(tls_port,'/tag-api/v1/peers/identity',tls=True,headers=forged)[0]==200
 assert request(tls_port,'/tag-api/v1/peers/approvals',tls=True,headers=forged)[0] in (401,302,303)
 cases.append('real_private_peer_scope_identity_not_general_admin_access')
 # Record OPTIONS compatibility explicitly; no write handler is invoked.
 options={}
 for label,p,tls,host,headers in [('lan',private_port,False,'nuc.local:5006',auth_header),('readonly-http',dual_port,False,'nuc.local:5008',auth_header),('readonly-tls',dual_port,True,'work.wttliou.top:5008',auth_header),('external',tls_port,True,'nas.wttliou.top',{})]:
  origin=('https://' if tls else 'http://')+host
  options[label]=request(p,'/tag-api/tags',host=host,tls=tls,method='OPTIONS',headers={**headers,'Origin':origin,'Access-Control-Request-Method':'POST'},session=label=='external')[0]
 assert request(tls_port,'/tag-api/tags',tls=True,method='OPTIONS',headers={'Origin':'https://nas.wttliou.top','Access-Control-Request-Method':'POST'},session=False)[0] in (401,302,303)
 for p,tls,host,headers in [(private_port,False,'nuc.local:5006',auth_header),(dual_port,True,'work.wttliou.top:5008',auth_header),(tls_port,True,'nas.wttliou.top',{})]:
  assert request(p,'/tag-api/tags',host=host,tls=tls,method='OPTIONS',headers={**headers,'Origin':'https://untrusted.invalid','Access-Control-Request-Method':'POST'},session=tls and p==tls_port)[0]==403
 print('OPTIONS statuses:',json.dumps(options),flush=True)
 assert all(v in (200,204) for v in options.values()),options
 cases.append('same_origin_options_preflight_compatible_and_nonmutating')
 # Restrict only the owned test listeners to an intentionally non-matching source.
 cp.terminate();cp.wait(timeout=10)
 restricted=json.loads(text)
 def restrict(value):
  if isinstance(value,dict):
   if 'remote_ip' in value:value['remote_ip']['ranges']=['192.0.2.0/24']
   for child in value.values():restrict(child)
  elif isinstance(value,list):
   for child in value:restrict(child)
 restrict(restricted);private_write(runtime,json.dumps(restricted))
 cp=spawn([CADDY,'run','--config',str(runtime)],'caddy-restricted')
 wait(lambda:request(tls_port,'/tag-api/v1/peers/identity',tls=True,headers={'X-Forwarded-For':'192.0.2.1'})[0]==404,cp)
 ap,cmd,ef=apps['private'];ap.terminate();ap.wait(timeout=10)
 private_write(ef,re.sub(r'allowed_sources = \[.*?\]', 'allowed_sources = ["192.0.2.0/24"]',ef.read_text(),count=1))
 ap=spawn(cmd,'private-restricted');wait(lambda:request(private_port,'/note.md',host='nuc.local:5006',headers={**auth_header,'X-Forwarded-For':'192.0.2.1'})[0]==403,ap)
 cases.append('real_caddy_and_application_source_filters_reject_forged_forwarded_source')
 report={'stage':'E4.a','cases':cases,'binary_sha256':proof['application_packages']['nuc']['binary_sha256'],'candidate':str(candidate),'tools':str(TOOLS),'caddy':CADDY,'authelia_image':authelia_image,'authelia_version':authelia_version,'readonly_gateway_image':gateway_image,'options':options,'production_access':False,'activated':False,'auth_scope':'Actual rendered two_factor policy, actual password and TOTP sessions; only owned synthetic users/CA/secrets/state.','limitations':['Native Authelia from product lock matches retained image version 4.39.20; HAProxy runs in the exact retained image in an owned runtime. Full installed namespace composition remains E4.b/c.','No production login/profile/CA/database tested; production acceptance remains E5.']}
except Exception:
 if gateway_engine and gateway_name:
  logs=subprocess.run(gateway_engine+['logs',gateway_name],capture_output=True,text=True);print(logs.stderr[-1500:],file=sys.stderr)
 for p in root.glob('*.log'):print(p.name,p.read_text()[-2500:],file=sys.stderr)
 raise
finally:
 if gateway_engine and gateway_name:run(gateway_engine+['rm','-f',gateway_name])
 stack.close()
 for p in reversed(processes):
  if p.poll() is None:
   p.terminate()
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
 for sock in owned_sockets:sock.close()
 shutil.rmtree(root)
report['owned_cleanup']=not root.exists() and all(p.poll() is not None for p in processes)
report['source_manifest']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['scripts/check-application-trust.py','scripts/application_nuc_ingress.py','deploy/scripts/render.py','tests/application-trust-tools.nix']}
(TAG/'.devenv/application-entry-trust-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(str(len(cases))+' real trust-chain cases passed; production unchanged')
