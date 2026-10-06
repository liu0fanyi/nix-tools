#!/usr/bin/env python3
"""Build and inspect a synthetic Home Manager generation; never activate it."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=300)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag_all', type=Path)
    parser.add_argument('dufs_plus', type=Path)
    args = parser.parse_args()
    expression = 'import ' + str(ROOT / 'tests/native-stack-install.nix') + ' { infrastructure = ' + json.dumps(str(ROOT))
    expression += '; tagAll = ' + json.dumps(str(args.tag_all.resolve()))
    expression += '; dufsPlus = ' + json.dumps(str(args.dufs_plus.resolve())) + '; '
    output = ROOT / '.devenv/native-install-results.json'
    output.parent.mkdir(exist_ok=True)
    output.unlink(missing_ok=True)
    disabled = json.loads(run(['nix', 'eval', '--impure', '--json', '--expr', '(' + expression + 'enabled = false; }).services']))
    assert not any(name in disabled for name in ['tag-all-core', 'tag-native-files', 'tag-native-workspace'])
    assertions = json.loads(run(['nix', 'eval', '--impure', '--json', '--expr', '(' + expression + 'enabled = true; }).assertions']))
    assert all(assertions)
    generation = Path(run(['nix-build', '--no-out-link', '-A', 'generation', '--expr', expression + 'enabled = true; }']))
    unit_root = generation / 'home-files/.config/systemd/user'
    units = {name: (unit_root / (name + '.service')).read_text()
             for name in ['tag-all-core', 'tag-native-files', 'tag-native-workspace']}
    native = json.loads((args.tag_all / '.devenv/native-core-results.json').read_text())
    assert native['package'] + '/bin/tag-all-core' in units['tag-all-core']
    assert 'WantedBy=default.target' in units['tag-all-core'] and 'WantedBy=default.target' in units['tag-native-workspace']
    for upstream in ['tag-all-core', 'tag-native-files']:
        assert 'Requires=' + upstream + '.service' in units['tag-native-workspace']
    assert 'work space %% $$ 中文' in units['tag-all-core'] and 'work space %% $$ 中文' in units['tag-native-files']
    assert '--bind /tmp/nativecheck/.local/share/tag-all/native-workspace/files.sock' in units['tag-native-files']
    for text in units.values():
        assert 'PrivateTmp=true' in text and 'NoNewPrivileges=true' in text and 'UMask=0077' in text
    report = {'generation': str(generation), 'default_disabled': True, 'enabled_assertions': True,
              'core_package': native['package'], 'all_three_units_built': True, 'dependencies_and_default_target': True,
              'private_socket_and_parameter_escaping': True,
              'unit_sha256': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in units.items()},
              'activated': False, 'real_login_boot_tested': False}
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Native combination installation generation verified, not activated: ' + str(output))


if __name__ == '__main__':
    main()
