#!/usr/bin/env python3
"""Compose Knowledge Cards into fixed native frontend candidates; never stop services."""
import argparse,hashlib,json,os,shlex,shutil,subprocess,tempfile,time
from pathlib import Path
HOST='liou@nuc.local'
CURRENT=Path('/home/liou/.local/share/tag-all/native-version-releases/current.json')
MANAGER=Path('/nix/store/vb0phbx5f56nnhgm7bc1xf03cmrwhy73-tag-native-release-manager')
def run(args):return subprocess.check_output(args,text=True).strip()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def frontend_files(source):
 files=[f for f in source.rglob('*') if f.is_file()]
 assert files and not any(f.is_symlink() for f in source.rglob('*')), 'Symlink artifact'
 allowed={'.js','.css','.wasm','.woff','.woff2','.ttf'}
 assert all(f.relative_to(source).as_posix()=='index.html' or f.relative_to(source).parts[0]=='assets' and f.suffix in allowed for f in files),'Unexpected artifact'
 return files

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--web-root',type=Path,required=True);p.add_argument('--frontend-base',type=Path);p.add_argument('--prepare',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--proof',type=Path);a=p.parse_args()
 source=a.web_root.resolve();owned=str(source).endswith('/share/knowledge-cards/web') or source.name=='dist' and '-knowledge-cards-ui-' in source.parent.name
 assert str(source).startswith('/nix/store/') and owned and (source/'index.html').is_file(),'Use fixed Knowledge Cards frontend output'
 files=frontend_files(source)
 proof={'source':str(source),'web_files':{str(f.relative_to(source)):digest(f) for f in files},'entry_url':'http://nuc.local:5006/dist/knowledge-cards/index.html?view=new','native_composition_required':True,'activated':False,'service_stopped':False}
 if not a.prepare or a.dry_run:print(json.dumps(proof,indent=2));return
 ssh=['ssh',HOST];pc=json.loads(CURRENT.read_text());nuc=json.loads(run(ssh+['cat',str(CURRENT)]));assert pc['package']==nuc['package'];package=pc['package']
 base=a.frontend_base.resolve() if a.frontend_base else Path(pc['frontend']).resolve()
 assert a.frontend_base or pc['frontend']==nuc['frontend'],'Different current frontends require explicit fixed base'
 assert str(base).startswith('/nix/store/') and (base/'index.html').is_file() and not any(f.is_symlink() for f in base.rglob('*')),'Unsafe frontend base'
 with tempfile.TemporaryDirectory(prefix='knowledge-cards-composite-') as folder:
  composite=Path(folder)/'dufs-plus-knowledge-cards-frontend';shutil.copytree(base,composite)
  composite.chmod(0o755)
  for directory in composite.rglob('*'):
   if directory.is_dir():directory.chmod(0o755)
  owned=composite/'knowledge-cards'
  if owned.exists():shutil.rmtree(owned)
  shutil.copytree(source,owned)
  for f in composite.rglob('*'):f.chmod(0o755 if f.is_dir() else 0o644)
  frontend=run(['nix-store','--add',str(composite)])
 subprocess.run(['nix-copy-closure','--to',HOST,package,frontend,str(MANAGER)],check=True);time.sleep(1)
 proof.update(package=package,frontend=frontend,frontend_base=str(base),manager_package=str(MANAGER),targets={},backend_unchanged=True,binary_sha256=digest(Path(package)/'libexec/tag-server-workspace'),frontend_index_sha256=digest(Path(frontend)/'index.html'),root_assets_sha256={f.name:digest(f) for f in Path(frontend).iterdir() if f.is_file()})
 for scope in ['pc','nuc']:
  command=([str(MANAGER/'bin/tag-native-release'),'--scope',scope] if scope=='pc' else ssh+[str(MANAGER/'bin/tag-native-release'),'--scope',scope])+['--package',package,'--frontend',frontend]
  preview=json.loads(run(command));assert not preview['activated'] and preview['processing_idle']
  prepared=json.loads(run(command+['--prepare']))['prepared'];assert prepared.startswith('/home/liou/.local/share/tag-all/native-version-releases/')
  manifest=json.loads(Path(prepared+'/manifest.json').read_text() if scope=='pc' else run(ssh+['cat',prepared+'/manifest.json']))
  for name,after in manifest['commands'].items():
   before=shlex.split(manifest['units'][name]['command']);updated=shlex.split(after);assert before[0]==package+'/bin/tag-all-core';before[before.index('--workspace-entry-frontend')+1]=frontend;assert before==updated
  proof['targets'][scope]={'prepared':prepared,'preview':preview,'changed_only_frontend':True}
 if a.proof:a.proof.parent.mkdir(parents=True,exist_ok=True);a.proof.write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
