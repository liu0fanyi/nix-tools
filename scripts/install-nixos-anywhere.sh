#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target="${NIXOS_ANYWHERE_TARGET:-}"
if [[ -z "$target" ]]; then
  target="${NIXOS_ANYWHERE_SSH_USER:-root}@${NIXOS_ANYWHERE_SSH_HOST:-192.168.1.6}"
fi
flake="${NIXOS_ANYWHERE_FLAKE:-}"
nix_extra_substituters="${NIXOS_ANYWHERE_EXTRA_SUBSTITUTERS-https://mirrors.tuna.tsinghua.edu.cn/nix-channels/store}"
proxy_mode="${NIXOS_ANYWHERE_PROXY_MODE:-auto}"
proxy_url="${NIXOS_ANYWHERE_PROXY_URL-http://127.0.0.1:7897}"
remote_proxy_url_override="${NIXOS_ANYWHERE_REMOTE_PROXY_URL-}"
remote_proxy_check="${NIXOS_ANYWHERE_REMOTE_PROXY_CHECK:-auto}"
kexec_mode="${NIXOS_ANYWHERE_KEXEC_MODE:-local}"
kexec_path="${NIXOS_ANYWHERE_KEXEC_PATH-}"
kexec_url="${NIXOS_ANYWHERE_KEXEC_URL:-https://github.com/nix-community/nixos-images/releases/download/nixos-25.11/nixos-kexec-installer-noninteractive-x86_64-linux.tar.gz}"
kexec_cache_dir="${NIXOS_ANYWHERE_KEXEC_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/nixos-anywhere}"
restore_mode="${NIXOS_ANYWHERE_RESTORE_SECRETS:-required}"
swap_override="${NIXOS_ANYWHERE_SWAP_GIB:-auto}"
swap_tier="custom"
auto_layout="1"
mode="install"
assume_yes="0"

ssh_options=(
  -o BatchMode=yes
  -o ConnectTimeout=5
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
)
cd "$repo_dir"

