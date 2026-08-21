#!/usr/bin/env bash
# 恢复目标机的 git-crypt secrets 和重装后的运行时数据。
# 用法: ./scripts/restore-secrets.sh [--mihomo-only] [user@host]
set -euo pipefail

skip_npm=0
skip_rime=0
check_only=0

usage() {
  cat <<'EOF'
用法：
  scripts/restore-secrets.sh [user@host]
  scripts/restore-secrets.sh --mihomo-only [user@host]
  scripts/restore-secrets.sh --check

--mihomo-only  只恢复 mihomo 配置并验证 clashtui controller，不安装 npm
               全局包，也不恢复 Rime userdb。
--check         只检查本地 git-crypt key/配置，不连接或修改目标机。

环境变量：
  NIX_TOOLS_SECRETS_DIR=~/.config/secrets
  NIX_TOOLS_GIT_CRYPT_KEY=~/.config/secrets/nix-tools/nix-tools-git-crypt.key
  NIXOS_ANYWHERE_TARGET=root@192.168.1.6
  NIXOS_ANYWHERE_PROXY_MODE=auto
  NIXOS_ANYWHERE_PROXY_URL=http://127.0.0.1:7897
  NIXOS_ANYWHERE_REMOTE_PROXY_URL=http://192.168.1.3:7897
  NIXOS_ANYWHERE_GEODATA_CACHE_DIR=~/.cache/mihomo
  （本机代理用于预取 GeoData；目标代理可选，用于重装后首次下载订阅。）
EOF
}

while (($# > 0)); do
  case "$1" in
    --mihomo-only)
      skip_npm=1
      skip_rime=1
      shift
      ;;
    --check)
      check_only=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -* )
      echo "未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

TARGET="${1:-${NIXOS_ANYWHERE_TARGET:-${NIXOS_ANYWHERE_SSH_USER:-root}@${NIXOS_ANYWHERE_SSH_HOST:-192.168.1.6}}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SECRETS_DIR="${NIX_TOOLS_SECRETS_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/secrets}"
KEY_FILE="${NIX_TOOLS_GIT_CRYPT_KEY:-$SECRETS_DIR/nix-tools/nix-tools-git-crypt.key}"
if [[ ! -s "$KEY_FILE" ]]; then
  # 兼容旧布局：~/.config/secrets/nix-tools-git-crypt.key（vault.sh 统一前）
  [[ -s "$SECRETS_DIR/nix-tools-git-crypt.key" ]] && KEY_FILE="$SECRETS_DIR/nix-tools-git-crypt.key"
fi
if [[ ! -s "$KEY_FILE" ]]; then
  for legacy_key in "$REPO_DIR/nix-tools-git-crypt.key" "$REPO_DIR/git-crypt-key"; do
    if [[ -s "$legacy_key" ]]; then
      KEY_FILE="$legacy_key"
      break
    fi
  done
fi
CONFIG_FILE="$REPO_DIR/secrets/mihomo-config.yaml"
REMOTE_PROXY_URL="${NIXOS_ANYWHERE_REMOTE_PROXY_URL:-}"
remote_proxy_arg="${REMOTE_PROXY_URL:-__NIXOS_ANYWHERE_NO_PROXY__}"
LOCAL_PROXY_MODE="${NIXOS_ANYWHERE_PROXY_MODE:-auto}"
LOCAL_PROXY_URL="${NIXOS_ANYWHERE_PROXY_URL:-http://127.0.0.1:7897}"
GEODATA_CACHE_DIR="${NIXOS_ANYWHERE_GEODATA_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/mihomo}"
GEOSITE_URL="https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat"
GEOIP_URL="https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat"
ssh_options=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
)
cd "$REPO_DIR"

# 1. git-crypt 解锁（用唯一密钥）。如果工作树已经是明文，允许在没有
# git-crypt 可执行文件的环境中继续恢复，方便安装脚本复用。
config_ready=0
if [[ -s "$CONFIG_FILE" ]] &&
   grep -Eq '^[[:space:]]*external-controller:[[:space:]]*127\.0\.0\.1:9090([[:space:]]*#.*)?$' \
     "$CONFIG_FILE"; then
  config_ready=1
fi

git_crypt_status=""
if (( ! config_ready )) && command -v git-crypt >/dev/null 2>&1; then
  # 不要把 git-crypt status 直接接 grep -q：grep 找到首个匹配后关闭管道，
  # git-crypt 可能把 SIGPIPE 报成 Aborted，造成误导性的预检告警。
  git_crypt_status="$(git-crypt status 2>/dev/null || true)"
