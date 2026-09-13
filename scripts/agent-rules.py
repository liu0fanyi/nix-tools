#!/usr/bin/env python3
"""Link versioned local agent rules; refuse to overwrite divergent local files."""
from pathlib import Path
import argparse
import os

ROOT = Path(__file__).resolve().parents[1]


def rules(root=ROOT, home=None, workspace=Path('/data/project')):
    home = Path.home() if home is None else home
    base = root / 'config/agent-rules'
    pairs = [(base / 'project/AGENTS.md', workspace / 'AGENTS.md')]
    for name in ['SKILL.md', 'agents/openai.yaml', 'scripts/work_file.py']:
        pairs.append((base / 'skills/work-progress' / name,
                      home / '.codex/skills/work-progress' / name))
    return pairs


def inspect(pairs):
    pending = []
    for source, target in pairs:
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Missing regular source: {source}')
        if any(parent.is_symlink() for parent in target.parents):
            raise ValueError(f'Symlink parent requires manual inspection: {target}')
        if target.is_symlink():
            if target.resolve() != source.resolve():
                raise ValueError(f'Different symlink preserved: {target}')
        elif target.exists():
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                raise ValueError(f'Different local content preserved: {target}')
            pending.append((source, target))
        else:
            pending.append((source, target))
    return pending


def install(pairs, apply=False, check=False):
    pending = inspect(pairs)  # Check every target before changing any file.
    if check and pending:
        raise ValueError('Not installed: ' + ', '.join(str(t) for _, t in pending))
    for source, target in pending:
        print(f'{target} -> {source}')
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive staging name: do not replace another process\'s temporary file.
            temporary = target.with_name(target.name + '.agent-rules-link')
            temporary.symlink_to(source)
            try:
                inspect([(source, target)])
                os.replace(temporary, target)
            finally:
                if temporary.is_symlink():
                    temporary.unlink()
    if apply or check:
        if inspect(pairs):
            raise ValueError('Link verification failed')
        print('All managed rule links verified')
    elif not pending:
        print('All managed rule links already installed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true')
    group.add_argument('--check', action='store_true')
    group.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        install(rules(), apply=args.apply, check=args.check)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
