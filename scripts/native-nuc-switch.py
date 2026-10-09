#!/usr/bin/env python3
"""Run the fixed prepared NUC control entry over verified SSH; default is read-only."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
REMOTE='/home/liou/.local/share/tag-all/nuc-native-release/'


def command(receipt,*,activate=False,rollback=False,editors_closed=False):
    release=receipt['prepared_release']
    if not re.fullmatch(re.escape(REMOTE)+'[a-f0-9]{64}',release) or release.rsplit('/',1)[1]!=receipt['manifest_sha256']:
        raise ValueError('Exact prepared release required')
    if activate and rollback:raise ValueError('Choose one action')
    if (activate or rollback) and not editors_closed:raise ValueError('Save and close editors before interruption')
    argv=['python3',release+'/native_nuc_switch.py',release]
    if activate:argv.append('--activate')
    if rollback:argv.append('--rollback')
    if editors_closed:argv.append('--editors-closed')
    return ['ssh','-F','/home/liou/.ssh/config','liou@nuc.local',shlex.join(argv)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group();action.add_argument('--activate',action='store_true');action.add_argument('--rollback',action='store_true')
    parser.add_argument('--editors-closed',action='store_true')
    args=parser.parse_args()
    try:
        receipt=json.loads((ROOT/'.devenv/native-nuc-preparation-results.json').read_text())
        result=subprocess.run(command(receipt,activate=args.activate,rollback=args.rollback,editors_closed=args.editors_closed),capture_output=True,text=True,timeout=1800)
        if result.returncode:
            print(result.stderr,file=sys.stderr);return result.returncode
        print(result.stdout,end='');return 0
    except (ValueError,KeyError,OSError,subprocess.SubprocessError) as error:
        print('NUC control refused: '+(str(error) if isinstance(error,ValueError) else type(error).__name__),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
