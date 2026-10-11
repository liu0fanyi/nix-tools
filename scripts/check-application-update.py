#!/usr/bin/env python3
"""E3.d immutable inventory, real Compose config and serial old/new state rehearsal."""
import copy,hashlib,json,os,shlex,shutil,socket,subprocess,sys,tempfile,time,tomllib,urllib.request,urllib.error
from pathlib import Path
from application_entry_release import manifest,prepare_synthetic_configuration,application_compose,handover_plan,digest,rebind_startup_control,RUNTIME,inventory_fingerprint
from application_nuc_ingress import render,candidate_ingress,candidate_readonly_transport
ROOT=Path(__file__).resolve().parents[1]
TAG=Path(sys.argv[1]).resolve();OUT=TAG/'.devenv'
sys.path.insert(0,'/nix/store/iw39pw567acajnaf1iywnwz6fwcb6cxg-python3.14-pyyaml-6.0.3/lib/python3.14/site-packages')
import yaml
PROVIDER='/etc/profiles/per-user/liou/bin/podman-compose'
DUFS='/nix/store/ph17xq80q9by2vmivfvm97a1729q4cgl-dufs-0.46.0/bin/dufs'
CADDY='/nix/store/z7n5vmb63i55f9xzish6fhyxlmwy6mrf-caddy-2.11.4/bin/caddy'
read=lambda file:json.loads(Path(file).read_text())
proof=read(TAG/'specs/027-application-entry-boundary/entry-application-results.json')
for name,sha in proof['source_manifest'].items():assert digest(TAG/name)==sha,name
pc=read(OUT/'application-entry-pc-results.json');nuc=read(OUT/'application-entry-nuc-results.json')
for candidate in [pc,nuc]:
 for name,sha in candidate['source_manifest'].items():assert digest(ROOT/name)==sha,name
legacy=read(OUT/'native-workspace-results.json');old_binary=Path(legacy['package'])/'libexec/tag-server-workspace'
assert digest(old_binary)==legacy['binary_sha256']
old_nuc=read(TAG/'specs/025-native-nuc-rollout/candidate-results.json')['candidate']
current_system=subprocess.check_output(['readlink','-f','/run/current-system'],text=True).strip()
release=manifest(pc,nuc,current_system,old_nuc,proof)
names=['dufs-plus_'+name+'_1' for name in ['tag-server','tag-server-readonly','dufs','dufs-readonly','tag-peer-discovery','caddy','authelia','readonly-gateway','ddns-go']]
inspection=subprocess.run(['ssh','-F','/home/liou/.ssh/config','liou@nuc.local','podman inspect '+' '.join(names)],capture_output=True,text=True,timeout=45)
if inspection.returncode:raise RuntimeError('Read-only NUC inventory failed; inspect output is not printed')
source_images,images=inventory_fingerprint(json.loads(inspection.stdout))
del inspection
assert set(images)=={'caddy','authelia','readonly-gateway','ddns-go'}
release['retained_images']=images
release['startup_source_images']=source_images
release['rollback_binary']={'package':legacy['package'],'binary_sha256':legacy['binary_sha256']}
release['source_manifest']={name:digest(ROOT/name) for name in ['scripts/application_entry_release.py','scripts/check-application-update.py','scripts/application_nuc_ingress.py','deploy/instances/home.toml','deploy/scripts/render.py','deploy/compose.yaml','deploy/compose.home-ipv6-cdn.yaml','deploy/compose.authelia.yaml','deploy/compose.readonly.yaml','deploy/compose.ddns.yaml','deploy/haproxy.readonly.cfg']}
cases=[];procs=[]
def call(args,cwd=None,timeout=90):
 result=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout)
 if result.returncode:raise RuntimeError((result.stdout+result.stderr)[-2500:])
 return result.stdout

