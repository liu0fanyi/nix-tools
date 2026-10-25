#!/usr/bin/env python3
"""Publish one explicitly selected desktop runtime closure and latest pin."""
import argparse,json,os,re,stat,subprocess,sys,urllib.request
from pathlib import Path
CACHE='liu0fanyi-nix'
KEY='liu0fanyi-nix.cachix.org-1:ihYHglsAtVvR6W+7m/tyjB+9S4f5e86mcygT7CMy144='
TOKEN=Path.home()/'.config/secrets/nix-tools/cachix-auth-token'
def credentials():
 env=dict(os.environ)
 if env.get('CACHIX_AUTH_TOKEN') or env.get('CACHIX_SIGNING_KEY'):return env
 token=Path(env.get('CACHIX_AUTH_TOKEN_FILE',str(TOKEN)))
 if token.exists():
  fd=os.open(token,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   info=os.fstat(fd)
   if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:raise ValueError('Cache token must be a private regular file owned by this user')
   with os.fdopen(fd,'r',closefd=False) as f:value=f.read(16385).strip()
   if not value or len(value)>16384 or any(c.isspace() for c in value):raise ValueError('Invalid cache token format')
   env['CACHIX_AUTH_TOKEN']=value
  finally:os.close(fd)
  return env
 config=Path(env.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'cachix/cachix.dhall'
 if config.is_file():return env
 raise ValueError('No existing private Cachix upload credentials')
def run(args,**kw):return subprocess.check_output(args,text=True,**kw).strip()
def pins():
 req=urllib.request.Request('https://app.cachix.org/api/v1/cache/'+CACHE+'/pin',headers={'User-Agent':'desktop-cache-publisher/1'})
 with urllib.request.urlopen(req,timeout=40) as r:return {p['name']:p for p in json.load(r)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--attribute',default='default');p.add_argument('--pin',required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--dry-run',action='store_true');p.add_argument('--expected-package');a=p.parse_args()
 if not a.repo.resolve().is_dir() or not re.fullmatch(r'[a-z0-9-]+-latest',a.pin) or not re.fullmatch(r'[A-Za-z0-9_-]+',a.attribute):raise ValueError('Invalid source, attribute or latest pin')
 if a.dry_run:print(json.dumps({'source':str(a.repo.resolve()),'attribute':a.attribute,'cache':CACHE,'pin':a.pin,'keep_revisions':1,'only_runtime_closure':True,'credentials_read':False},indent=2));return
 env=credentials();before=pins();package=run(['nix','build','--no-link','--print-out-paths',str(a.repo.resolve())+'#'+a.attribute])
 if len(package.splitlines())!=1 or not package.startswith('/nix/store/'):raise ValueError('Expected one immutable package output')
 if a.expected_package and package!=a.expected_package:raise ValueError('Built package differs from verified candidate')
 cmd=['nix','shell','--inputs-from',str(a.repo.resolve()),'nixpkgs#cachix','--command','cachix']
 subprocess.run(cmd+['push',CACHE,package],env=env,check=True)
 assert run(['nix','path-info','--refresh','--store','https://'+CACHE+'.cachix.org',package])==package
 subprocess.run(['nix','store','copy-sigs','-s','https://'+CACHE+'.cachix.org',package],check=True)
 subprocess.run(['nix','store','verify','--sigs-needed','1','--extra-trusted-public-keys',KEY,package],check=True)
 subprocess.run(cmd+['pin',CACHE,a.pin,package,'--keep-revisions','1'],env=env,check=True)
 after=pins();current=after[a.pin]
 assert current['lastRevision']['storePath']==package and current['keep']=={'tag':'Revisions','contents':1} and not current['lastRevision']['orphaned']
 for name,old in before.items():
  if name!=a.pin:assert after[name]['lastRevision']['storePath']==old['lastRevision']['storePath'],name
 proof={'package':package,'cache':CACHE,'trusted_signature_verified':True,'pin':current,'other_pins_unchanged':sorted(n for n in before if n!=a.pin),'only_runtime_closure':True}
 a.proof.parent.mkdir(parents=True,exist_ok=True);a.proof.write_text(json.dumps(proof,indent=2)+'\n');print('Verified package published and latest pin updated:',package)
if __name__=='__main__':
 try:main()
 except (OSError,ValueError,AssertionError,subprocess.SubprocessError):
  print('Desktop cache publication failed; inspect source/build/cache permissions. No success asserted.',file=sys.stderr);sys.exit(1)
