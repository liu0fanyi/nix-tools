#!/usr/bin/env bash
# 重装/部署后的可重复验收脚本。
set -euo pipefail

target="${NIXOS_VERIFY_TARGET:-${NIXOS_ANYWHERE_TARGET:-${NIXOS_ANYWHERE_SSH_USER:-root}@${NIXOS_ANYWHERE_SSH_HOST:-192.168.1.6}}}"
profile="${NIXOS_VERIFY_PROFILE:-reinstalled}"
strict="0"

usage() {
  cat <<EOF
用法：
  $0 [--target root@host] [--profile current|reinstalled] [--strict]

current      验证旧系统的 16G swapfile 和 pool-root resume
reinstalled  验证当前全新安装的 swap tier、pool-swap LV 和独立 resume（默认）
--strict     将缺少 secrets/运行时配置的警告也视为失败
EOF
}

while (($# > 0)); do
  case "$1" in
    --target)
      target="$2"
      shift 2
      ;;
    --profile)
      profile="$2"
      shift 2
      ;;
    --strict)
      strict="1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$profile" in
  current|reinstalled)
    ;;
  *)
    echo "--profile 必须是 current 或 reinstalled。" >&2
    exit 2
    ;;
esac

exec ssh -o BatchMode=yes -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
  "$target" bash -s -- "$profile" "$strict" <<'REMOTE'
set -u

profile="$1"
strict="$2"
failures=0
warnings=0

pass() {
  printf '[PASS] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1"
  failures=$((failures + 1))
}

warn() {
  printf '[WARN] %s\n' "$1"
  warnings=$((warnings + 1))
  if [ "$strict" = 1 ]; then
    failures=$((failures + 1))
  fi
}

check_file() {
  if [ -f "$1" ]; then
    pass "文件存在：$1"
  else
    fail "文件缺失：$1"
  fi
}

check_marker() {
  if grep -Fq -- "$2" "$1" 2>/dev/null; then
    pass "$3"
  else
    fail "$3"
  fi
}

echo "== homebox 自动验收（profile=$profile） =="

if [ "$(hostname)" = homebox ]; then
  pass "hostname=homebox"
else
  fail "hostname 不是 homebox：$(hostname)"
fi

if [ -e /run/current-system ]; then
  pass "当前 NixOS generation 存在：$(readlink -f /run/current-system)"
else
  fail "缺少 /run/current-system"
fi

if command -v nixos-version >/dev/null 2>&1; then
  pass "$(nixos-version)"
else
  fail "找不到 nixos-version"
fi

for unit in NetworkManager systemd-logind sshd; do
  if systemctl is-active --quiet "$unit"; then
    pass "服务 active：$unit"
  else
    fail "服务非 active：$unit"
  fi
done

if ip route show default | grep -q '^default '; then
  pass "存在默认网络路由"
else
  fail "缺少默认网络路由"
fi

if mountpoint -q /boot; then
  pass "/boot 已挂载"
else
  fail "/boot 未挂载"
fi

if [ "$profile" = reinstalled ]; then
  if [ -e /sys/firmware/efi/efivars/BootOrder-* ] &&
     [ -f /boot/EFI/NixOS-boot/grubx64.efi ]; then
    pass "UEFI NixOS-boot 启动文件和 NVRAM 环境存在"
  else
    fail "缺少 UEFI NixOS-boot 启动文件或 NVRAM 环境"
  fi
fi

if findmnt -n -o FSTYPE / | grep -qx ext4; then
  pass "根文件系统为 ext4"
else
  fail "根文件系统不是预期的 ext4"
fi

mem_kib="$(awk '/^MemTotal:/ { print $2; exit }' /proc/meminfo)"
swap_rows="$(swapon --show=NAME,SIZE --noheadings --bytes 2>/dev/null || true)"
swap_bytes="$(awk '{ total += $2 } END { print total + 0 }' <<<"$swap_rows")"
if [ "$swap_bytes" -ge $((mem_kib * 1024)) ]; then
  pass "磁盘 swap 不小于内存：${swap_bytes} bytes"
else
  fail "磁盘 swap 小于内存：${swap_bytes} < $((mem_kib * 1024)) bytes"
fi

