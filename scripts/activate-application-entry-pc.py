#!/usr/bin/env python3
"""PC entry cutover: read-only by default; --apply/--rollback are user terminal actions."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
from application_entry_transaction import ConfigurationTransaction, atomic, backup_state, create_lock, digest, exclusive, offline_states, private

PRODUCT=Path('/data/project/tag-all')
PROOF=PRODUCT/'specs/027-application-entry-boundary/entry-pc-preparation-results.json'
ROOT=Path('/home/liou/.local/share/tag-all/pc-native')
UNITS=['tag-native-stack.target','tag-native-workspace.service','tag-all-core.service','tag-native-files.service','tag-all-tools.service']
SYSTEM='/nix/store/5fbv5sg8mlcdqgq6pz391sl9qxaalb48-nixos-system-liu-bigpc-26.11.20260922.b6c98e9'
PREVIOUS='/nix/store/q9cvijcr3xz9wdaby5bm0i34zg3p54q5-nixos-system-liu-bigpc-26.11.20260922.b6c98e9'


def run(argv):
    return subprocess.run(argv,check=True,capture_output=True,text=True,timeout=1800)


def status():
    result={}
    for name in UNITS:
        text=run(['systemctl','--user','show',name,'--property=ActiveState']).stdout
        result[name]=text.strip().split('=',1)[1]
    return result


def preflight(rollback=False):
    if socket.gethostname()!='liu-bigpc' or os.getuid()!=1000:raise ValueError('Fixed PC host/user required')
    proof=json.loads(PROOF.read_text())
    if proof['candidate_generation']['system']!=SYSTEM or proof['candidate_generation']['rollback_system']!=PREVIOUS:
        raise ValueError('Frozen PC generations required')
    target=ROOT/'config/application-entry.toml'
    if proof['entry_target']!=str(target) or proof['state_directory']!=str(ROOT/'data'):raise ValueError('Fixed PC state/entry targets required')
    private(ROOT,True);private(ROOT/'peer-caddy',True)
    for name,sha in proof['current_input_sha256'].items():
        if digest(private(name))!=sha:raise ValueError('PC input drifted')
    if digest(private(proof['entry_file']))!=proof['entry_sha256']:raise ValueError('PC staged entry changed')
    expected=SYSTEM if rollback else PREVIOUS
    active=str(Path('/run/current-system').resolve())
    if active not in ([SYSTEM,PREVIOUS] if rollback else [expected]):raise ValueError('PC active generation changed')
    if str(Path('/nix/var/nix/profiles/system').resolve()) not in ([SYSTEM,PREVIOUS] if rollback else [expected]):raise ValueError('PC system profile drifted')
    if (ROOT/'container-mode').exists():raise ValueError('PC is not in native mode')
    if not rollback:
        private(ROOT/'ready')
        if any(value!='active' for value in status().values()):raise ValueError('Current PC stack unavailable')
    if status()['tag-all-tools.service']=='active':
        current=json.loads(run(['podman','--remote','--url','unix://'+str(ROOT/'tools/runtime.sock'),'ps','--format','json']).stdout)
        if current:raise ValueError('Processing tasks active; wait before switch')
    for system in [SYSTEM,PREVIOUS]:
        if not (Path(system)/'bin/switch-to-configuration').is_file():raise ValueError('Fixed generation unavailable')
    return proof,target


def stopped():
    if any(value not in {'inactive','failed'} for value in status().values()):raise ValueError('PC native units still running')
    for port in [5006,5009]:
        with socket.socket() as probe:probe.bind(('0.0.0.0',port))


def execute(proof,target,rollback):
    run(['sudo','-v'])
    preflight(rollback)
    transaction=ConfigurationTransaction(ROOT/'application-entry-cutover',{target})
    if rollback:transaction.load()
    else:transaction.create({target:{'kind':'file','source':proof['entry_file'],'sha256':proof['entry_sha256']}})
    barrier=ROOT/'application-entry-cutover/ready-before-switch'
    # Moving ready disables native startup conditions while HM changes units.
    if (ROOT/'ready').exists():
        if barrier.exists():raise ValueError('Ready barrier collision')
        os.rename(ROOT/'ready',barrier)
    private(barrier)
    transaction.phase('rollback-stopping' if rollback else 'stopping')
    try:
        print('PC: stopping the scoped native stack; saved-editor confirmation received',flush=True)
        run(['systemctl','--user','stop',UNITS[0]])
        run(['systemctl','--user','stop',*UNITS[1:]])
        with offline_states([ROOT/'data'],stopped):
            if not rollback:
                print('PC: creating the offline backup; rollback will keep current data',flush=True)
                receipt=backup_state(ROOT/'data',ROOT/'application-entry-cutover/backup-state')
                archive=ROOT/'application-entry-cutover/peer-caddy.tar'
                source=private(ROOT/'peer-caddy',True)
                with tarfile.open(archive,'x',dereference=False) as out:out.add(source,arcname='peer-caddy')
                archive.chmod(0o600)
                with archive.open('rb') as stream:os.fsync(stream.fileno())
                atomic(ROOT/'application-entry-cutover/offline-backup.json',json.dumps({'state':receipt,'pki_sha256':digest(archive),'restore_allowed':False})+'\n')
            transaction.install(rollback)
        selected=PREVIOUS if rollback else SYSTEM
        transaction.phase('user-system-activation')
        # This code path is reserved for the user's ordinary terminal, never agent execution.
        print('PC: activating the fixed system generation from your terminal',flush=True)
        run(['sudo','nix-env','--profile','/nix/var/nix/profiles/system','--set',selected])
        run(['sudo',selected+'/bin/switch-to-configuration','switch'])
        if str(Path('/run/current-system').resolve())!=selected:raise ValueError('System activation did not select frozen generation')
        if (ROOT/'ready').exists():raise ValueError('Unexpected ready marker during activation')
        os.rename(barrier,ROOT/'ready')
        run(['systemctl','--user','daemon-reload'])
        run(['systemctl','--user','reset-failed',*UNITS])
        run(['systemctl','--user','start',UNITS[0]])
        if any(value!='active' for value in status().values()):raise ValueError('PC stack did not recover')
        transaction.phase('rolled-back-current-state' if rollback else 'activated-awaiting-P3')
        print('PC: stack active; return to chat for live acceptance',flush=True)
    except BaseException:
        # Never resume automatically or restore state on an activation failure.
        if (ROOT/'ready').exists() and not barrier.exists():os.rename(ROOT/'ready',barrier)
        subprocess.run(['systemctl','--user','stop',*UNITS],capture_output=True,timeout=120)
        transaction.phase('failed-keep-current-state-and-ready-barrier')
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group();group.add_argument('--apply',action='store_true');group.add_argument('--rollback',action='store_true')
    parser.add_argument('--editors-saved',action='store_true');opts=parser.parse_args()
    if (opts.apply or opts.rollback) and not opts.editors_saved:raise ValueError('Fresh PC saved-editor confirmation required')
    proof,target=preflight(opts.rollback)
    if opts.apply or opts.rollback:
        lock=ROOT/'application-entry-cutover.lock'
        create_lock(lock)
        with exclusive(lock):execute(proof,target,opts.rollback)
    else:print(json.dumps({'stage':'E5/P2','dry_run':True,'target':str(target),'system':SYSTEM,'rollback_system':PREVIOUS,
        'system_activation_by_user_only':True,'restore_state_on_rollback':False,'production_changed':False,'database_read':False},indent=2))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('PC entry switch refused: '+type(error).__name__+'; current state is never restored from backup',file=sys.stderr)
        raise SystemExit(1)