def canonical_provider_model(model,base):
 # The real provider does all interpolation/merging; only expand its fixed short bind/port notation.
 for service in model['services'].values():
  if 'volumes' in service:
   normalized=[]
   for volume in service['volumes']:
    if isinstance(volume,dict):normalized.append(volume);continue
    parts=volume.split(':')
    if len(parts) not in (2,3) or not parts[1].startswith('/'):raise ValueError('Unknown source bind syntax')
    source=Path(parts[0]);source=source if source.is_absolute() else base/source
    if len(parts)==3 and parts[2] not in ('ro','rw'):raise ValueError('Unknown bind policy')
    normalized.append({'type':'bind','source':str(source),'target':parts[1],'read_only':len(parts)==3 and parts[2]=='ro'})
   service['volumes']=normalized
  if 'ports' in service:
   normalized=[]
   for port in service['ports']:
    if isinstance(port,dict):normalized.append(port);continue
    parts=str(port).split(':')
    if len(parts)!=3 or parts[0]!='0.0.0.0' or not all(v.isdecimal() for v in parts[1:]):raise ValueError('Unknown fixed port syntax')
    normalized.append({'host_ip':parts[0],'published':int(parts[1]),'target':int(parts[2]),'protocol':'tcp'})
   service['ports']=normalized
 return model

