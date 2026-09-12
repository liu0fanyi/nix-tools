#!/usr/bin/env python3
"""Mirror this repository's specs and documentation to its fixed NUC directory."""
from pathlib import Path
import argparse
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'nix-tools'
REMOTE_HOST = 'liou@nuc.local'
REMOTE_DIR = '/home/liou/dufs-lan/todos/' + PROJECT


def task_counts(path):
    done = total = 0
    fence = None
    for line in path.read_text().splitlines() if path.is_file() else []:
        match = re.match(r'^\s*(`{3,}|~{3,})', line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        match = re.match(r'^\s*[-*+]\s+\[([ xX])\]\s+', line)
        if fence is None and match:
            total += 1
            done += match[1].lower() == 'x'
    return done, total


def render():
    lines = [f'# {PROJECT} 规格与进度', '',
             '> 本地仓库为权威源；由 just sync-todos 生成，远端勿手工编辑。任务勾选不等于部署或实机验收。', '',
             '| 特性 | 任务 | 规格 | 方案 |', '| --- | --- | --- | --- |']
    for directory in sorted((ROOT / 'specs').iterdir()):
        if not directory.is_dir() or not (directory / 'spec.md').is_file():
            continue
        title = next((line[2:].strip() for line in (directory / 'spec.md').read_text().splitlines()
                      if line.startswith('# ')), directory.name).replace('|', '\\|')
        done, total = task_counts(directory / 'tasks.md')
        base = 'specs/' + directory.name
        tasks = f'[{done}/{total}]({base}/tasks.md)' if (directory / 'tasks.md').is_file() else '未建任务清单'
        plan = f'[plan]({base}/plan.md)' if (directory / 'plan.md').is_file() else '—'
        lines.append(f'| {title} | {tasks} | [spec]({base}/spec.md) | {plan} |')
    lines.extend(['', '- [项目宪法](.specify/memory/constitution.md)'])
    if (ROOT / 'README.md').is_file():
        lines.append('- [仓库操作入口](repository-readme.md)（源码相对链接请在仓库中查阅）')
    if (ROOT / 'AGENTS.md').is_file():
        lines.append('- [工程操作规则](AGENTS.md)')
    for doc in sorted((ROOT / 'docs').rglob('*.md')) if (ROOT / 'docs').is_dir() else []:
        rel = doc.relative_to(ROOT).as_posix()
        lines.append(f'- [{doc.stem}]({rel})')
    for doc in sorted((ROOT / 'deploy/docs').rglob('*.md')):
        rel = 'docs/' + doc.relative_to(ROOT / 'deploy/docs').as_posix()
        lines.append(f'- [{doc.stem}]({rel})')
    return '\n'.join(lines) + '\n'


def transfers(readme):
    pairs = [(ROOT / 'specs', REMOTE_DIR + '/specs/', True),
             (ROOT / '.specify/memory/constitution.md', REMOTE_DIR + '/.specify/memory/constitution.md', False),
             (readme, REMOTE_DIR + '/README.md', False)]
    for name, target in [('docs', 'docs/'), ('deploy/docs', 'docs/'), ('README.md', 'repository-readme.md'), ('AGENTS.md', 'AGENTS.md')]:
        if (ROOT / name).exists():
            pairs.append((ROOT / name, REMOTE_DIR + '/' + target, False))
    return pairs


def command(source, destination, delete=False, verify=False):
    # docs/ and deploy/docs/ share a destination; directory mtimes are not content.
    cmd = ['rsync', '-rptz', '--omit-dir-times', '--checksum', '--chmod=D755,F644']
    if delete:
        cmd.append('--delete')
    if verify:
        cmd += ['--dry-run', '--itemize-changes']
    return cmd + [str(source) + ('/' if source.is_dir() else ''), REMOTE_HOST + ':' + destination]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Render and print commands locally; no network writes')
    args = parser.parse_args()
    if not (ROOT / 'specs').is_dir() or not (ROOT / '.specify/memory/constitution.md').is_file():
        parser.error('specs/ and constitution are required')
    for doc in (ROOT / 'deploy/docs').rglob('*'):
        if doc.is_file() and (ROOT / 'docs' / doc.relative_to(ROOT / 'deploy/docs')).exists():
            parser.error('duplicate docs mirror path: ' + str(doc))
    with tempfile.TemporaryDirectory(prefix='spec-mirror-') as temp:
        readme = Path(temp) / 'README.md'
        readme.write_text(render())
        pairs = transfers(readme)
        # Refuse symlink sources: never publish files outside owned source directories.
        for source, _, _ in pairs:
            if source.is_symlink() or (source.is_dir() and any(p.is_symlink() for p in source.rglob('*'))):
                parser.error('symlink source is not supported: ' + str(source))
        mkdir = ['ssh', REMOTE_HOST, 'mkdir -p ' + shlex.quote(REMOTE_DIR + '/specs') + ' ' + shlex.quote(REMOTE_DIR + '/docs') + ' ' + shlex.quote(REMOTE_DIR + '/.specify/memory')]
        commands = [mkdir] + [command(*pair) for pair in pairs]
        if args.dry_run:
            print(readme.read_text())
            for cmd in commands:
                print(shlex.join(cmd))
            return
        for cmd in commands:
            subprocess.run(cmd, check=True)
        for pair in pairs:
            result = subprocess.run(command(*pair, verify=True), text=True, capture_output=True, check=True)
            if result.stdout.strip():
                raise RuntimeError('Mirror mismatch: ' + result.stdout)
        print('Verified specs, constitution, documentation and dashboard: ' + REMOTE_DIR)


if __name__ == '__main__':
    main()
