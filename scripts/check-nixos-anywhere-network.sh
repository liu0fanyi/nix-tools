#!/usr/bin/env bash
# 只读检查 nixos-anywhere/kexec 重装所需的有线网络。
set -euo pipefail

target="${1:-${NIXOS_ANYWHERE_TARGET:-${NIXOS_ANYWHERE_SSH_USER:-root}@${NIXOS_ANYWHERE_SSH_HOST:-192.168.1.6}}}"

if ! report="$({
  ssh -o BatchMode=yes -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR "$target" 'set -u
    found=0
    for path in /sys/class/net/*; do
      iface=${path##*/}
      [ "$iface" = lo ] && continue
      # 只接受真实的、非无线的物理网卡；排除 Wi-Fi 和 tun/bridge。
      [ -e "$path/device" ] || continue
      [ -e "$path/wireless" ] && continue
      found=1
      carrier=unknown
      [ -r "$path/carrier" ] && carrier=$(cat "$path/carrier")
      printf "wired %s carrier=%s\n" "$iface" "$carrier"
      ip -brief address show "$iface" 2>/dev/null || true
      if ip -4 -o address show "$iface" scope global 2>/dev/null | grep -q .; then
        printf "wired-ip %s yes\n" "$iface"
      else
        printf "wired-ip %s no\n" "$iface"
      fi
    done
    [ "$found" -eq 1 ] || printf "wired none\n"
    if [ -d /sys/firmware/efi/efivars ] && [ -w /sys/firmware/efi/efivars ]; then
      printf "boot uefi efivars=rw\n"
    elif [ -d /sys/firmware/efi ]; then
      printf "boot uefi efivars=ro\n"
    else
      printf "boot legacy\n"
    fi
  '
} 2>&1)"; then
  printf '%s\n' "$report" >&2
  echo "网络预检失败：无法通过 SSH 读取目标机网络状态。" >&2
  exit 2
fi

printf '%s\n' "$report"

if ! grep -Eq '^wired [^ ]+ carrier=1$' <<<"$report"; then
  cat >&2 <<EOF
网络预检失败：目标机没有检测到已连接的有线网卡。
nixos-anywhere 的默认 kexec 安装流程不支持 Wi-Fi；请接上网线、确认目标机
从有线网卡获得地址，然后把那个有线地址作为 NIXOS_ANYWHERE_TARGET 重试。
EOF
  exit 3
fi

echo "网络预检通过：目标机存在已连接的有线网卡。"

if ! grep -Eq '^wired-ip [^ ]+ yes$' <<<"$report"; then
  cat >&2 <<EOF
网络预检失败：有线网卡虽然检测到链路，但没有全局 IPv4 地址。
请先让有线连接完成 DHCP，再以该地址重试；未执行清盘。
EOF
  exit 3
fi

if ! grep -Eq '^boot uefi efivars=rw$' <<<"$report"; then
  cat >&2 <<EOF
启动方式预检失败：目标机不是可写 EFI 环境（需要 UEFI + efivars 可写）。
当前配置会为这台目标机安装 UEFI GRUB 并注册 NVRAM 启动项；如果是 BIOS、
efivars 只读或另一种硬件，请先准备单独的 flake/bootloader 配置，未执行清盘。
EOF
  exit 4
fi

echo "启动方式预检通过：UEFI efivars 可写。"
