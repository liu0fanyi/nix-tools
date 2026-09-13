#!/usr/bin/env python3
"""Read, validate, and compare-before-write DUFS work Markdown. No credentials stored."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path('/home/liou/dufs-lan/todos')
BACKUPS = Path('/home/liou/dufs-lan/todos/project-planner/work-file-backups')
PARSER = Path('/data/project/bevy-env/bevy-project-planner/markdown-project.mjs')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(text):
    headings = []
    fence = None
    for line in text.splitlines():
        m = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if m:
            mark = m[1]
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence):
                fence = None
            continue
        if fence is None and re.match(r'^#{1,2} ', line):
            headings.append(line.rstrip())
    if fence:
        raise ValueError('Unclosed code fence')
    if len([h for h in headings if h.startswith('# ')]) != 1:
        raise ValueError('Use exactly one level-one project title; demote historical titles')
    required = ['## 现在怎样', '## 卡在哪', '## 下一步', '## 记录']
    for h in required:
        if headings.count(h) != 1:
            raise ValueError('Require exactly one ' + h)
    warnings = []
    if len(text.splitlines()) > 400 or len(text.encode()) > 65536:
        warnings.append('Long file: consider moving old records to an archive outside the discovery directory, preserving links')
    return warnings


def target(root, filename):
    parts = Path(filename).parts
    if len(parts) < 2 or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', part) or '..' in part for part in parts):
        raise ValueError('Use project/plan.md or project/docs/name.md')
    if not (len(parts) == 2 and parts[1] == 'plan.md') and not (len(parts) >= 3 and parts[1] == 'docs' and parts[-1].endswith('.md')):
        raise ValueError('Expected plan.md or a Markdown document under docs/')
    path = root / filename
    if any((root.joinpath(*parts[:i])).is_symlink() for i in range(1,len(parts)+1)) or not path.is_file():
        raise ValueError('Expected an existing regular file without symlink ancestors')
    return path


def update(root, backups, filename, content, expected):
    warnings = validate(content) if filename.endswith("/plan.md") else []
    path = target(root, filename)
    data = content.encode('utf-8')
    # This serializes this helper only; browser and arbitrary SSH writers do not share the lock.
    lock = path.parent / ('.' + path.name + '.work-progress.lock')
    with lock.open('a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        current = path.read_bytes()
        if sha(current) != expected:
            raise ValueError('CONFLICT: reread latest content and merge; do not retry an old candidate')
        if current == data:
            return {'changed': False, 'sha256': expected, 'warnings': warnings}
        backups.mkdir(parents=True, exist_ok=True)
        backup = backups / (filename.replace('/', '__') + '.' + expected + '.bak')
        try:
            with backup.open('xb') as out:
                out.write(current)
        except FileExistsError:
            if backup.read_bytes() != current:
                raise ValueError('Backup collision')
        descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(descriptor, 'wb') as out:
                os.fchmod(out.fileno(), path.stat().st_mode & 0o777)
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            if path.is_symlink() or sha(path.read_bytes()) != expected:
                raise ValueError('CONFLICT: source changed during write preparation')
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        actual = sha(path.read_bytes())
        if actual != sha(data):
            raise ValueError('Post-write mismatch: reread before any further action')
        return {'changed': True, 'sha256': actual, 'backup': str(backup), 'warnings': warnings}


def remote(payload):
    filename = payload['filename']
    path = target(ROOT, filename)
    if payload['operation'] == 'read':
        data = path.read_bytes()
        return {'filename': filename, 'sha256': sha(data), 'content': data.decode('utf-8')}
    if payload['operation'] == 'update':
        return update(ROOT, BACKUPS, filename, payload['content'], payload['expected'])
    raise ValueError('Unknown operation')


def check(candidate):
    text = Path(candidate).read_text()
    warnings = validate(text)
    # Use the actual UI parser, not a second implementation of task semantics.
    js = '''import {readFileSync} from 'node:fs';
const {parsePlainProject}=await import(process.argv[1]);
const p=parsePlainProject(readFileSync(process.argv[2],'utf8'));
console.log(JSON.stringify({title:p.meta.title,current:p.current,blocker:p.blocker,next:p.next,tasks:p.taskItems.map(t=>({title:t.title,done:t.stateKey==='done'}))}));'''
    result = subprocess.run(['node', '--input-type=module', '-e', js, str(PARSER), str(Path(candidate).resolve())], check=True, capture_output=True, text=True)
    parsed = json.loads(result.stdout)
    parsed['warnings'] = warnings
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['read', 'check', 'update'])
    parser.add_argument('filename', help='project/plan.md or project/docs/name.md; local candidate for check')
    parser.add_argument('--candidate')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args()
    if args.operation == 'check':
        result = check(args.filename)
    else:
        payload = {'operation': args.operation, 'filename': args.filename}
        if args.operation == 'update':
            if not args.candidate or not re.fullmatch('[0-9a-f]{64}', args.expected_sha256 or ''):
                parser.error('update needs --candidate and --expected-sha256 from read')
            if args.filename.endswith("/plan.md"):
                check(args.candidate)
            payload.update(content=Path(args.candidate).read_text(), expected=args.expected_sha256)
        # Source + a JSON string literal travel as stdin; no interpolated shell commands.
        source = Path(__file__).read_text().rsplit("if __name__ == '__main__':", 1)[0]
        source += '\nprint(json.dumps(remote(json.loads(' + repr(json.dumps(payload, ensure_ascii=False)) + ')),ensure_ascii=False))\n'
        result = json.loads(subprocess.run(['ssh', 'liou@nuc.local', 'python3 -'], input=source, capture_output=True, text=True, check=True).stdout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.stderr or str(error))
    except ValueError as error:
        sys.exit(str(error))