while (($# > 0)); do
  case "$1" in
    --check)
      mode="check"
      shift
      ;;
    --yes)
      assume_yes="1"
      shift
      ;;
    --target)
      [[ $# -ge 2 ]] || { echo "--target 需要 user@host 参数。" >&2; exit 2; }
      target="$2"
      shift 2
      ;;
    --flake)
      [[ $# -ge 2 ]] || { echo "--flake 需要 flake 参数。" >&2; exit 2; }
      flake="$2"
      shift 2
      ;;
    --swap-gib)
      [[ $# -ge 2 ]] || { echo "--swap-gib 需要 auto、16、24、32 或 64。" >&2; exit 2; }
      swap_override="$2"
      shift 2
      ;;
    --proxy-mode)
      [[ $# -ge 2 ]] || { echo "--proxy-mode 需要 auto、always 或 off。" >&2; exit 2; }
      proxy_mode="$2"
      shift 2
      ;;
    --proxy-url)
      [[ $# -ge 2 ]] || { echo "--proxy-url 需要 URL 参数。" >&2; exit 2; }
      proxy_url="$2"
      shift 2
      ;;
    --remote-proxy-url)
      [[ $# -ge 2 ]] || { echo "--remote-proxy-url 需要 URL 参数。" >&2; exit 2; }
      remote_proxy_url_override="$2"
      shift 2
      ;;
    --remote-proxy-check)
      [[ $# -ge 2 ]] || { echo "--remote-proxy-check 需要 auto、required 或 off。" >&2; exit 2; }
      remote_proxy_check="$2"
      shift 2
      ;;
    --kexec-path)
      [[ $# -ge 2 ]] || { echo "--kexec-path 需要本地 kexec tarball 路径。" >&2; exit 2; }
      kexec_path="$2"
      kexec_mode="local"
      shift 2
      ;;
    --extra-substituters)
      [[ $# -ge 2 ]] || { echo "--extra-substituters 需要 URL 列表参数。" >&2; exit 2; }
      nix_extra_substituters="$2"
      shift 2
      ;;
    --restore-secrets)
      [[ $# -ge 2 ]] || { echo "--restore-secrets 需要 required、auto 或 off。" >&2; exit 2; }
      restore_mode="$2"
      shift 2
      ;;
    --help|-h)
      cat <<EOF
用法：
  $0 --check       只做重装前只读预检，不构建、不分区、不重启
  $0               检查后要求输入 REINSTALL，再执行完整重装
  $0 --yes         检查后跳过确认提示，执行完整重装
  $0 --target root@192.168.1.23 --proxy-url http://127.0.0.1:8890

环境变量：
  NIXOS_ANYWHERE_TARGET=root@192.168.1.6
  NIXOS_ANYWHERE_SSH_USER=root             # 未设置 TARGET 时使用
  NIXOS_ANYWHERE_SSH_HOST=192.168.1.6      # 未设置 TARGET 时使用
  NIXOS_ANYWHERE_FLAKE=.#homebox-install-32g  # 可选 16g/24g/32g/64g
  NIXOS_ANYWHERE_SWAP_GIB=auto              # auto/16/24/32/64；有 FLAKE 时不生效
  NIXOS_ANYWHERE_PROXY_MODE=auto               # auto/always/off，默认探测 Clash Verge
  NIXOS_ANYWHERE_PROXY_URL=http://127.0.0.1:7897
  NIXOS_ANYWHERE_REMOTE_PROXY_URL=http://192.168.1.3:7897
  NIXOS_ANYWHERE_REMOTE_PROXY_CHECK=auto       # auto/required/off
  NIXOS_ANYWHERE_KEXEC_MODE=local              # local/remote；默认本机准备镜像
  NIXOS_ANYWHERE_KEXEC_PATH=/path/to/kexec.tar.gz  # 可选，复用本地镜像
  NIXOS_ANYWHERE_KEXEC_URL=https://github.com/nix-community/nixos-images/releases/download/nixos-25.11/nixos-kexec-installer-noninteractive-x86_64-linux.tar.gz
  NIXOS_ANYWHERE_KEXEC_CACHE_DIR=~/.cache/nixos-anywhere
  NIXOS_ANYWHERE_EXTRA_SUBSTITUTERS=https://mirrors.tuna.tsinghua.edu.cn/nix-channels/store
  NIXOS_ANYWHERE_USE_DESTINATION_SUBSTITUTERS=1  # 可选，恢复目标端下载
  NIXOS_ANYWHERE_RESTORE_SECRETS=required       # required/auto/off，默认重装后自动恢复

默认使用本机代理和清华 substituter，并由本机直接推送闭包；目标机的局域网代理
地址会从本机代理 URL 自动推导，也可用 NIXOS_ANYWHERE_REMOTE_PROXY_URL 单独指定。
默认还会在本机通过代理下载并缓存 kexec 镜像，再上传给目标机，避免目标机直连 GitHub；
可用 KEXEC_PATH 复用已有镜像，只有明确设置 KEXEC_MODE=remote 才恢复目标机直连下载。
安装完成后自动恢复 git-crypt secrets、mihomo/clashtui、Rime userdb 和 npm 工具。
EOF
      exit 0
      ;;
    --)
      shift
      (($# == 0)) || { echo "不支持位置参数：$*" >&2; exit 2; }
      ;;
    *)
      echo "未知参数：$1" >&2
      echo "使用 $0 --help 查看用法。" >&2
      exit 2
      ;;
  esac
done

if [[ -n "$flake" ]]; then
  auto_layout="0"
fi

case "$restore_mode" in
  required|auto|off)
    ;;
  *)
    echo "NIXOS_ANYWHERE_RESTORE_SECRETS 必须是 required、auto 或 off。" >&2
    exit 2
    ;;
esac

case "$swap_override" in
  auto|16|24|32|64)
    ;;
  *)
    echo "NIXOS_ANYWHERE_SWAP_GIB 必须是 auto、16、24、32 或 64。" >&2
    exit 2
    ;;
esac

case "$remote_proxy_check" in
  auto|required|off)
    ;;
  *)
    echo "NIXOS_ANYWHERE_REMOTE_PROXY_CHECK 必须是 auto、required 或 off。" >&2
    exit 2
    ;;
esac

case "$kexec_mode" in
  local|remote)
    ;;
  *)
    echo "NIXOS_ANYWHERE_KEXEC_MODE 必须是 local 或 remote。" >&2
    exit 2
    ;;
esac

# 在任何清盘动作前确认 secrets 能在重装后恢复。required 是默认值，避免
# 安装成功但 clashtui/mihomo 因运行时配置缺失而不可用；off 只适合有意部署
# 一个不含运行时 secrets 的基础系统。
secrets_ready="0"
if [[ "$restore_mode" != off ]] &&
   { [[ -s "$repo_dir/secrets/mihomo-config.yaml" ]] || [[ -s "$repo_dir/git-crypt-key" ]]; }; then
  if "$repo_dir/scripts/restore-secrets.sh" --check; then
    secrets_ready="1"
  fi
fi
if [[ "$restore_mode" == required && "$secrets_ready" != 1 ]]; then
  cat >&2 <<'EOF'
重装前检查失败：没有可用的已解锁 mihomo secrets。
请先准备 git-crypt-key 并安装 git-crypt，或解锁 secrets/mihomo-config.yaml。
如确实只想安装基础系统，可显式设置 NIXOS_ANYWHERE_RESTORE_SECRETS=off。
EOF
  exit 7
fi

"$repo_dir/scripts/check-nixos-anywhere-network.sh" "$target"

if [[ "$auto_layout" == 1 ]]; then
  target_arch="$(ssh "${ssh_options[@]}" "$target" uname -m)"
  if [[ "$target_arch" != "x86_64" ]]; then
    echo "自动安装档位仅支持 x86_64，目标架构为 $target_arch；请指定适配的 flake。" >&2
    exit 5
  fi
  if ! ssh "${ssh_options[@]}" "$target" test -b /dev/sda; then
    echo "自动安装布局要求目标存在 /dev/sda；检测到其他磁盘布局，请指定适配的 flake。" >&2
    exit 6
  fi
  disk_names="$(ssh "${ssh_options[@]}" "$target" \
    "lsblk -dn -o NAME,TYPE,RM | awk '\$2 == \"disk\" && \$3 == \"0\" { print \$1 }' | sort -u")"
  if [[ "$disk_names" != "sda" ]]; then
    echo "自动安装布局只允许唯一的内部 /dev/sda；检测到：${disk_names:-无}。请指定适配的 flake。" >&2
    exit 6
  fi
fi

if [[ -z "$flake" ]]; then
  memory_kib="$(ssh "${ssh_options[@]}" "$target" \
    'grep "^MemTotal:" /proc/meminfo | tr -cd "0-9"')"
  if [[ -z "$memory_kib" ]]; then
    echo "无法读取目标机内存，拒绝继续重装；可显式设置 NIXOS_ANYWHERE_FLAKE。" >&2
    exit 4
  fi
  memory_gib=$(( (memory_kib + 1048575) / 1048576 ))
  if [[ "$swap_override" != auto ]]; then
    swap_tier="$swap_override"
  elif (( memory_gib <= 8 )); then
    swap_tier=16
  elif (( memory_gib <= 16 )); then
    swap_tier=24
  elif (( memory_gib <= 24 )); then
    swap_tier=32
  else
    swap_tier=64
  fi
  flake=".#homebox-install-${swap_tier}g"
  if [[ "$swap_override" == auto ]]; then
    echo "检测到目标内存约 ${memory_gib} GiB，自动选择 ${swap_tier}G swap 配置：${flake}"
  else
    echo "目标内存约 ${memory_gib} GiB，使用手动指定的 ${swap_tier}G swap 配置：${flake}"
  fi
fi

# The installer is launched from the current machine.  Apply its local HTTP
# proxy and substituter settings to nixos-anywhere and all child Nix commands.
# This does not make 127.0.0.1 refer to the target machine; the target is kept
# off destination-side substitution below so it does not need this proxy.
case "$proxy_mode" in
  off|none|0)
    proxy_active="0"
    echo "本机安装下载代理：已关闭。"
    ;;
  always|on|1)
    [[ -n "$proxy_url" ]] || {
      echo "代理模式为 always，但 NIXOS_ANYWHERE_PROXY_URL 为空。" >&2
      exit 2
    }
    export http_proxy="$proxy_url"
    export https_proxy="$proxy_url"
    export HTTP_PROXY="$proxy_url"
    export HTTPS_PROXY="$proxy_url"
    export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost}"
    proxy_active="1"
    echo "本机安装下载代理：$proxy_url"
    ;;
  auto)
    if [[ -z "$proxy_url" ]]; then
      proxy_active="0"
      echo "本机安装下载代理：已关闭（PROXY_URL 为空）。"
    elif command -v curl >/dev/null 2>&1 &&
       curl -fsS --proxy "$proxy_url" --connect-timeout 2 --max-time 5 \
         https://cache.nixos.org/nix-cache-info -o /dev/null; then
      export http_proxy="$proxy_url"
      export https_proxy="$proxy_url"
      export HTTP_PROXY="$proxy_url"
      export HTTPS_PROXY="$proxy_url"
      export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost}"
      proxy_active="1"
      echo "本机安装下载代理：$proxy_url（自动探测成功）"
    else
      echo "本机安装下载代理：未检测到可用的 $proxy_url，继续使用直连。" >&2
    fi
    ;;
  *)
    echo "NIXOS_ANYWHERE_PROXY_MODE 必须是 auto、always 或 off。" >&2
    exit 2
    ;;
