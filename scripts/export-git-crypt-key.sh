#!/usr/bin/env bash
# 从通用 KeePassXC 加密库导出 nix-tools 的 git-crypt key 到本机配置目录。
# 密码只在本地终端输入，key 内容不会打印到终端。
set -euo pipefail

if [[ ! -t 0 || ! -t 1 ]]; then
  echo "错误：此脚本必须在本机交互式终端中运行，不能通过 SSH 管道或 CI 输入主密码。" >&2
  exit 2
fi

command -v keepassxc-cli >/dev/null 2>&1 || {
  echo "错误：找不到 keepassxc-cli，请先通过 Home Manager 安装 KeePassXC。" >&2
  exit 1
}

config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
secrets_dir="${NIX_TOOLS_SECRETS_DIR:-$config_home/secrets}"
destination="${NIX_TOOLS_GIT_CRYPT_KEY:-$secrets_dir/nix-tools-git-crypt.key}"
sync_dir="${NIX_TOOLS_SYNC_DIR:-$HOME/Sync/secrets}"
vault_file="${NIX_TOOLS_VAULT_FILE:-$sync_dir/secrets.kdbx}"
entry_path="${NIX_TOOLS_GIT_CRYPT_ENTRY:-nix-tools/git-crypt-key}"
attachment_name="${NIX_TOOLS_GIT_CRYPT_ATTACHMENT:-nix-tools-git-crypt.key}"

[[ -f "$vault_file" ]] || {
  echo "错误：找不到 KeePassXC 加密库：$vault_file" >&2
  echo "请先运行 scripts/init-secret-vault.sh，或设置 NIX_TOOLS_VAULT_FILE。" >&2
  exit 1
}

umask 077
install -d -m 700 "$secrets_dir"
tmp_file="$(mktemp "$secrets_dir/.nix-tools-git-crypt.key.XXXXXX")"
cleanup() {
  rm -f -- "$tmp_file"
}
trap cleanup EXIT

echo "请在下面输入 KeePassXC 主密码。"
keepassxc-cli attachment-export \
  "$vault_file" "$entry_path" "$attachment_name" "$tmp_file"

[[ -s "$tmp_file" ]] || {
  echo "错误：导出的附件为空，已拒绝安装。" >&2
  exit 1
}

chmod 600 "$tmp_file"
install -m 600 "$tmp_file" "$destination"
chmod 600 "$destination"
echo "已导出 nix-tools git-crypt key：$destination"
echo "文件权限已设为 600；文件未写入 Git，也未写入 Syncthing 同步目录。"
