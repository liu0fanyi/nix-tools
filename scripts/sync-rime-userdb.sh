#!/usr/bin/env bash
# 快照/恢复 Rime 的运行时 userdb。
# 用法：
#   ./scripts/sync-rime-userdb.sh snapshot
#   ./scripts/sync-rime-userdb.sh deploy [user@host]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
RIME_DIR="${RIME_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/fcitx5/rime}"
SNAPSHOT_DIR="$REPO_DIR/secrets/rime"
SNAPSHOT="$SNAPSHOT_DIR/luna_pinyin.userdb.tar.gz"
TARGET="${2:-${NIXOS_ANYWHERE_TARGET:-${NIXOS_ANYWHERE_SSH_USER:-root}@${NIXOS_ANYWHERE_SSH_HOST:-192.168.1.6}}}"
ssh_options=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
)

snapshot() {
  if [[ ! -d "$RIME_DIR/luna_pinyin.userdb" ]]; then
    echo "错误: 找不到 Rime userdb: $RIME_DIR/luna_pinyin.userdb" >&2
    exit 1
  fi

  mkdir -p "$SNAPSHOT_DIR"
  # 排除锁和日志，避免把正在运行时的临时文件带到远程。
  tar \
    --exclude='LOCK' \
    --exclude='LOG' \
    --exclude='LOG.old' \
    --exclude='*.log' \
    -C "$RIME_DIR" \
    -czf "$SNAPSHOT" \
    luna_pinyin.userdb
  chmod 600 "$SNAPSHOT"
  echo "Rime userdb 快照已写入 $SNAPSHOT"
}

deploy() {
  if [[ ! -f "$SNAPSHOT" ]]; then
    echo "错误: 缺少 $SNAPSHOT，请先运行 snapshot" >&2
    exit 1
  fi

  echo "部署 Rime userdb 到 $TARGET ..."
  ssh "${ssh_options[@]}" "$TARGET" '
    set -eu
    rime_dir=/home/liou/.local/share/fcitx5/rime
    install -d -o liou -g users -m 700 "$rime_dir"
    if [ -d "$rime_dir/luna_pinyin.userdb" ]; then
      backup="$rime_dir/luna_pinyin.userdb.before-nix-tools-$(date +%s)"
      mv "$rime_dir/luna_pinyin.userdb" "$backup"
    fi
  '
  # 传输时在远端直接展开，避免中间产生可读的临时归档。
  ssh "${ssh_options[@]}" "$TARGET" 'tar -xzf - -C /home/liou/.local/share/fcitx5/rime' < "$SNAPSHOT"
  ssh "${ssh_options[@]}" "$TARGET" 'chown -R liou:users /home/liou/.local/share/fcitx5/rime/luna_pinyin.userdb'
  echo "Rime userdb 已部署到 $TARGET"
}

case "${1:-}" in
  snapshot)
    snapshot
    ;;
  deploy)
    deploy
    ;;
  *)
    echo "用法: $0 snapshot | deploy [user@host]" >&2
    exit 2
    ;;
esac
