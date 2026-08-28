#!/usr/bin/env bash
# 统一的 KeePassXC 密钥库管理脚本（数据库驱动，目录与库结构对齐）。
#
# 对齐规则：
#   KeePassXC 组 <name>  ↔  明文目录 ~/.config/secrets/<name>/
#   组内条目的附件       ↔  目录内的文件（附件名 = 文件名）
#
# 新增密钥集：在 KeePassXC 建一个组（或在 ~/.config/secrets/ 建同名目录），
# 无需修改本脚本。
#
# 用法:
#   bash scripts/vault.sh list              # 列出库中所有组（需要主密码）
#   bash scripts/vault.sh <组名> export     # 组内所有条目附件 → ~/.config/secrets/<组>/
#   bash scripts/vault.sh <组名> import     # ~/.config/secrets/<组>/ 下文件 → 组内条目附件
#   bash scripts/vault.sh <组名> list       # 查看该组条目及附件
#   bash scripts/vault.sh init              # 创建加密库（首次使用）
#
# import 规则：目录中每个文件作为一个附件，导入到组内同名条目
#   （条目 <组>/<文件名>，附件名 <文件名>）；若条目不存在则自动创建。
#   - ~/.config/secrets/<组>/*.key  →  条目 <组>/<文件名>，附件 <文件名>
#   - 目录下每个文件独立成条目，方便在 KeePassXC 里按条目管理。
#
# 安全说明:
#   - 必须在本机交互式终端运行（防 SSH 管道/CI 泄露主密码）
#   - 主密码只读入一次并经 stdin 传给 keepassxc-cli，不经过参数/环境变量/磁盘
#   - 导出到明文目录时自动设置 0700/0600 权限
#   - 明文文件只放 ~/.config/secrets/（不入 Git，也不放回 Syncthing 同步目录）
set -euo pipefail

config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
base_dir="${NIX_TOOLS_VAULT_BASE:-$config_home/secrets}"       # 明文根目录
sync_dir="${NIX_TOOLS_SYNC_DIR:-$HOME/Sync/secrets}"
vault_file="${NIX_TOOLS_VAULT_FILE:-$sync_dir/secrets.kdbx}"

if [[ ! -t 0 || ! -t 1 ]]; then
  echo "错误：此脚本必须在本机交互式终端中运行，不能通过 SSH 管道或 CI 输入主密码。" >&2
  exit 2
fi

command -v keepassxc-cli >/dev/null 2>&1 || {
  echo "错误：找不到 keepassxc-cli，请先通过 Home Manager 安装 KeePassXC。" >&2
  exit 1
}

[[ -f "$vault_file" ]] || {
  echo "错误：找不到 KeePassXC 加密库：$vault_file" >&2
  echo "请先运行 bash scripts/vault.sh init，或设置 NIX_TOOLS_VAULT_FILE。" >&2
  exit 1
}

if [[ "${1:-}" == "init" ]]; then
  umask 077
  install -d -m 700 "$sync_dir"
  if [[ ! -e "$vault_file" ]]; then
    echo "将创建加密库：$vault_file"
    echo "请在下面的 KeePassXC 提示中输入并确认一个主密码；不要把它写进配置。"
    keepassxc-cli db-create --set-password "$vault_file"
  else
    echo "使用已有 KeePassXC 加密库：$vault_file"
  fi
  chmod 600 "$vault_file"
  echo "完成：KeePassXC 加密库已就绪：$vault_file"
  exit 0
fi

# Read the database password once. Keep it only in this shell process; each
# keepassxc-cli invocation receives it through stdin, never argv, env, or disk.
read -r -s -p "KeePassXC database password: " vault_password
printf '\n'
trap 'unset vault_password' EXIT
vault_cli() {
  local command_name="$1"
  shift
  printf '%s\n' "$vault_password" |
    LC_ALL=C keepassxc-cli "$command_name" --quiet "$@"
}