fi
if (( ! config_ready )) && grep -q "encrypted: secrets/" <<<"$git_crypt_status"; then
  [[ -s "$KEY_FILE" ]] || {
    echo "错误: secrets 仍处于加密状态，但找不到 Nix Tools 密钥：$KEY_FILE。" >&2
    echo "请先从 KeePassXC 导出 nix-tools-git-crypt.key，或设置 NIX_TOOLS_GIT_CRYPT_KEY。" >&2
    exit 1
  }
  echo "解锁 git-crypt（$KEY_FILE）..."
  git-crypt unlock "$KEY_FILE"
fi

[[ -s "$CONFIG_FILE" ]] || {
  echo "错误: 缺少已解锁的 $CONFIG_FILE。" >&2
  exit 1
}
# 这个检查避免把任意文件误当作 mihomo 配置部署；不输出订阅 URL 等 secrets。
grep -Eq '^[[:space:]]*external-controller:[[:space:]]*127\.0\.0\.1:9090([[:space:]]*#.*)?$' "$CONFIG_FILE" || {
  echo "错误: mihomo 配置缺少预期的 127.0.0.1:9090 external-controller。" >&2
  exit 1
}

if (( check_only )); then
  echo "本地 secrets 预检通过：git-crypt/mihomo 配置可用于重装后恢复。"
  exit 0
fi

# mihomo 的 GeoData 下载不稳定地继承 systemd 的 HTTP_PROXY；先由本机
# （通常是 Clash Verge）下载并缓存，重装后直接上传，避免首次启动卡在
# GeoSite.dat/GeoIP.dat。
prepare_mihomo_geodata() {
  command -v curl >/dev/null 2>&1 || {
    echo "错误：恢复 mihomo 需要本机 curl 下载 GeoData。" >&2
    exit 1
  }

  mkdir -p "$GEODATA_CACHE_DIR"
  local proxy_args=()
  if [[ "$LOCAL_PROXY_MODE" != off && -n "$LOCAL_PROXY_URL" ]]; then
    if curl --fail --silent --show-error --proxy "$LOCAL_PROXY_URL" \
      --connect-timeout 3 --max-time 8 \
      https://cache.nixos.org/nix-cache-info -o /dev/null; then
      proxy_args=(--proxy "$LOCAL_PROXY_URL")
      echo "mihomo GeoData 下载代理：$LOCAL_PROXY_URL"
    elif [[ "$LOCAL_PROXY_MODE" == always ]]; then
      echo "错误：NIXOS_ANYWHERE_PROXY_MODE=always，但本机代理不可用：$LOCAL_PROXY_URL" >&2
      exit 1
    else
      echo "警告：本机代理不可用，尝试直连下载 mihomo GeoData。" >&2
    fi
  fi

  local name url cache_file tmp_file
  for name in geosite geoip; do
    if [[ "$name" == geosite ]]; then
      url="$GEOSITE_URL"
    else
      url="$GEOIP_URL"
    fi
    cache_file="$GEODATA_CACHE_DIR/$name.dat"
    if [[ ! -s "$cache_file" ]]; then
      tmp_file="$cache_file.part.$$"
      echo "下载 mihomo $name.dat：$url"
      if ! curl --fail --location --retry 3 --connect-timeout 10 --max-time 600 \
        "${proxy_args[@]}" --output "$tmp_file" "$url"; then
        rm -f "$tmp_file"
        echo "错误：mihomo $name.dat 下载失败。" >&2
        exit 1
      fi
      mv -f "$tmp_file" "$cache_file"
    else
      echo "复用本机缓存的 mihomo $name.dat：$cache_file"
    fi
  done
}

# 2. 部署 mihomo 配置和预取的 GeoData，并在目标机验证 controller 已经可用。
prepare_mihomo_geodata
echo "部署 mihomo 配置到 $TARGET ..."
remote_tmp="/tmp/mihomo-config.$$"
remote_geosite_tmp="/tmp/mihomo-geosite.$$"
remote_geoip_tmp="/tmp/mihomo-geoip.$$"
ssh "${ssh_options[@]}" "$TARGET" 'install -d -o liou -g users -m 2770 /home/liou/.config/clashtui/mihomo && chmod g+s /home/liou/.config/clashtui/mihomo'
scp -O -q "${ssh_options[@]}" "$CONFIG_FILE" "$TARGET:$remote_tmp"
scp -O -q "${ssh_options[@]}" "$GEODATA_CACHE_DIR/geosite.dat" "$TARGET:$remote_geosite_tmp"
scp -O -q "${ssh_options[@]}" "$GEODATA_CACHE_DIR/geoip.dat" "$TARGET:$remote_geoip_tmp"
ssh "${ssh_options[@]}" "$TARGET" bash -s -- "$remote_proxy_arg" "$remote_tmp" "$remote_geosite_tmp" "$remote_geoip_tmp" <<'REMOTE'
set -euo pipefail

