#!/usr/bin/env bash
# 创建或补充通用 KeePassXC 密钥库，并导入 nix-tools 的 git-crypt key。
# 密码只在本地终端输入，不会经过参数、环境变量或仓库。
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
key_file="${NIX_TOOLS_GIT_CRYPT_KEY:-$secrets_dir/nix-tools-git-crypt.key}"
sync_dir="${NIX_TOOLS_SYNC_DIR:-$HOME/Sync/secrets}"
vault_file="${NIX_TOOLS_VAULT_FILE:-$sync_dir/secrets.kdbx}"
entry_path="${NIX_TOOLS_GIT_CRYPT_ENTRY:-nix-tools/git-crypt-key}"
attachment_name="${NIX_TOOLS_GIT_CRYPT_ATTACHMENT:-nix-tools-git-crypt.key}"
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -s "$key_file" ]]; then
  for legacy_key in "$repo_dir/nix-tools-git-crypt.key" "$repo_dir/git-crypt-key"; do
    if [[ -s "$legacy_key" ]]; then
      key_file="$legacy_key"
      break
    fi
  done
fi

[[ -s "$key_file" ]] || {
  echo "错误：找不到 git-crypt key。" >&2
  echo "预期位置：$secrets_dir/nix-tools-git-crypt.key" >&2
  exit 1
}

umask 077
install -d -m 700 "$sync_dir"

if [[ -e "$vault_file" && ! -f "$vault_file" ]]; then
  echo "错误：KeePassXC 路径不是普通文件：$vault_file" >&2
  exit 1
fi

if [[ ! -e "$vault_file" ]]; then
  echo "将创建加密库：$vault_file"
  echo "请在下面的 KeePassXC 提示中输入并确认一个主密码；不要把它发给我或写进配置。"
  keepassxc-cli db-create --set-password "$vault_file"
else
  echo "使用已有 KeePassXC 加密库：$vault_file"
fi

group_path="${entry_path%%/*}"
if [[ "$entry_path" == */* ]]; then
  group_exists=0
  group_listing=""
  set +e
  group_listing="$(keepassxc-cli ls "$vault_file" /)"
  list_status=$?
  set -e
  if (( list_status != 0 )); then
    echo "错误：无法打开 KeePassXC 加密库；请确认主密码正确。" >&2
    exit 1
  fi
  if grep -Eq "^${group_path}/?$" <<<"$group_listing"; then
    group_exists=1
  fi
  if (( ! group_exists )); then
    keepassxc-cli mkdir "$vault_file" "$group_path"
  fi
fi

entry_exists=0
set +e
keepassxc-cli show "$vault_file" "$entry_path" >/dev/null
show_status=$?
set -e
if (( show_status == 0 )); then
  entry_exists=1
else
  echo "创建 KeePassXC 条目：$entry_path"
  # --no-password is a database access flag (it disables the master
  # password), not a request to leave the new entry password empty.
  # Omitting it keeps the database protected while add creates an entry
  # without an entry-password prompt.
  keepassxc-cli add \
    --notes "Encrypted git-crypt key for the nix-tools repository. Export only when needed." \
    "$vault_file" "$entry_path"
fi

if (( entry_exists )); then
  echo "条目已存在，保留条目内容并覆盖同名附件：$attachment_name"
else
  echo "导入 git-crypt key 附件：$attachment_name"
fi
keepassxc-cli attachment-import --force \
  "$vault_file" "$entry_path" "$attachment_name" "$key_file"

chmod 600 "$vault_file"
echo "完成：KeePassXC 加密库已准备好。"
echo "数据库位置：$vault_file"
echo "条目位置：$entry_path"
echo "后续需要本机文件时运行：scripts/export-git-crypt-key.sh"
