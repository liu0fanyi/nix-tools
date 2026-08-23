#!/usr/bin/env bash
# 检测 nu rerun.nu 后 home-manager 是否正常更新到当前 git 状态。
# 用法: bash scripts/check-home-update.sh
# 也可在 rerun.nu 后自动调用（见 rerun.nu 的说明）。
set -uo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

say() { printf '%s\n' "$*"; }
ok()  { printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[31m✗\033[0m %s\n' "$*"; FAIL=1; }

say ""
say "=== home-manager 更新检测（$REPO_DIR）==="

# ── 1. 生效 home-manager 指针与当前 git 构建结果是否一致 ──
# home-manager >= 24.11 以 ~/.local/state/nix/profiles/home-manager 为真实生效
# generation（switch 会更新它）；旧 current-home 已废弃不再维护（会停在旧值），
# 故这里读 profile 链接，与 rerun.nu 自检保持一致。
say ""
say "[1] home-manager 生效指针是否等于当前 git 状态构建出的 generation"
current="$(readlink -f "$HOME/.local/state/nix/profiles/home-manager" 2>/dev/null || true)"
expected="$(nix build --no-link --print-out-paths "$REPO_DIR#nixosConfigurations.homebox.config.home-manager.users.liou.home.activationPackage" 2>/dev/null | tail -1 || true)"
if [[ -n "$current" && "$current" == "$expected" ]]; then
  ok "生效指针 == 构建结果: $current"
else
  bad "不一致:"
  bad "  生效指针: $current"
  bad "  构建结果: $expected"
  bad "  （需要再跑 nu rerun.nu，或 flake 有未提交改动未包含）"
fi

# ── 2. 关键文件是否已部署 ──
say ""
say "[2] 关键文件部署检查"
check_file() {
  local desc="$1" path="$2" pat="$3"
  if [[ -e "$path" ]]; then
    if [[ -n "$pat" ]] && ! grep -q "$pat" "$path" 2>/dev/null; then
      bad "$desc 存在但内容不符（缺 '$pat'）: $path"
    else
      ok "$desc: $path"
    fi
  else
    bad "$desc 缺失: $path"
  fi
}
check_file "SSH config（nuc.local）" "$HOME/.ssh/config" "HostName nuc.local"
check_file "dsh-web systemd service" "$HOME/.config/systemd/user/dsh-web.service" "ExecStart=.*dsh web"
check_file "dsh-web toggle 脚本" "$HOME/.local/bin/dsh-web-toggle" "notify="
check_file "dsh wrapper（--expose-internals）" "$HOME/.local/bin/dsh" "expose-internals"

# ── 3. systemd user service 是否被 systemd 识别 ──
say ""
say "[3] dsh-web.service 状态"
if systemctl --user list-unit-files 2>/dev/null | grep -q "^dsh-web.service"; then
  ok "systemd 已识别 dsh-web.service"
  st="$(systemctl --user is-active dsh-web 2>/dev/null || true)"
  if [[ "$st" == "active" ]]; then
    ok "dsh-web 正在运行"
  else
    bad "dsh-web 状态: $st（期望 active，可 systemctl --user start dsh-web）"
  fi
else
  bad "systemd 未识别 dsh-web.service（home-manager 可能未正确激活）"
fi

# ── 4. activation 是否在 switch 中实际执行（看日志或时间戳）──
say ""
say "[4] home-manager activation 时间 vs NixOS switch 时间"
hm_gen_target="$(readlink -f "$current" 2>/dev/null || true)"
hm_gen_time="$(stat -c '%y' "$hm_gen_target" 2>/dev/null | cut -d. -f1 || true)"
nixos_gen="$(nixos-rebuild list-generations 2>/dev/null | grep -oP '^Current\s+\S+' | head -1)"
sys_time="$(nixos-rebuild list-generations 2>/dev/null | awk 'NR==1 || /Current/' | head -2 | tail -1 | awk '{print $2, $3}')"
if [[ -n "$hm_gen_time" ]]; then
  ok "home-manager generation 时间: $hm_gen_time"
  say "   NixOS current generation 时间: $sys_time"
  say "   （若 home-manager 时间明显早于 NixOS，说明 switch 可能没重新激活 home-manager）"
else
  bad "无法获取 home-manager generation 时间"
fi

# ── 5. 本地 git 是否干净（有未提交改动则结果可能不完整）──
say ""
say "[5] git 工作树状态"
if [[ -z "$(cd "$REPO_DIR" && git status --porcelain 2>/dev/null)" ]]; then
  ok "工作树干净（检测基于已提交状态）"
else
  say "  ⚠ 有未提交改动（检测基于 git 已提交内容，未提交改动不会生效）:"
  (cd "$REPO_DIR" && git status --porcelain 2>/dev/null | head -5 | sed 's/^/     /')
fi

say ""
if (( FAIL )); then
  printf '结果: \033[31m存在失败项，home-manager 未完全更新\033[0m。先跑 nu rerun.nu 再看。\n'
  exit 1
else
  printf '结果: \033[32m全部通过，home-manager 已是最新\033[0m。\n'
  exit 0
fi
