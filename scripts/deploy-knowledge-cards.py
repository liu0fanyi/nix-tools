#!/usr/bin/env python3
"""Deliver only the immutable Knowledge Cards web subtree; activation is explicit."""
import argparse,hashlib,json,shlex,subprocess,time,uuid
from pathlib import Path
HOST='liou@nuc.local'
DEST='/home/liou/dufs-lan/dist/knowledge-cards'
BACKUPS='/home/liou/dufs-lan/.app-backups/knowledge-cards'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--web-root',type=Path,required=True);p.add_argument('--activate',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 source=a.web_root.resolve();assert str(source).startswith('/nix/store/') and str(source).endswith('/share/knowledge-cards/web') and (source/'index.html').is_file(),'Use the verified Nix package web output'
 files=[f for f in source.rglob('*') if f.is_file()];assert files and not any(f.is_symlink() for f in source.rglob('*'))
 assert all(f.relative_to(source).as_posix()=='index.html' or f.relative_to(source).parts[0]=='assets' and f.suffix in ('.js','.css') for f in files),'Unexpected web artifact'
 manifest={f.relative_to(source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
 print(json.dumps({'source':str(source),'target':HOST+':'+DEST,'files':manifest,'only_owned_subtree':True,'activation':a.activate and not a.dry_run},indent=2),flush=True)
 if not a.activate or a.dry_run:return
 stage=DEST+'.stage-'+uuid.uuid4().hex;backup=BACKUPS+'/'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
 def ssh(cmd):subprocess.run(['ssh',HOST,cmd],check=True);time.sleep(1)
 ssh('set -eu; test ! -L '+shlex.quote(DEST)+'; mkdir -p '+shlex.quote(stage)+' '+shlex.quote(BACKUPS))
 subprocess.run(['rsync','-rptz','--checksum','--chmod=D755,F644',str(source)+'/',HOST+':'+stage+'/'],check=True);time.sleep(1)
 result=subprocess.check_output(['rsync','-rptz','--checksum','--delete','--dry-run','--itemize-changes','--chmod=D755,F644',str(source)+'/',HOST+':'+stage+'/'],text=True);assert not result.strip(),result
 ssh('set -eu; if test -e '+shlex.quote(DEST)+'; then mv '+shlex.quote(DEST)+' '+shlex.quote(backup)+'; fi; if mv '+shlex.quote(stage)+' '+shlex.quote(DEST)+'; then chmod 755 '+shlex.quote(DEST)+'; else test ! -e '+shlex.quote(backup)+' || mv '+shlex.quote(backup)+' '+shlex.quote(DEST)+'; exit 1; fi')
 result=subprocess.check_output(['rsync','-rptz','--checksum','--delete','--dry-run','--itemize-changes','--chmod=D755,F644',str(source)+'/',HOST+':'+DEST+'/'],text=True);assert not result.strip(),result
 print('Verified owned web subtree activated; previous subtree retained at '+backup)
if __name__=='__main__':main()
