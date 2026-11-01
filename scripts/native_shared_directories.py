#!/usr/bin/env python3
"""NUC installation adapter for the browser's shared directory transaction.

Only the private NUC workspace is in scope. Directory validation, configuration
rendering, ownership and job guards stay in the exact packaged App helper.
"""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import uuid

UNITS=('tag-nuc-private-core.service','tag-nuc-private-files.service')
WORKSPACE=Path('/home/liou/dufs-lan')
ROOT=Path('/home/liou/.local/share/tag-all/nuc-native/private')


def load_helper(path, expected):
    path=Path(path).resolve(strict=True)
    if not str(path).startswith('/nix/store/') or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise ValueError('Exact immutable packaged helper required')
    loader=importlib.machinery.SourceFileLoader('directory_helper',str(path))
    spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module)
    module.UNITS=UNITS
    return module


def checked_rows(rows, workspace=WORKSPACE):
    if not isinstance(rows,list) or not rows:raise ValueError('Explicit directory inventory required')
    if not {'media/Art','media/project'} <= {r['prefix'] for r in rows}:raise ValueError('Legacy disk prefixes must remain')
    for row in rows:
        prefix=row['prefix'];source=Path(row['path'])
        if not row.get('enabled'):raise ValueError('Initial inventory must preserve enabled roots')
        if prefix.startswith('media/'):
            if prefix not in ['media/Art','media/project'] or source!=Path('/media/liou')/prefix.split('/')[1]:
                raise ValueError('Unreviewed disk mapping')
        elif '/' in prefix or prefix.startswith('.') or source!=workspace/prefix:
            raise ValueError('Existing workspace directories must retain their exact prefix')
    return rows


def local_location(node, workspace):
    locations=node.get('locations',[])
    if not locations:
        # Same implicit default as ServerConfig::load_or_default; no config write.
        return {'id':'default'}
    return next(v for v in locations if v.get('node_id',node['node']['id'])==node['node']['id'] and Path(v['path'])==workspace)


def installation(module, run):
    bindings={};conditions={};commands={}
    for unit in UNITS:
        props=dict(line.split('=',1) for line in run([module.SYSTEMCTL,'--user','show',unit,'-p','FragmentPath','-p','DropInPaths']).splitlines() if '=' in line)
        paths=[Path(props['FragmentPath']),*map(Path,shlex.split(props.get('DropInPaths','')))];bindings[unit]=[];conditions[unit]=[]
        if not str(paths[0].resolve(strict=True)).startswith('/nix/store/'):raise ValueError('Immutable installed NUC template required')
        for index,path in enumerate(paths):
            if path.name==module.MANAGED:
                if not module.regular(path,True).startswith(module.HEADER):raise ValueError('Directory override ownership changed')
                continue
            resolved=path.resolve(strict=True)
            text=resolved.read_text() if str(resolved).startswith('/nix/store/') else module.regular(path,True)
            command=module.unit_command(text)
            if command:commands[unit]=command
            for line in text.splitlines():
                for key,target in [('BindPaths',bindings[unit]),('ConditionPathIsDirectory',conditions[unit])]:
                    if line.startswith(key+'='):
                        raw=line.partition('=')[2]
                        if raw:target.extend(shlex.split(raw))
                        else:target.clear()
        if unit not in commands:raise ValueError('Installed command missing')
    cmd=commands[UNITS[0]]
    expected={'--workspace':WORKSPACE,'--state-dir':ROOT/'state','--config':ROOT/'config/node.toml','--workspace-entry-config':ROOT/'config/application-entry.toml'}
    for key,value in expected.items():
        if module.options(cmd,key)!=str(value):raise ValueError('NUC workspace scope changed: '+key)
    node=module.tomllib.loads(module.regular(expected['--config'],True))
    location=local_location(node,WORKSPACE)
    pairs=[]
    for word in bindings[UNITS[0]]:
        parts=word.replace('%%','%').removeprefix('-').split(':')
        if len(parts)>=2:pairs.append((parts[0],parts[1]))
    return {'workspace':WORKSPACE,'entry':expected['--workspace-entry-config'],'config':expected['--config'],'state':ROOT/'state','metadata':Path(module.options(cmd,'--metadata-dir') or ROOT/'state/metadata'),'controlSocket':Path(module.options(cmd,'--workspace-entry-dufs-socket')+'.directories'),'nodeId':node['node']['id'],'locationId':location['id'],'bindings':pairs,'unitBindings':bindings,'unitConditions':conditions}