root=Path(tempfile.mkdtemp(prefix='entry-update-dry-run-',dir=OUT));root.chmod(0o700)
owned_cleaned=False
try:
 templates={'pc':'peer_socket="'+release['target_roots']['pc']+'/sockets/peer.sock"\npeer_authorities=["liu-bigpc.local:5009"]\npeer_write_delegation=true\n'}
 for role in ['private','readonly']:templates[role]=(Path(nuc['candidate'])/(role+'-entry.toml')).read_text()
 source=root/'synthetic.entries';password='synthetic-update-password'
 source.write_text('synthetic '+call([CADDY,'hash-password','--algorithm','bcrypt','--plaintext',password]).strip()+'\n');source.chmod(0o600)
 prepare_synthetic_configuration(root,templates,{'private':source,'readonly':source})
 for role in templates:
  assert (root/role/'config/application-entry.toml').stat().st_mode&0o777==0o600
  assert (root/role/'config').stat().st_mode&0o777==0o700
 cases.append('runtime_staging_private_credentials_and_apps_no_database_copy')

 # Real full model from existing renderer + the actual installed Compose provider.
 config=tomllib.loads((ROOT/'deploy/instances/home.toml').read_text())
 fixture=copy.deepcopy(config)
 for key in fixture['paths']:fixture['paths'][key]=str(root/'source-paths'/key)
 secrets=Path(fixture['paths']['secrets']);secrets.mkdir(parents=True,mode=0o700)
 runtime=root/'compose';runtime.mkdir(mode=0o700)
 for name in render.compose_asset_names(config):
  if name!='compose.instance.yaml':shutil.copyfile(ROOT/'deploy'/name,runtime/name)
 (runtime/'compose.instance.yaml').write_text(render.render_instance_compose(fixture,runtime,secrets))
 files=render.compose_asset_names(config)
 env=root/'compose.env'
 variables={'COMPOSE_PROJECT_NAME':'entry-update-dry-run','CONTAINER_SUBNET':'10.89.50.0/24','LAN_PUBLISH_PORT':'5006','MAIN_ORIGIN_PUBLISH_PORT':'5009','READONLY_ORIGIN_PUBLISH_PORT':'5008','TZ':'Asia/Shanghai',
 'CADDY_IMAGE':'sha256:'+images['caddy'].removeprefix('sha256:'),'AUTHELIA_IMAGE':'sha256:'+images['authelia'].removeprefix('sha256:'),'READONLY_GATEWAY_IMAGE':'sha256:'+images['readonly-gateway'].removeprefix('sha256:'),'DDNS_GO_IMAGE':'sha256:'+images['ddns-go'].removeprefix('sha256:'),'DUFS_IMAGE':'sha256:'+'1'*64,'TAG_SERVER_IMAGE':'sha256:'+'2'*64}
 env.write_text(''.join(name+'='+value+'\n' for name,value in variables.items()));env.chmod(0o600)
 argv=[PROVIDER,'--env-file',str(env)]
 for name in files:argv+=['-f',str(runtime/name)]
 merged=canonical_provider_model(yaml.safe_load(call(argv+['config'],runtime)),runtime)
 transformed=application_compose(merged)
 out=root/'application-compose.json';out.write_text(json.dumps(transformed));out.chmod(0o600)
 final=canonical_provider_model(yaml.safe_load(call([PROVIDER,'-f',str(out),'config'],runtime)),runtime)
 assert set(final['services'])=={'caddy','authelia','readonly-gateway','ddns-go'}
 assert {int(p['target']) for p in final['services']['caddy']['ports']}=={5009}
 assert final['services']['caddy']['entrypoint']==['caddy']
 for name in ['authelia','ddns-go']:assert final['services'][name]==merged['services'][name],name
 assert 'tag-peer-admin.env' not in json.dumps(final['services']['caddy'])
 assert 'TAG_PEER_ADMIN_TOKEN' not in json.dumps(final['services']['caddy'])
 assert final['networks']==merged['networks']
 assert final['services']['readonly-gateway']['extra_hosts']['host.containers.internal']=='host-gateway'
 release['compose_model_sha256']=digest(out)
 release['compose_model_scope']='Synthetic staging paths only; production model must be rendered and fingerprinted in E5'
 release['compose_provider']=str(Path(PROVIDER).resolve())
 release['haproxy_candidate_sha256']=hashlib.sha256(candidate_readonly_transport((ROOT/'deploy/haproxy.readonly.cfg').read_text()).encode()).hexdigest()
 cases.append('actual_provider_full_merged_compose_no_old_writers_admin_environment_or_port_conflict')
 caddy_original=render.render_caddy(config,('synthetic',source.read_text().split()[1]))
 caddy_candidate,_=candidate_ingress(caddy_original,config)
 reviewed={RUNTIME+'/application-compose.json':digest(out),RUNTIME+'/Caddyfile':hashlib.sha256(caddy_candidate.encode()).hexdigest()}
 for role in ['private','readonly']:
  for name in ['application-entry.toml','basic.entries']:
   reviewed[release['target_roots']['nuc']+'/'+role+'/config/'+name]=digest(root/role/'config'/name)
 previous={'root':release['target_roots']['nuc'],'hostname':'nuc','uid':1000,'source_images':source_images,'files':{RUNTIME+'/compose.env':digest(env),RUNTIME+'/Caddyfile':hashlib.sha256(caddy_original.encode()).hexdigest()},'compose':['podman','compose','--env-file',RUNTIME+'/compose.env','-f',RUNTIME+'/previous.json']}
 control=rebind_startup_control(previous,reviewed)
 assert control['source_images']==previous['source_images'] and control['files'][RUNTIME+'/Caddyfile']==reviewed[RUNTIME+'/Caddyfile']
 assert control['compose'][-1]==RUNTIME+'/application-compose.json'
 release['startup_control_rebind_verified']=True
 cases.append('hash_bound_startup_control_rebound_to_full_model_and_reviewed_entry_inputs')

 # Actual old/new CLI serial handover against the SAME three synthetic stores.
 for role in ['pc','private','readonly']:
  data=root/role/'data';data.mkdir(mode=0o700)
  workspace=root/role/'workspace';workspace.mkdir(mode=0o700)
  frontend=root/role/'frontend';frontend.mkdir(mode=0o700);(frontend/'index.html').write_text('synthetic entry')
  (workspace/'note.md').write_text('preserved workspace')
  metadata=data/'metadata';metadata.mkdir(mode=0o700)
  (metadata/'paired-peers.json').write_text('[]\n')
  identity=metadata/'retained-node-identity';identity.write_text(role+'-synthetic-identity\n');identity.chmod(0o600)
  ca=root/role/'ca';ca.mkdir(mode=0o700);(ca/'root.crt').write_text('synthetic retained CA bytes');(ca/'root.key').write_text('synthetic retained private key bytes');(ca/'root.key').chmod(0o600)
  retained={str(file):digest(file) for file in [identity,metadata/'paired-peers.json',ca/'root.crt',ca/'root.key',workspace/'note.md']}
  node=root/role/'config/node.toml';node.write_text('[node]\nid="entry-update-'+role+'"\n[sync]\nenabled=false\n[pairing]\nenabled=false\n[discovery]\nenabled=false\n');node.chmod(0o600)
  files_socket=root/'sockets'/(role+'-files.sock')
  log=(root/(role+'-files.log')).open('w')
  fp=subprocess.Popen([DUFS,str(workspace),'--bind',str(files_socket),'--allow-all'],stdout=log,stderr=log);procs.append(fp)
  for _ in range(100):
   if files_socket.exists():break
   assert fp.poll() is None;time.sleep(.05)
  else:raise RuntimeError('Owned file upstream failed')
  process=None;latest=None
  def stop():
   global process
   if process is not None:
    process.terminate();process.wait(timeout=15);process=None
  def launch(binary,application):
   global process,base,application_prefix
   assert process is None,'Previous writer must be stopped'
   with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
   base='http://127.0.0.1:'+str(port);application_prefix='/tag-api' if application else ''
   command=[str(binary),'--workspace',str(workspace),'--database',str(data/'core.db'),'--metadata-dir',str(metadata),'--config',str(node),'--disable-sync','--addr','127.0.0.1:'+str(port)]
   if application:
    command+=['--workspace-entry-frontend',str(frontend),'--workspace-entry-dufs-socket',str(files_socket)]
    if role=='readonly':command+=['--workspace-entry-read-only']
   with (root/(role+'-core.log')).open('a') as corelog:process=subprocess.Popen(command,stdout=corelog,stderr=corelog)
   procs.append(process)
   for _ in range(200):
    if process.poll() is not None:raise RuntimeError((root/(role+'-core.log')).read_text()[-2000:])
    try:
     if request('/tags')[0]==200:return
    except (OSError,ConnectionError):pass
    time.sleep(.05)
   raise RuntimeError('Owned CLI did not become ready')
  def request(path,method='GET',data=None):
   req=urllib.request.Request(base+application_prefix+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Origin':base,'Content-Type':'application/json'})
   try:
    with urllib.request.urlopen(req,timeout=3) as response:return response.status,response.read()
   except urllib.error.HTTPError as error:return error.code,error.read()
  launch(old_binary,False)
  status,body=request('/tags','POST',{'name':'before-'+role});assert status==201
  first=json.loads(body)['id'];stop()
  database_inode=(data/'core.db').stat().st_ino
  latest=Path(release['application_packages']['pc' if role=='pc' else 'nuc']['path'])/'libexec/tag-server-workspace'
  launch(latest,True)
  assert 'before-'+role in request('/tags')[1].decode()
  if role=='readonly':
   assert request('/tags','POST',{'name':'must-not-write'})[0]==405
  else:
   assert request('/tags','POST',{'name':'during-'+role})[0]==201
   assert request('/tags/'+str(first),'DELETE')[0] in (200,204)
  stop();assert (data/'core.db').stat().st_ino==database_inode
  launch(old_binary,False)
  status,body=request('/tags');assert status==200
  tags=json.loads(body);names={t['name'] for t in tags}
  if role=='readonly':assert names=={'before-'+role}
  else:
   assert 'during-'+role in names and 'before-'+role not in names
   assert request('/tags','POST',{'name':'after-rollback-'+role})[0]==201
  stop()
  launch(latest,True)
  names={t['name'] for t in json.loads(request('/tags')[1])}
  if role!='readonly':assert {'during-'+role,'after-rollback-'+role}.issubset(names)
  stop()
  for file,sha in retained.items():assert digest(file)==sha,file
  assert (data/'core.db').stat().st_ino==database_inode
  fp.terminate();fp.wait(timeout=10);log.close()
  cases.append('actual_'+role+'_old_update_rollback_reupdate_same_db_tags_metadata_ca_identity')

 for target in ['pc','nuc']:
  for direction in ['update','rollback']:
   plan=handover_plan(release,target,direction,units_stopped=True,ports_released=True)
   assert plan['restore_old_database'] is False
 cases.append('four_handover_plans_preserve_current_state_and_require_single_writer')
 call([sys.executable,'-m','unittest','discover','-s',str(ROOT/'deploy/tests'),'-p','test_application_entry_release.py'])
 cases.append('composition_staging_and_handover_refusal_tests')
finally:
 for p in procs:
  if p.poll() is None:
   p.terminate()
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
 assert all(p.poll() is not None for p in procs)
 shutil.rmtree(root);owned_cleaned=not root.exists()
release['pc_candidate_refresh']=pc
release['owned_cleanup']=owned_cleaned
release['cases']=cases
release['production_database_access']=False
release['production_service_changed']=False
release['limitations']=['Synthetic serial CLI state rehearsal, not installed OS namespaces or production cutover; metadata/CA/identity checks use sentinel files, not real TLS identities.','Real final TLS/Authelia/HAProxy/OPTIONS/media/terminal/independent application combination remains E4.','PC rollback system is the currently observed immutable generation, to recheck before any user switch; no system switch executed.','E5 requires fresh saved-editor confirmation and runtime/configuration fingerprint recheck before applying.']
(OUT/'application-entry-update-results.json').write_text(json.dumps(release,indent=2)+'\n')
print('E3.d inventory/composition/state-preserving update and rollback rehearsal passed; no activation')
