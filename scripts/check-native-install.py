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
    invalid = subprocess.run(['nix', 'eval', '--impure', '--json', '--expr', '(' + expression + 'workspaceMounts = { "../escape" = "/tmp/source"; }; }).assertions'], capture_output=True, text=True, timeout=300)
    assert invalid.returncode != 0 and 'Native workspace mappings require' in invalid.stderr, 'Reject escaping workspace target before activation'
    generation = Path(run(['nix-build', '--no-out-link', '-A', 'generation', '--expr', expression + 'enabled = true; }']))
    unit_root = generation / 'home-files/.config/systemd/user'
    units = {name: (unit_root / (name + '.service')).read_text()
             for name in ['tag-all-core', 'tag-native-files', 'tag-native-workspace']}
    native = json.loads((args.tag_all / '.devenv/native-core-results.json').read_text())
    assert native['package'] + '/bin/tag-all-core' in units['tag-all-core']
    target_unit = (unit_root / 'tag-native-stack.target').read_text()
    assert 'WantedBy=default.target' in target_unit
    assert 'Upholds=tag-all-core.service' in target_unit
    for text in units.values():
        assert 'PartOf=tag-native-stack.target' in text and 'WantedBy=default.target' not in text
    for upstream in ['tag-all-core', 'tag-native-files']:
        assert 'Requires=' + upstream + '.service' in units['tag-native-workspace']
    assert 'work space %% $$ 中文' in units['tag-all-core'] and 'work space %% $$ 中文' in units['tag-native-files']
    assert '--bind /tmp/nativecheck/.local/share/tag-all/native-workspace/files.sock' in units['tag-native-files']
    for text in units.values():
        assert 'PrivateTmp=true' in text and 'NoNewPrivileges=true' in text and 'UMask=0077' in text
    configured_assertions = json.loads(run(['nix', 'eval', '--impure', '--json', '--expr', '(' + expression + 'configured = true; }).assertions']))
    assert all(configured_assertions)
    configured_generation = Path(run(['nix-build', '--no-out-link', '-A', 'generation', '--expr', expression + 'configured = true; }']))
    configured_unit = (configured_generation / 'home-files/.config/systemd/user/tag-all-core.service').read_text()
    assert '--sync-mode configured' in configured_unit and "--config '/tmp/nativecheck/runtime node.toml'" in configured_unit
    assert "EnvironmentFile='/tmp/nativecheck/private auth %% $ 中文.env'" in configured_unit
    assert 'native-core-environment-check' in configured_unit
    peer_generation = Path(run(['nix-build', '--no-out-link', '-A', 'generation', '--expr', expression + 'configured = true; peerEnabled = true; }']))
    peer_unit = (peer_generation / 'home-files/.config/systemd/user/tag-native-workspace.service').read_text()
    assert 'native-peer-tls-check' in peer_unit
    rejected_peer = subprocess.run(['nix', 'eval', '--impure', '--json', '--expr', '(' + expression + 'peerEnabled = true; }).assertions'], capture_output=True, text=True, timeout=300)
    assert rejected_peer.returncode and 'requires explicit configured core mode' in rejected_peer.stderr
    colliding_peer = subprocess.run(['nix', 'eval', '--impure', '--json', '--expr', '(' + expression + 'configured = true; peerEnabled = true; peerPort = 18006; }).assertions'], capture_output=True, text=True, timeout=300)
    assert colliding_peer.returncode and 'requires a separate TLS port' in colliding_peer.stderr
    report = {'generation': str(generation), 'default_disabled': True, 'enabled_assertions': True,
              'core_package': native['package'], 'all_three_units_built': True, 'dependencies_and_default_target': True,
              'private_socket_and_parameter_escaping': True,
              'unit_sha256': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in units.items()},
              'configured_generation': str(configured_generation), 'configured_runtime_paths_only': True,
              'environment_path_escaping': True, 'escaping_mapping_rejected': True,
              'whole_stack_target_is_autostart_owner': True,
              'peer_generation': str(peer_generation), 'configured_peer_tls_unit_and_negative_gates': True,
              'activated': False, 'real_login_boot_tested': False}
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Native combination installation generation verified, not activated: ' + str(output))


if __name__ == '__main__':
    main()
