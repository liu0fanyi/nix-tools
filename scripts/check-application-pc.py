#!/usr/bin/env python3
"""Build full PC application candidate and owned gates without activation."""
import sys, hashlib, subprocess, tarfile, tempfile, shutil, json
from pathlib import Path
r = Path(__file__).resolve().parents[1]
tag = Path(sys.argv[1]).resolve()
dufs = Path(sys.argv[2]).resolve()
d = tag / '.devenv'
snapshot = Path(tempfile.mkdtemp(prefix='tag-entry-pc-candidate-'))
p = subprocess.run(['git', 'archive', 'HEAD'], cwd=r, stdout=subprocess.PIPE, check=True)
import io
with tarfile.open(fileobj=io.BytesIO(p.stdout)) as archive:
    archive.extractall(snapshot, filter='data')
owned = ['home-manager/native-stack.nix', 'home-manager/native-workspace.nix', 'packages/native-workspace.nix', 'packages/native-peer-site.nix', 'nixos/modules/native-pc-candidate.nix', 'tests/native-pc-host.nix']
for path in owned:
    shutil.copyfile(r / path, snapshot / path)
shutil.copyfile(r / 'flake.lock', snapshot / 'flake.lock')
proof = json.loads((tag / '.devenv/application-entry-package-results.json').read_text())
for path, digest in proof['source_manifest'].items():
    assert hashlib.sha256((tag / path).read_bytes()).hexdigest() == digest, path
(d / 'application-entry-pc-source-path').write_text(str(snapshot) + '\n')
expr = 'import (builtins.toPath ' + json.dumps(str(snapshot / 'tests/native-pc-host.nix')) + ') { infrastructure = ' + json.dumps(str(snapshot)) + '; hostSource = ' + json.dumps(str(snapshot)) + '; tagAll = ' + json.dumps(str(tag)) + '; dufsPlus = ' + json.dumps(str(dufs)) + '; processing = true; applicationEntry = true; }'
(d / 'application-entry-pc-expression.nix').write_text(expr + '\n')

def run(args, name):
    with (d / (name + '.log')).open('w') as log:
        p = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        print((d / (name + '.log')).read_text()[-10000:])
        raise SystemExit(p.returncode)
    print(name + ' passed', flush=True)
    return (d / (name + '.log')).read_text()
meta = run(['nix', 'eval', '--impure', '--json', '--expr', 'let c = (' + expr + '); in { inherit (c) hostname nativePackage homeBackupExtension entryConfiguration processingSelection toolRuntimeSelection target; services = builtins.listToAttrs (map (name: { inherit name; value = c.services.${name}; }) [ "tag-all-core" "tag-all-tools" "tag-native-files" "tag-native-workspace" "pc-private-node-restore" ]); }'], 'application-entry-pc-evaluation')
(d / 'application-entry-pc-evaluation.json').write_text(meta)
for attr in ['toplevel', 'home']:
    run(['nix-build', '--impure', '--expr', expr, '-A', attr, '--out-link', str(d / ('application-entry-pc-' + attr))], 'application-entry-pc-' + attr)
print('Candidate system and HM built. No activation.', flush=True)
m = json.loads(meta)
core = m['services']['tag-all-core']
tls = m['services']['tag-native-workspace']
files = m['services']['tag-native-files']
assert '--addr 127.0.0.1:5006' in core['Service']['ExecStart'][0]
assert '--workspace-entry-config ' in core['Service']['ExecStart'][0]
assert 'tag-native-files.service' in core['Unit']['Requires']
assert 'tag-native-workspace.service' not in core['Unit'].get('Requires', []) + core['Unit'].get('BindsTo', [])
assert tls['Unit']['Description'] == 'Private peer TLS transport'
assert 'EnvironmentFile' not in tls['Service']
assert len(tls['Service']['ExecStartPre']) == 1
assert '--mode native' in core['Service']['ExecCondition']
assert '--mode container' in m['services']['pc-private-node-restore']['Service']['ExecCondition']
assert 'KillMode' in m['services']['pc-private-node-restore']['Service']
run([sys.executable, str(r / 'scripts/check-native-pc-guard-runtime.py'), '--generation', str(d / 'application-entry-pc-home'), '--output', str(d / 'application-entry-pc-guard-results.json')], 'application-entry-pc-guard')
run([sys.executable, str(r / 'scripts/check-application-pc-runtime.py'), str(d / 'application-entry-pc-evaluation.json'), str(tag / '.devenv/application-entry-package-results.json')], 'application-entry-pc-runtime')
legacy = 'import (builtins.toPath ' + json.dumps(str(snapshot / 'tests/native-stack-install.nix')) + ') { infrastructure=' + json.dumps(str(snapshot)) + '; tagAll=' + json.dumps(str(tag)) + '; dufsPlus=' + json.dumps(str(dufs)) + '; }'
run(['nix-build', '--impure', '--expr', legacy, '-A', 'generation', '--out-link', str(d / 'application-entry-pc-legacy-home')], 'application-entry-pc-legacy-home')
result = {'stage': 'E3.b', 'toplevel': str((d / 'application-entry-pc-toplevel').resolve()), 'home': str((d / 'application-entry-pc-home').resolve()), 'legacy_home': str((d / 'application-entry-pc-legacy-home').resolve()), 'package': m['nativePackage'], 'runtime': json.loads((d / 'application-entry-pc-runtime-results.json').read_text()), 'guard': json.loads((d / 'application-entry-pc-guard-results.json').read_text()), 'candidate_dependencies_and_units_checked': True, 'source_manifest': {path: hashlib.sha256((r / path).read_bytes()).hexdigest() for path in owned}, 'host_lock_sha256': hashlib.sha256((r / 'flake.lock').read_bytes()).hexdigest(), 'host_lock_is_readonly_current_worktree_input': True, 'unrelated_dirty_source_excluded': True, 'activated': False, 'production_database_access': False}
(d / 'application-entry-pc-results.json').write_text(json.dumps(result, indent=2) + '\n')
shutil.rmtree(snapshot)
print('E3.b candidate gates passed; no activation', flush=True)
