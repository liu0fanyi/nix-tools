#!/usr/bin/env bash
# 恢复目标机的加密 secrets（git-crypt 解锁 + 部署 mihomo 配置）
# 用法: ./scripts/restore-secrets.sh [user@host]
# 前置: git-crypt 已安装（nix shell nixpkgs#git-crypt 或 sudo apt install git-crypt），
#       且唯一密钥文件 git-crypt-key 存在（不在 git 里，注意备份）。
set -euo pipefail

TARGET="${1:-root@192.168.1.14}"
KEY_FILE="git-crypt-key"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

# 1. git-crypt 解锁（用唯一密钥）
if ! command -v git-crypt >/dev/null 2>&1; then
  echo "错误: 需要 git-crypt，请先安装（nix shell nixpkgs#git-crypt 或 sudo apt install git-crypt）" >&2
  exit 1
fi
if git-crypt status 2>/dev/null | grep -q "encrypted: secrets/"; then
  echo "解锁 git-crypt（$KEY_FILE）..."
  git-crypt unlock "$KEY_FILE"
fi

# 2. 安装 npm 全局包（dsh / dsh-tui / pnpm；~/.npmrc 由 home-manager 声明式提供）
echo "安装 npm 全局包到 $TARGET ..."
ssh "$TARGET" 'runuser -u liou -- env HOME=/home/liou bash -c "cd /home/liou && npm install -g @deepseek-ai/dsh @deepseek-harness-tui/dsh-tui pnpm 2>&1 | tail -3"'

# 3. 部署 mihomo 配置到目标机（订阅 URL 等 secrets）
echo "部署 mihomo 配置到 $TARGET ..."
ssh "$TARGET" 'mkdir -p /home/liou/.config/clashtui/mihomo'
scp -q secrets/mihomo-config.yaml "$TARGET":/home/liou/.config/clashtui/mihomo/config.yaml
ssh "$TARGET" 'chown liou:users /home/liou/.config/clashtui/mihomo/config.yaml && systemctl restart clashtui-mihomo && sleep 2 && systemctl is-active clashtui-mihomo && echo "mihomo 服务已恢复"'

echo "✅ secrets 恢复完成"
