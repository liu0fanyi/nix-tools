#!/usr/bin/env bash
# 统一的 KeePassXC 密钥库管理脚本。
# 所有密钥（git-crypt key、DUFS Plus secrets、未来任何密钥文件）都以
# 加密附件形式存放在同一个 Syncthing 同步的 secrets.kdbx 里，按需导出到
# 本机 ~/.config/secrets/ 下的对应子目录使用。
#
# 用法:
#   bash scripts/vault.sh <profile> import   # 本机明文目录 → KeePassXC 附件
#   bash scripts/vault.sh <profile> export   # KeePassXC 附件 → 本机明文目录
#   bash scripts/vault.sh <profile> list     # 查看该 profile 已保管的附件
#   bash scripts/vault.sh list               # 列出所有可用 profile
#
# Profile 定义在下面的 profiles 关联数组中；新增密钥只需加一行：
#   [条目路径]="本机明文目录"
# 文件清单放在 scripts/vault/<目录名>.files（进 git，每行一个文件名）。
#
# 安全说明:
#   - 必须在本机交互式终端运行（防 SSH 管道/CI 泄露主密码）
#   - 主密码只由 keepassxc-cli 交互提示输入，不经过参数/环境变量
#   - 导出到明文目录时自动设置 0700/0600 权限
#   - 明文文件只放 ~/.config/secrets/（不入 Git，也不放回 Syncthing 同步目录）
set -euo pipefail

config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
base_dir="${NIX_TOOLS_VAULT_BASE:-$config_home/secrets}"       # 明文根目录
sync_dir="${NIX_TOOLS_SYNC_DIR:-$HOME/Sync/secrets}"
vault_file="${NIX_TOOLS_VAULT_FILE:-$sync_dir/secrets.kdbx}"

# 声明式 profile：KeePassXC 条目路径 => 本机明文子目录（相对 base_dir）
# 文件清单放在 scripts/vault/<dir>.files（进 git，每行一个文件名）。
declare -A profiles=(
  ["nix-tools/git-crypt-key"]="nix-tools"
  ["dufs-plus/secrets"]="dufs-plus"
)

# 仅列出 profile 不需要解锁库，放 TTY 检查之前
if [[ "${1:-}" == "list" && $# -eq 1 ]]; then
  echo "可用 profile："
  for entry in "${!profiles[@]}"; do
    printf "  %-30s → %s\n" "$entry" "${profiles[$entry]}"
  done
  exit 0
fi

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

# 解析 profile：传入条目路径或别名（目录名）均可
resolve_profile() {
  local want="$1"
  for entry in "${!profiles[@]}"; do
    local dir="${profiles[$entry]}"
    if [[ "$entry" == "$want" || "$dir" == "$want" ]]; then
      echo "$entry|$dir"
      return 0
    fi
  done
  return 1
}

if [[ "${1:-}" == "list" && $# -eq 1 ]]; then
  echo "可用 profile："
  for entry in "${!profiles[@]}"; do
    printf "  %-30s → %s\n" "$entry" "${profiles[$entry]}"
  done
  exit 0
fi

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
  echo "接下来运行 bash scripts/vault.sh <profile> import 导入密钥。"
  exit 0
fi

[[ $# -eq 2 ]] || {
  echo "用法: bash scripts/vault.sh <profile> {import|export|list}" >&2
  echo "      bash scripts/vault.sh init   # 创建加密库（首次使用）" >&2
  echo "      bash scripts/vault.sh list   # 列出所有 profile" >&2
  exit 1
}

resolved="$(resolve_profile "$1")" || {
  echo "错误：未知 profile：$1" >&2
  echo "可用：$(printf '%s ' "${!profiles[@]}")" >&2
  exit 1
}
entry_path="${resolved%%|*}"
dir_name="${resolved##*|}"
secrets_dir="$base_dir/$dir_name"
files_list="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/vault/$dir_name.files"

action="$2"
case "$action" in
  import)
    umask 077
    install -d -m 700 "$secrets_dir"
    [[ -s "$files_list" ]] || {
      echo "错误：缺少文件清单 $files_list（每行一个要保管的文件名）。" >&2
      exit 1
    }
    mapfile -t secret_files < "$files_list"
    # 确保 KeePassXC 条目存在
    if ! keepassxc-cli show "$vault_file" "$entry_path" >/dev/null 2>&1; then
      echo "创建 KeePassXC 条目：$entry_path"
      group_path="${entry_path%%/*}"
      if [[ "$entry_path" == */* ]]; then
        keepassxc-cli ls "$vault_file" / 2>/dev/null | grep -q "^${group_path}/?$" || \
          keepassxc-cli mkdir "$vault_file" "$group_path"
      fi
      keepassxc-cli add \
        --notes "Encrypted secrets for $entry_path. Export to $secrets_dir when needed." \
        "$vault_file" "$entry_path"
    fi
    for f in "${secret_files[@]}"; do
      [[ -n "$f" ]] || continue
      if [[ ! -s "$secrets_dir/$f" ]]; then
        echo "警告：$secrets_dir/$f 不存在或为空，跳过" >&2
        continue
      fi
      echo "导入 $f ..."
      keepassxc-cli attachment-import --force \
        "$vault_file" "$entry_path" "$f" "$secrets_dir/$f"
    done
    echo "完成：$entry_path 的密钥已导入 KeePassXC。"
    ;;
  export)
    umask 077
    install -d -m 700 "$secrets_dir"
    # 先确认条目存在，避免静默全部跳过
    if ! keepassxc-cli show "$vault_file" "$entry_path" >/dev/null 2>&1; then
      echo "错误：KeePassXC 中不存在条目 $entry_path。" >&2
      echo "可能原因：1) 另一台机器 import 时用了不同条目；2) secrets.kdbx 未同步。" >&2
      echo "先运行 bash scripts/vault.sh $1 list 查看实际条目。" >&2
      exit 1
    fi
    # 导出所有附件（枚举条目的附件名，不依赖 .vault-files）
    attachments="$(keepassxc-cli show --all "$vault_file" "$entry_path" 2>/dev/null \
      | sed -n 's/^Attachments: //p')"
    if [[ -z "$attachments" ]]; then
      echo "错误：条目 $entry_path 没有任何附件（import 可能未成功）。" >&2
      exit 1
    fi
    IFS=', ' read -r -a attach_names <<< "$attachments"
    for f in "${attach_names[@]}"; do
      [[ -n "$f" ]] || continue
      echo "导出 $f ..."
      keepassxc-cli attachment-export \
        "$vault_file" "$entry_path" "$f" "$secrets_dir/.$f.tmp" 2>/dev/null \
        && mv -f "$secrets_dir/.$f.tmp" "$secrets_dir/$f"
      chmod 600 "$secrets_dir/$f"
      rm -f "$secrets_dir/.$f.tmp"
    done
    chmod 700 "$secrets_dir"
    echo "完成：密钥已导出到 $secrets_dir"
    echo "（目录 0700，文件 0600；这些文件不应加入 Git）"
    ;;
  list)
    if keepassxc-cli show --all "$vault_file" "$entry_path" 2>/dev/null; then
      :
    else
      echo "条目 $entry_path 不存在。当前库中的顶层条目：" >&2
      keepassxc-cli ls "$vault_file" / 2>/dev/null || true
    fi
    ;;
  *)
    echo "用法: bash scripts/vault.sh <profile> {import|export|list}" >&2
    exit 1
    ;;
esac