esac

# 目标机上的 mihomo 首次启动也可能需要下载 GeoData/订阅。把本机回环
# 代理改写成“到目标机可达的本机地址”，只通过环境变量传给 post-install，
# 不写入 NixOS 配置，避免把远端永久绑定到本机的临时地址。
remote_proxy_url="$remote_proxy_url_override"
if [[ -z "$remote_proxy_url" && "${proxy_active:-0}" == 1 ]]; then
  proxy_host="${proxy_url#*://}"
  proxy_host="${proxy_host%%:*}"
  if [[ "$proxy_host" == 127.0.0.1 || "$proxy_host" == localhost ]]; then
    target_host="${target##*@}"
    local_proxy_ip="$(ip -4 route get "$target_host" 2>/dev/null |
      sed -n 's/.* src \([0-9.][0-9.]*\).*/\1/p' | head -1)"
    if [[ -n "$local_proxy_ip" ]]; then
      remote_proxy_url="${proxy_url/$proxy_host/$local_proxy_ip}"
    fi
  else
    remote_proxy_url="$proxy_url"
  fi
fi
if [[ -n "$remote_proxy_url" ]]; then
  echo "重装后恢复 mihomo 订阅时将临时使用目标可达代理：$remote_proxy_url"
fi

if [[ -n "$remote_proxy_url" && "$remote_proxy_check" != off ]]; then
  if ssh "${ssh_options[@]}" "$target" bash -s -- "$remote_proxy_url" <<'REMOTE_PROXY_CHECK'