proxy_url="$1"
remote_tmp="$2"
remote_geosite_tmp="$3"
remote_geoip_tmp="$4"
if [[ "$proxy_url" == __NIXOS_ANYWHERE_NO_PROXY__ ]]; then
  proxy_url=""
fi
config_dir=/home/liou/.config/clashtui/mihomo
proxy_set=0

clear_proxy_environment() {
  if (( proxy_set )); then
    systemctl unset-environment \
      http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY || true
  fi
}
trap clear_proxy_environment EXIT

# 只为首次启动继承目标可达的本机代理，给 mihomo 下载订阅；GeoData 已由本机
# 预取，不会依赖 mihomo 自己下载。这个代理不会被写进 NixOS 配置；
# 写进 NixOS 配置。启动完成后撤掉 system manager 的临时环境。
if [[ -n "$proxy_url" ]]; then
  systemctl set-environment \
    "http_proxy=$proxy_url" "https_proxy=$proxy_url" \
    "HTTP_PROXY=$proxy_url" "HTTPS_PROXY=$proxy_url" "ALL_PROXY=$proxy_url"
  proxy_set=1
fi

install -o liou -g users -m 0640 "$remote_tmp" "$config_dir/config.yaml"
install -o liou -g users -m 0640 "$remote_geosite_tmp" "$config_dir/geosite.dat"
install -o liou -g users -m 0640 "$remote_geoip_tmp" "$config_dir/geoip.dat"
rm -f "$remote_tmp" "$remote_geosite_tmp" "$remote_geoip_tmp"
systemctl restart clashtui-mihomo.service

ready=0
for _ in $(seq 1 180); do
  if systemctl is-active --quiet clashtui-mihomo.service &&
     ss -ltn 2>/dev/null | grep -Eq '127\.0\.0\.1:9090[[:space:]]'; then
    if ! command -v curl >/dev/null 2>&1 ||
       curl -fsS --max-time 3 http://127.0.0.1:9090/version -o /dev/null; then
      ready=1
      break
    fi
  fi
  sleep 1
done

if (( ! ready )); then
  echo "错误: mihomo 未在 180 秒内提供 clashtui controller。" >&2
  systemctl status clashtui-mihomo.service --no-pager -l >&2 || true
  journalctl -u clashtui-mihomo.service -n 40 --no-pager >&2 || true
  exit 1
fi

echo "mihomo 已恢复，clashtui controller=127.0.0.1:9090 可访问。"
REMOTE

# 3. dsh/dsh-tui/pnpm 是独立的 npm 运行时工具；mihomo 恢复成功后再安装，
# 避免 npm 临时网络失败掩盖 clashtui 的真正状态。
if (( ! skip_npm )); then
  echo "安装 npm 全局包到 $TARGET ..."
  ssh "${ssh_options[@]}" "$TARGET" bash -s -- "$remote_proxy_arg" <<'REMOTE'
set -euo pipefail

proxy_url="$1"
if [[ "$proxy_url" == __NIXOS_ANYWHERE_NO_PROXY__ ]]; then
  proxy_url=""
fi
if [[ -n "$proxy_url" ]]; then
  export http_proxy="$proxy_url"
  export https_proxy="$proxy_url"
  export HTTP_PROXY="$proxy_url"
  export HTTPS_PROXY="$proxy_url"
  export ALL_PROXY="$proxy_url"
  export npm_config_proxy="$proxy_url"
  export npm_config_https_proxy="$proxy_url"
fi

user_env=(HOME=/home/liou)
if [[ -n "$proxy_url" ]]; then
  user_env+=(
    "http_proxy=$proxy_url" "https_proxy=$proxy_url"
    "HTTP_PROXY=$proxy_url" "HTTPS_PROXY=$proxy_url" "ALL_PROXY=$proxy_url"
    "npm_config_proxy=$proxy_url" "npm_config_https_proxy=$proxy_url"
  )
fi

runuser -u liou -- env "${user_env[@]}" bash -c \
  'cd /home/liou && npm install -g @deepseek-ai/dsh @deepseek-harness-tui/dsh-tui pnpm 2>&1 | tail -20'
REMOTE
fi

# 4. 恢复 Rime 运行时词库（快照不存在时跳过，避免阻断其他 secrets 恢复）。
if (( ! skip_rime )) && [[ -f "$REPO_DIR/secrets/rime/luna_pinyin.userdb.tar.gz" ]]; then
  "$SCRIPT_DIR/sync-rime-userdb.sh" deploy "$TARGET"
elif (( ! skip_rime )); then
  echo "未找到 Rime userdb 快照，跳过词库恢复"
fi

echo "✅ secrets 和重装后运行时数据恢复完成"
