#!/usr/bin/env bash
# 在 KeePassXC 加密库与 deploy/secrets/ 之间导入/导出 DUFS Plus 运行时 secrets。
# 对标 scripts/export-git-crypt-key.sh 的模式：secrets 作为加密附件存放在
# Syncthing 同步的 secrets.kdbx 里，按需导出到本机明文目录使用。
#
# 用法:
#   bash scripts/manage-dufs-secrets.sh import   # deploy/secrets/* → KeePassXC 附件
#   bash scripts/manage-dufs-secrets.sh export   # KeePassXC 附件 → deploy/secrets/*
#   bash scripts/manage-dufs-secrets.sh list     # 列出 KeePassXC 中已保管的 secrets
#
# 安全说明:
#   - 必须在本机交互式终端运行（防 SSH 管道/CI 泄露主密码）
#   - 主密码只由 keepassxc-cli 交互提示输入，不经过参数/环境变量
#   - 导出到明文目录时自动设置 0700/0600 权限
set -euo pipefail

if [[ ! -t 0 || ! -t 1 ]]; then
  echo "错误：此脚本必须在本机交互式终端中运行，不能通过 SSH 管道或 CI 输入主密码。" >&2
  exit 2
fi

command -v keepassxc-cli >/dev/null 2>&1 || {
  echo "错误：找不到 keepassxc-cli，请先通过 Home Manager 安装 KeePassXC。" >&2
  exit 1
}

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
secrets_dir="${NIX_TOOLS_DEPLOY_SECRETS_DIR:-$repo_dir/deploy/secrets}"
sync_dir="${NIX_TOOLS_SYNC_DIR:-$HOME/Sync/secrets}"
vault_file="${NIX_TOOLS_VAULT_FILE:-$sync_dir/secrets.kdbx}"
entry_path="${NIX_TOOLS_DUFS_SECRETS_ENTRY:-dufs-plus/secrets}"
# 附件名用固定集合，与 deploy/secrets/README.md 列出的必需文件一致
# （不含 README.md/.gitignore 这两个仓库内文件）。
secret_files=(
  authelia_jwt_secret
  authelia_session_secret
  authelia_storage_key
  authelia_users_database.yml
  dufs-readonly.yaml
  caddy_lan_basic_auth
  tag-server.env
)

[[ -f "$vault_file" ]] || {
  echo "错误：找不到 KeePassXC 加密库：$vault_file" >&2
  echo "请先运行 scripts/init-secret-vault.sh，或设置 NIX_TOOLS_VAULT_FILE。" >&2
  exit 1
}

action="${1:-help}"
case "$action" in
  import)
    umask 077
    missing=0
    for f in "${secret_files[@]}"; do
      if [[ ! -s "$secrets_dir/$f" ]]; then
        echo "警告：$secrets_dir/$f 不存在或为空（跳过，可选文件可忽略）" >&2
        missing=1
      fi
    done
    if (( missing )); then
      echo "提示：缺失的文件将跳过；可选的 tag-server.env 缺失不影响主流程。" >&2
    fi
    # 确保条目存在（--no-password 是数据库访问标志，不是让条目密码为空）
    if ! keepassxc-cli show "$vault_file" "$entry_path" >/dev/null 2>&1; then
      echo "创建 KeePassXC 条目：$entry_path"
      group_path="${entry_path%%/*}"
      keepassxc-cli ls "$vault_file" / | grep -q "^${group_path}/?$" || \
        keepassxc-cli mkdir "$vault_file" "$group_path"
      keepassxc-cli add \
        --notes "DUFS Plus runtime secrets (Authelia/Caddy/DUFS). Export to deploy/secrets/ when needed." \
        "$vault_file" "$entry_path"
    fi
    for f in "${secret_files[@]}"; do
      [[ -s "$secrets_dir/$f" ]] || continue
      echo "导入 $f ..."
      keepassxc-cli attachment-import --force \
        "$vault_file" "$entry_path" "$f" "$secrets_dir/$f"
    done
    echo "完成：DUFS Plus secrets 已导入 KeePassXC。"
    echo "条目：$entry_path（附件：${secret_files[*]}）"
    ;;
  export)
    umask 077
    install -d -m 700 "$secrets_dir"
    for f in "${secret_files[@]}"; do
      echo "导出 $f ..."
      keepassxc-cli attachment-export \
        "$vault_file" "$entry_path" "$f" "$secrets_dir/.$f.tmp" 2>/dev/null \
        && mv -f "$secrets_dir/.$f.tmp" "$secrets_dir/$f" \
        || {
          rm -f "$secrets_dir/.$f.tmp"
          echo "跳过：条目中无附件 $f" >&2
        }
      chmod 600 "$secrets_dir/$f" 2>/dev/null || true
    done
    chmod 700 "$secrets_dir"
    echo "完成：DUFS Plus secrets 已导出到 $secrets_dir"
    echo "（目录 0700，文件 0600；这些文件不应加入 Git）"
    ;;
  list)
    keepassxc-cli show --all "$vault_file" "$entry_path" 2>/dev/null \
      || echo "条目 $entry_path 不存在（先运行 import）。" >&2
    ;;
  *)
    echo "用法: bash scripts/manage-dufs-secrets.sh {import|export|list}" >&2
    exit 1
    ;;
esac