kernel_params=""
if [ -f /run/current-system/kernel-params ]; then
  kernel_params="$(cat /run/current-system/kernel-params)"
else
  fail "缺少 /run/current-system/kernel-params"
fi

case "$profile" in
  current)
    if grep -Fq '/var/lib/swapfile' <<<"$swap_rows"; then
      pass "当前使用 /var/lib/swapfile"
    else
      fail "当前未发现 /var/lib/swapfile"
    fi
    if grep -Fq 'resume=/dev/mapper/pool-root' <<<"$kernel_params"; then
      pass "resume device=pool-root"
    else
      fail "缺少 pool-root resume 参数"
    fi
    if grep -Fq 'resume_offset=' <<<"$kernel_params"; then
      pass "存在 swapfile resume_offset"
    else
      fail "缺少 swapfile resume_offset"
    fi
    ;;
  reinstalled)
    pool_swap_device=""
    if [ -e /dev/mapper/pool-swap ]; then
      pool_swap_device="$(readlink -f /dev/mapper/pool-swap)"
    fi
    pool_swap_active="0"
    while read -r swap_name _; do
      [ -n "$swap_name" ] || continue
      if [ -n "$pool_swap_device" ] &&
         [ "$(readlink -f "$swap_name" 2>/dev/null || true)" = "$pool_swap_device" ]; then
        pool_swap_active="1"
        break
      fi
    done <<<"$(swapon --show=NAME --noheadings 2>/dev/null || true)"
    if [ "$pool_swap_active" = 1 ]; then
      pass "发现独立 pool-swap LV"
    else
      fail "未发现独立 pool-swap LV"
    fi
    if grep -Fq 'resume=/dev/mapper/pool-swap' <<<"$kernel_params"; then
      pass "resume device=pool-swap"
    else
      fail "缺少 pool-swap resume 参数"
    fi
    if grep -Fq 'resume_offset=' <<<"$kernel_params"; then
      fail "独立 swap LV 不应存在 resume_offset"
    else
      pass "独立 swap LV 未使用 resume_offset"
    fi
    ;;
esac

logind_config="$(systemd-analyze cat-config systemd/logind.conf 2>/dev/null || true)"
sleep_config="$(systemd-analyze cat-config systemd/sleep.conf 2>/dev/null || true)"
check_marker <(printf '%s\n' "$logind_config") 'HandleLidSwitch=suspend-then-hibernate' '合盖策略=suspend-then-hibernate'
check_marker <(printf '%s\n' "$logind_config") 'HandleLidSwitchExternalPower=suspend-then-hibernate' '外接电源合盖策略正确'
check_marker <(printf '%s\n' "$logind_config") 'HandleLidSwitchDocked=ignore' 'Docked 合盖策略=ignore'
check_marker <(printf '%s\n' "$sleep_config") 'HibernateDelaySec=1h' 'HibernateDelaySec=1h'

niri_config=/home/liou/.config/niri/config.kdl
waybar_config=/home/liou/.config/waybar/config.jsonc
helix_config=/home/liou/.config/helix/languages.toml
rime_config=/home/liou/.local/share/fcitx5/rime/user.yaml

check_file "$niri_config"
check_file "$waybar_config"
check_file "$helix_config"
check_marker "$niri_config" 'wlopm --off' 'Niri 包含挂起前关闭输出'
check_marker "$niri_config" 'wlopm --on' 'Niri 包含恢复后打开输出'
check_marker "$waybar_config" '"temperature"' 'Waybar 包含温度模块'
check_marker "$waybar_config" '"custom/fan"' 'Waybar 包含风扇模块'
check_marker "$waybar_config" '"mpris"' 'Waybar 包含 MPRIS 模块'
check_marker "$helix_config" 'nixfmt' 'Helix Nix formatter 已生成'

if [ -x /etc/profiles/per-user/liou/bin/waybar-fan ]; then
  pass 'waybar-fan 已安装'
else
  fail 'waybar-fan 未安装'
fi

if [ -d /home/liou/.local/share/fcitx5/rime/sync ] &&
   grep -Eq '^[[:space:]]*sync_dir:' "$rime_config" 2>/dev/null; then
  pass 'Rime sync_dir 已配置'