set -euo pipefail
proxy_url="$1"
command -v curl >/dev/null 2>&1
curl -fsS --proxy "$proxy_url" --connect-timeout 3 --max-time 8 \
  https://cache.nixos.org/nix-cache-info -o /dev/null
REMOTE_PROXY_CHECK
  then
    echo "目标机访问局域网代理检查通过：$remote_proxy_url"
  elif [[ "$remote_proxy_check" == required ]]; then
    echo "目标机无法通过代理访问 cache.nixos.org，按 required 策略停止，未清盘。" >&2
    exit 8
  else
    echo "警告：目标机暂时无法访问 $remote_proxy_url，本次重装将不向 mihomo 首次启动传递该代理。" >&2
    echo "如目标机必须使用本机代理，请修正 LAN sharing/端口，或设置 NIXOS_ANYWHERE_REMOTE_PROXY_CHECK=required。" >&2
    remote_proxy_url=""
  fi
fi

if [[ -n "$nix_extra_substituters" && "${NIX_CONFIG:-}" != *"extra-substituters"* ]]; then
  nix_config="${NIX_CONFIG:-}"
  if [[ -n "$nix_config" ]]; then
    nix_config+=$'\n'
  fi
  nix_config+="extra-substituters = $nix_extra_substituters"
  export NIX_CONFIG="$nix_config"
  echo "Nix 额外 substituter：$nix_extra_substituters"
elif [[ -z "$nix_extra_substituters" ]]; then
  echo "本次安装不额外添加 substituter（目标 NixOS 配置仍可能有持久化设置）。"
fi

nixos_anywhere_network_args=()
use_destination_substituters="${NIXOS_ANYWHERE_USE_DESTINATION_SUBSTITUTERS:-0}"
case "$use_destination_substituters" in
  0|1)
    ;;
  *)
    echo "NIXOS_ANYWHERE_USE_DESTINATION_SUBSTITUTERS 必须是 0 或 1。" >&2
    exit 2
    ;;
esac
if [[ "$use_destination_substituters" != 1 ]]; then
  nixos_anywhere_network_args+=(--no-substitute-on-destination)
  echo "传输策略：本机直接推送闭包（禁用目标端 substituter）。"
else
  echo "传输策略：允许目标端 substituter 下载闭包。"
fi

if [[ "$mode" == "check" ]]; then
  echo "检查完成：未执行 nixos-anywhere。"
  exit 0
fi