if [[ "${1:-}" == "list" && $# -eq 1 ]]; then
  echo "KeePassXC 库顶层组（↔ ~/.config/secrets/<组>/）："
  vault_cli ls "$vault_file" / 2>/dev/null | sed 's#/$##' | sed 's/^/  /'
  exit 0
fi

[[ $# -eq 2 ]] || {
  echo "用法: bash scripts/vault.sh <组名> {import|export|list}" >&2
  echo "      bash scripts/vault.sh init   # 创建加密库（首次使用）" >&2
  echo "      bash scripts/vault.sh list   # 列出库中所有组" >&2
  exit 1
}

group_name="$1"
group_path="/${group_name#/}"
action="$2"
secrets_dir="$base_dir/$group_name"

# 组是否存在（列出组下内容验证；不存在则报错并显示顶层组）
group_exists() {
  vault_cli ls "$vault_file" "$group_path" >/dev/null 2>&1
}

case "$action" in
  list)
    if ! group_exists; then
      echo "错误：库中不存在组 $group_name。" >&2
      echo "顶层组：" >&2
      vault_cli ls "$vault_file" / 2>/dev/null | sed 's#/$##' | sed 's/^/  /' >&2
      exit 1
    fi
    echo "组 $group_name 的条目及附件："
    # 条目 = ls 输出中不带斜杠的行；子组 = 带斜杠行
    while IFS= read -r item; do
      [[ -z "$item" ]] && continue
      if [[ "$item" == */ ]]; then
        echo "  [子组] ${item%/}"
      else
        # 显示该条目的附件
        atts="$(vault_cli show --all "$vault_file" "$group_path/$item" 2>/dev/null \
          | sed -n 's/^Attachments: //p')"
        echo "  $item"
        [[ -n "$atts" ]] && IFS=', ' read -r -a a <<< "$atts" && for x in "${a[@]}"; do
          [[ -n "$x" ]] && echo "      ↳ $x"
        done
      fi
    done < <(vault_cli ls "$vault_file" "$group_path" 2>/dev/null)
    ;;
  import)
    umask 077
    install -d -m 700 "$secrets_dir"
    shopt -s nullglob
    files=("$secrets_dir"/*)
    shopt -u nullglob
    [[ ${#files[@]} -gt 0 ]] || {
      echo "错误：$secrets_dir 下没有文件可导入。" >&2
      exit 1
    }
    # 确保组存在
    group_exists || vault_cli mkdir "$vault_file" "$group_path" 2>/dev/null || true
    imported=0
    for f in "${files[@]}"; do
      [[ -f "$f" ]] || continue
      name="$(basename "$f")"
      entry_path="$group_path/$name"
      # 条目不存在则创建（--no-password 是数据库访问标志，不是让条目密码为空）
      if ! vault_cli show "$vault_file" "$entry_path" >/dev/null 2>&1; then
        vault_cli add \
          --notes "Imported by vault.sh from $secrets_dir" \
          "$vault_file" "$entry_path"
      fi
      echo "导入 $name → $entry_path ..."
      vault_cli attachment-import --force \
        "$vault_file" "$entry_path" "$name" "$f"
      imported=$((imported + 1))
    done
    echo "完成：${#files[@]} 个文件已导入组 $group_name（$imported 个条目）。"
    ;;
  export)
    umask 077
    install -d -m 700 "$secrets_dir"
    if ! group_exists; then
      echo "错误：库中不存在组 $group_name。" >&2
      exit 1
    fi
    exported=0
    # vault.sh imports each file as an entry with an attachment of the same name.
    # KeePassXC 2.7 does not expose attachment names through `show --all`, so
    # export by that stable convention and skip unrelated entries safely.
    while IFS= read -r item; do
      [[ -z "$item" || "$item" == */ ]] && continue
      tmp="$secrets_dir/.$item.tmp"
      echo "导出 $item ..."
      if vault_cli attachment-export \
        "$vault_file" "$group_path/$item" "$item" "$tmp" 2>/dev/null; then
        mv -f "$tmp" "$secrets_dir/$item"
        chmod 600 "$secrets_dir/$item"
        exported=$((exported + 1))
      else
        rm -f "$tmp"
        echo "跳过 $item：没有同名附件" >&2
      fi
    done < <(vault_cli ls "$vault_file" "$group_path" 2>/dev/null)
    if (( exported == 0 )); then
      echo "错误：组 $group_name 下没有找到任何附件（import 可能未成功）。" >&2
      exit 1
    fi
    chmod 700 "$secrets_dir"
    echo "完成：$exported 个附件已导出到 $secrets_dir"
    echo "（目录 0700，文件 0600；这些文件不应加入 Git）"
    ;;
  *)
    echo "用法: bash scripts/vault.sh <组名> {import|export|list}" >&2
    exit 1
    ;;
esac