else
  warn 'Rime sync_dir 尚未配置'
fi

if [ -d /home/liou/.local/share/fcitx5/rime/luna_pinyin.userdb ]; then
  pass 'Rime luna_pinyin.userdb 存在'
else
  warn 'Rime userdb 尚未恢复'
fi

mihomo_config=/home/liou/.config/clashtui/mihomo/config.yaml
if [ -f "$mihomo_config" ]; then
  mihomo_dir=/home/liou/.config/clashtui/mihomo
  mihomo_providers_dir="$mihomo_dir/providers"
  mihomo_dir_mode="$(stat -c %a "$mihomo_dir" 2>/dev/null || true)"
  mihomo_providers_mode="$(stat -c %a "$mihomo_providers_dir" 2>/dev/null || true)"
  mihomo_umask="$(systemctl show clashtui-mihomo.service -p UMask --value 2>/dev/null || true)"
  if [ "$mihomo_dir_mode" = 2770 ] &&
     [ "$mihomo_providers_mode" = 2770 ] &&
     [ "$mihomo_umask" = 0007 ]; then
    pass 'clashtui/mihomo 目录权限、setgid 和 systemd UMask 正确'
  else
    fail "clashtui/mihomo 权限不符合预期：dir=$mihomo_dir_mode providers=$mihomo_providers_mode UMask=$mihomo_umask"
  fi
  if grep -Eq -q '^[[:space:]]*external-controller:[[:space:]]*127\.0\.0\.1:9090([[:space:]]*#.*)?$' "$mihomo_config" &&
     grep -Eq -q '^[[:space:]]*mixed-port:[[:space:]]*7897([[:space:]]*#.*)?$' "$mihomo_config"; then
    pass 'mihomo 配置包含 clashtui controller=127.0.0.1:9090 和 mixed-port=7897'
  else
    fail 'mihomo 配置缺少 clashtui controller 或预期 mixed-port'
  fi
  if systemctl is-active --quiet clashtui-mihomo; then
    pass 'clashtui-mihomo.service active'
  else
    fail 'clashtui-mihomo.service 非 active'
  fi
  if ip link show Meta >/dev/null 2>&1; then
    pass 'mihomo TUN 接口 Meta 存在'
  else
    fail 'mihomo TUN 接口 Meta 不存在'
  fi
  if ss -ltnup 2>/dev/null | grep -Eq '[:.]7897[[:space:]]'; then
    pass 'mihomo mixed-port 7897 正在监听'
  else
    fail 'mihomo mixed-port 7897 未监听'
  fi
  if ss -ltnup 2>/dev/null | grep -Eq '127\.0\.0\.1:9090[[:space:]]'; then
    pass 'mihomo clashtui controller 9090 正在监听'
  else
    fail 'mihomo clashtui controller 9090 未监听'
  fi
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS --max-time 5 http://127.0.0.1:9090/version -o /dev/null; then
      pass 'clashtui controller API smoke test 通过'
    else
      fail 'clashtui controller API 不可访问'
    fi
    if curl -fsS --max-time 15 --proxy http://127.0.0.1:7897 \
      https://www.gstatic.com/generate_204 -o /dev/null; then
      pass 'mihomo 代理出站 smoke test 通过'
    else
      warn 'mihomo 代理出站 smoke test 失败（可能是节点/外网临时问题）'
    fi
  else
    warn '找不到 curl，跳过 mihomo 代理出站 smoke test'
  fi
else
  warn 'mihomo 配置不存在；请先运行 scripts/restore-secrets.sh'
fi

echo
echo '[MANUAL] 仍需在目标机本地桌面确认：'
echo '  1. greetd/niri 能否登录，显示器和外接屏是否正常。'
echo '  2. fcitx5 能否切换到 Rime，并实际输入中文候选词。'
echo '  3. Waybar 温度/风扇/MPRIS 是否在真实硬件和播放器上显示。'
echo '  4. 先手动 suspend/resume，再在本地执行一次真实 hibernate。'

printf '\n总结：%s 个失败，%s 个警告。\n' "$failures" "$warnings"
if [ "$failures" -gt 0 ]; then
  exit 1
fi
REMOTE