nixos_anywhere_kexec_args=()
if [[ "$kexec_mode" == local ]]; then
  if [[ -z "$kexec_path" ]]; then
    command -v curl >/dev/null 2>&1 || {
      echo "本机模式需要 curl 下载 kexec 镜像；请安装 curl 或设置 NIXOS_ANYWHERE_KEXEC_PATH。" >&2
      exit 9
    }
    mkdir -p "$kexec_cache_dir"
    kexec_filename="${kexec_url##*/}"
    kexec_path="$kexec_cache_dir/$kexec_filename"
    if [[ ! -s "$kexec_path" ]]; then
      kexec_tmp="$kexec_path.part.$$"
      echo "通过本机代理下载 kexec 镜像：$kexec_url"
      curl_args=(
        --fail
        --location
        --retry 3
        --connect-timeout 10
        --max-time 1800
        --output "$kexec_tmp"
        "$kexec_url"
      )
      if [[ "${proxy_active:-0}" == 1 ]]; then
        curl_args=(--proxy "$proxy_url" "${curl_args[@]}")
      fi
      if ! curl "${curl_args[@]}"; then
        rm -f "$kexec_tmp"
        echo "kexec 镜像下载失败：$kexec_url" >&2
        exit 9
      fi
      mv -f "$kexec_tmp" "$kexec_path"
    else
      echo "复用本机缓存的 kexec 镜像：$kexec_path"
    fi
  fi
  if [[ ! -f "$kexec_path" ]]; then
    echo "本地 kexec 镜像不存在：$kexec_path" >&2
    exit 9
  fi
  nixos_anywhere_kexec_args+=(--kexec "$kexec_path")
  echo "kexec 传输策略：使用本机镜像 $kexec_path"
else
  echo "kexec 传输策略：目标机自行下载镜像（可能受目标网络速度影响）。"
fi

if [[ "$assume_yes" != 1 ]]; then
  cat >&2 <<EOF
警告：这会通过 disko 清空并重新分区 $target 的磁盘，目标布局为：
  EFI 500M + ${swap_tier}G（或指定配置中的）swap LV + 其余空间 root LV

目标配置：$flake
如果确认目标和数据备份无误，请输入 REINSTALL 继续：
EOF
  read -r confirmation
  [[ "$confirmation" == "REINSTALL" ]] || {
    echo "已取消。" >&2
    exit 1
  }
fi

# nixos-anywhere 需要先把目标机硬件报告写到 flake 中才能构建，但这个
# 报告只属于本次目标机，不能留在工作区或被提交。无论安装成功、失败还是
# post-install 失败，都恢复用户原来的文件。
hardware_config="$repo_dir/nixos/hardware-configuration.nix"
hardware_backup="$(mktemp "${TMPDIR:-/tmp}/nixos-anywhere-hardware.XXXXXX")"
cp -p "$hardware_config" "$hardware_backup"
restore_hardware_config() {
  cp -p "$hardware_backup" "$hardware_config"
  rm -f "$hardware_backup"
}
trap restore_hardware_config EXIT

wait_for_target_ssh() {
  echo "等待目标机重启后 SSH 恢复..."
  for _ in $(seq 1 90); do
    if ssh "${ssh_options[@]}" "$target" true >/dev/null 2>&1; then
      echo "目标机 SSH 已恢复。"
      return 0
    fi
    sleep 2
  done
  echo "错误：目标机重启后 180 秒内 SSH 未恢复。" >&2
  return 1
}

nix run github:nix-community/nixos-anywhere -- \
  "${nixos_anywhere_network_args[@]}" \
  "${nixos_anywhere_kexec_args[@]}" \
  --flake "$flake" \
  --generate-hardware-config nixos-generate-config "$repo_dir/nixos/hardware-configuration.nix" \
  "$target"

if [[ "$restore_mode" == off ]]; then
  echo "已完成 NixOS 安装；按 NIXOS_ANYWHERE_RESTORE_SECRETS=off 跳过运行时 secrets 恢复。"
elif [[ "$secrets_ready" == 1 ]]; then
  wait_for_target_ssh
  restore_proxy_mode="off"
  if [[ "${proxy_active:-0}" == 1 ]]; then
    restore_proxy_mode="always"
  fi
  NIXOS_ANYWHERE_PROXY_MODE="$restore_proxy_mode" \
  NIXOS_ANYWHERE_PROXY_URL="$proxy_url" \
  NIXOS_ANYWHERE_REMOTE_PROXY_URL="$remote_proxy_url" \
    "$repo_dir/scripts/restore-secrets.sh" "$target"
else
  echo "警告：NixOS 安装完成，但本地没有可恢复的 secrets；clashtui/mihomo 尚未配置。" >&2
  echo "稍后准备 secrets 后运行：scripts/restore-secrets.sh $target" >&2
fi