class Adapter:
    def __init__(self,module,run=None):
        self.m=module;self.execute=run or module.Directories.execute;self.idle_only=False;self.restart_attempted=False
        self.d=module.Directories(run=self.run)
        self.d.state=Path.home()/'.local/state/tag-workspace-directories/nuc-private'
        self.control=Path.home()/'.local/share/dufs-plus/runtime/home/native-nuc-control.json'
        self.d.installation=lambda:installation(module,self.execute)

    def run(self,args):
        expected=[self.m.SYSTEMCTL,'--user','restart',*UNITS,'tag-native-workspace.service']
        if args==expected:
            if self.idle_only:raise IdleVerified()
            self.restart_attempted=True
            # The private file namespace must be ready before core reopens it.
            self.execute([self.m.SYSTEMCTL,'--user','restart',UNITS[1]])
            return self.execute([self.m.SYSTEMCTL,'--user','restart',UNITS[0]])
        return self.execute(args)

    def paths(self,i):return [i['entry'],self.d.state/'directories.json',*(self.d.units/(u+'.d')/self.m.MANAGED for u in UNITS),self.control]
    def snapshot(self,i):return {str(p):self.m.regular(p,True) if p.exists() or p.is_symlink() else None for p in self.paths(i)}

    def restore(self,receipt,*,restart=True):
        value=json.loads(self.m.regular(receipt,True));i=self.d.installation()
        if value.get('schema')!=1 or set(value['before'])!={str(p) for p in self.paths(i)}:raise ValueError('Backup scope changed')
        self.d.recover(i)
        after=value.get('after')
        if after is None and self.snapshot(i)!=value['before']:
            # Recover the completed helper commit if the outer receipt was interrupted.
            self.d.verify_owned(i)
            if self.d.registry()!=value['directories']:raise ValueError('Interrupted directory inventory changed')
            current_control=self.m.regular(self.control,True)
            before_control=value['before'][str(self.control)]
            expected_control=json.loads(before_control)
            expected_control['files'][str(i['entry'])]=hashlib.sha256(self.m.regular(i['entry'],True).encode()).hexdigest()
            if current_control!=before_control and json.loads(current_control)!=expected_control:
                raise ValueError('Startup control changed after interrupted configuration')
            after=self.snapshot(i)
        current=self.snapshot(i)
        for name,old in value['before'].items():
            if current[name] not in [old,(after or {}).get(name)]:raise ValueError('External configuration changed; refusing rollback')
        for name,old in value['before'].items():
            p=Path(name)
            if old is None:p.unlink(missing_ok=True)
            else:self.m.atomic(p,old)
        self.execute([self.m.SYSTEMCTL,'--user','daemon-reload'])
        if restart:
            self.execute([self.m.SYSTEMCTL,'--user','restart',UNITS[1]])
            self.execute([self.m.SYSTEMCTL,'--user','restart',UNITS[0]])
        value['phase']='rolled-back';self.m.atomic(receipt,json.dumps(value,ensure_ascii=False))
        return {'phase':'rolled-back','receipt':str(receipt),'data_restored':False}

    def bind_entry_hash(self,i,expected=None,previous_entry=None):
        text=self.m.regular(self.control,True)
        if expected is not None and text!=expected:raise ValueError('Startup control changed during directory transaction')
        value=json.loads(text)
        if value.get('root')!=str(ROOT) or value.get('hostname')!='nuc' or value.get('uid')!=1000:
            raise ValueError('Fixed native startup control required')
        files=value.get('files',{})
        if str(i['entry']) not in files:raise ValueError('Entry missing from startup binding')
        if previous_entry is not None and files[str(i['entry'])]!=hashlib.sha256(previous_entry.encode()).hexdigest():raise ValueError('Previous entry binding changed')
        files[str(i['entry'])]=hashlib.sha256(self.m.regular(i['entry'],True).encode()).hexdigest()
        self.m.atomic(self.control,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

    def apply(self,rows):
        i=self.d.installation();rows=self.d.validate(checked_rows(rows),i)
        self.idle_only=True
        try:self.d.apply()
        except IdleVerified:pass
        finally:self.idle_only=False
        self.restart_attempted=False
        receipt=self.d.state/('release-'+uuid.uuid4().hex+'.json')
        value={'schema':1,'phase':'prepared','before':self.snapshot(i),'after':None,'directories':rows}
        self.m.atomic(receipt,json.dumps(value,ensure_ascii=False))
        try:
            self.d.save(rows);self.bind_entry_hash(i,value['before'][str(self.control)],value['before'][str(i['entry'])]);value['after']=self.snapshot(i);value['phase']='configured';self.m.atomic(receipt,json.dumps(value,ensure_ascii=False))
            actual=self.d.apply();value['phase']='activated';self.m.atomic(receipt,json.dumps(value,ensure_ascii=False))
            return {'phase':'activated','receipt':str(receipt),'roots':len(rows),'unavailable':actual['unavailable'],'data_restored':False}
        except Exception:
            self.restore(receipt,restart=self.restart_attempted)
            raise


class IdleVerified(Exception):pass


def main():
    p=argparse.ArgumentParser();p.add_argument('--helper',required=True);p.add_argument('--helper-sha256',required=True)
    action=p.add_mutually_exclusive_group();action.add_argument('--apply',action='store_true');action.add_argument('--rollback',type=Path)
    p.add_argument('--inventory',type=Path);args=p.parse_args()
    if socket.gethostname()!='nuc' or os.getuid()!=1000:raise ValueError('Fixed nuc/liou scope required')
    m=load_helper(args.helper,args.helper_sha256);adapter=Adapter(m)
    if args.rollback:
        if args.rollback.parent!=adapter.d.state:raise ValueError('Rollback receipt outside owned state')
        with adapter.d.lock():result=adapter.restore(args.rollback)
    else:
        if not args.inventory:raise ValueError('Inventory required')
        rows=checked_rows(json.loads(m.regular(args.inventory,True))['roots']);i=adapter.d.installation();adapter.d.validate(rows,i)
        if args.apply:
            with adapter.d.lock():result=adapter.apply(rows)
        else:result={'activated':False,'roots':len(rows),'legacy_prefixes_preserved':True,'can_apply':adapter.d.inspect()['canApply']}
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
