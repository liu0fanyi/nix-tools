#!/usr/bin/env bash
set -euo pipefail
cd /home/liou/nix-tools
test "$(hostname)" = liu-bigpc
test "$(id -u)" = 1000
export TAG_PODMAN_URL=unix:///run/user/1000/podman/podman.sock
native_state=/home/liou/.local/share/tag-all/pc-native
test ! -e "$native_state"
test ! -L "$native_state"
python3 - <<'PY'
import json,pathlib,subprocess
repo=pathlib.Path.cwd()
r=json.loads((repo/'specs/012-native-core-gateway/native-final-combination-results.json').read_text())
assert r['cutover_ready'] and pathlib.Path(r['actual_toplevel']).is_dir()
s=pathlib.Path(r['actual_host_source_snapshot'])
for f in subprocess.check_output(['git','ls-files','-z']).decode().split('\0'):
    if f and (f.endswith('.nix') or f=='flake.lock'):
        a,b=repo/f,s/f
        assert a.exists()==b.exists() and (not a.exists() or a.read_bytes()==b.read_bytes()), 'Candidate is stale: '+f
print('Fixed liu-bigpc candidate and current configuration match.')
import re
podman=['podman','--remote','--url','unix:///run/user/1000/podman/podman.sock']
records=json.loads(subprocess.check_output(podman+['inspect','dufs-plus-pc_caddy_1','dufs-plus-pc_dufs_1']))
for record in records:
    assert record['Config']['Labels'].get('io.podman.compose.project')=='dufs-plus-pc'
    if record['Name'].endswith('caddy_1'):
        source=next(x['Source'] for x in record['Mounts'] if x['Destination']=='/etc/caddy/Caddyfile')
        assert not re.search(r'\b(?:basic_auth|basicauth|import)\b',pathlib.Path(source).read_text()), 'Auth changed; do not stop services'
    else:
        assert not any(x in {'-a','--auth'} or x.startswith(('--auth=','-a=')) for x in record['Config']['Cmd']), 'DUFS auth changed'
PY
sudo -v
system_before=$(readlink -f /run/current-system)
profile_before=$(readlink -f /nix/var/nix/profiles/system)
candidate_system=$(python3 -c 'import json; print(json.load(open("specs/012-native-core-gateway/native-final-combination-results.json"))["actual_toplevel"])')
trap 'printf "Switch stopped. Do not restart old containers after native writes. Keep the snapshot and report this failure.\n" >&2' ERR
# The old oneshot may own conmon processes. Change only its stop behavior before
# stopping it; otherwise systemd kills the container monitors with its cgroup.
stop_override=/run/user/1000/systemd/user/pc-private-node-restore.service.d
mkdir -p "$stop_override"
test ! -e "$stop_override/native-cutover-stop.conf"
printf '[Service]\nKillMode=process\n' > "$stop_override/native-cutover-stop.conf"
systemctl --user daemon-reload
systemctl --user stop pc-private-node-restore.service
systemctl --user reset-failed pc-private-node-restore.service
python3 - <<'PY'
import json,subprocess
p=['podman','--remote','--url','unix:///run/user/1000/podman/podman.sock']
names=['dufs-plus-pc_caddy_1','dufs-plus-pc_peer-gateway_1','dufs-plus-pc_peer-discovery_1','dufs-plus-pc_tag-server_1','dufs-plus-pc_dufs_1']
subprocess.run(p+['stop']+names,check=False)
records=json.loads(subprocess.check_output(p+['inspect']+names))
assert len(records)==5
assert all(x['Config']['Labels'].get('io.podman.compose.project')=='dufs-plus-pc' and not x['State']['Running'] and x['State']['Status'] in {'exited','stopped','created'} for x in records), 'Not all old containers stopped; migration refused'
PY
rm -- "$stop_override/native-cutover-stop.conf"
systemctl --user daemon-reload
python3 scripts/native-pc-cutover.py --prepare-offline
python3 scripts/native_pc_mode_guard.py --mode native
# The pinned static backend cannot use host NSS mDNS. Keep the old explicit
# container aliases only inside its mount namespace; never edit global hosts.
network_override=/home/liou/.config/systemd/user/tag-all-core.service.d
mkdir -p "$network_override"
test ! -e "$network_override/native-cutover-hosts.conf"
printf '[Service]\nBindReadOnlyPaths=%s/config/hosts:/etc/hosts\n' "$native_state" > "$network_override/native-cutover-hosts.conf"
chmod 644 "$network_override/native-cutover-hosts.conf"
systemctl --user daemon-reload
umask 077
printf '%s\n' "$system_before" > "$native_state/config/system-before-cutover"
printf '%s\n' "$profile_before" > "$native_state/config/profile-before-cutover"
nix-store --add-root "$native_state/config/system-before-gc-root" --indirect --realise "$system_before"
nix-store --add-root "$native_state/config/profile-before-gc-root" --indirect --realise "$profile_before"
sudo nix-env -p /nix/var/nix/profiles/system --set "$candidate_system"
sudo "$candidate_system/bin/switch-to-configuration" switch
python3 scripts/native-pc-register.py
systemctl --user start tag-native-stack.target
for unit in tag-native-stack.target tag-all-core.service tag-native-files.service tag-native-workspace.service tag-all-tools.service; do
  systemctl --user is-active "$unit"
done
printf '\nNative PC candidate activated. Return to the chat for live service verification.\n'
