# clipboard-sync systemd user service（home-manager 模块）
#
# homebox / nuc 共享（homeConfigurations.liou / liou-nuc 都 import home.nix）。
#
# 二进制来源（优先级）：
#   1. ~/.local/bin/clipboard-sync —— activation 脚本从 nix-tools/bin 同步的
#      统一 release 二进制（`just deploy-linux` 安装到 nix-tools/bin）
#   2. nix-tools/bin/clipboard-sync —— 直接来源
#   3. 项目内 cargo 编译的 debug 二进制（fallback）
# 这样 nix-tools 换位置也不影响，~/.local/bin 位置稳定。

{ config, pkgs, lib, ... }:

{
  # switch 时把 nix-tools/bin/clipboard-sync 同步到 ~/.local/bin/
  # （若存在；不存在则静默跳过，wrapper 会 fallback 到项目 debug 版）
  home.activation.clipboardSyncBin = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    run() {
      if [ -x "$1" ]; then
        install -m 755 "$1" "$HOME/.local/bin/clipboard-sync"
        echo "clipboard-sync: installed $1 -> $HOME/.local/bin/clipboard-sync"
      fi
    }
    run "$HOME/project/nix-tools/bin/clipboard-sync"
    run "$HOME/dufs-lan/project/nix-tools/bin/clipboard-sync"
  '';

  systemd.user.services.clipboard-sync = {
    Unit = {
      Description = "clipboard-sync daemon (LAN clipboard/file sync)";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };
    Service = {
      # wrapper：优先 ~/.local/bin（activation 同步），fallback 到项目 debug 版
      ExecStart = "${pkgs.writeShellScript "clipboard-sync-start" ''
        set -eu
        HOME_DIR="''${HOME:-/home/$(id -un)}"
        BIN=""
        for p in \
          "$HOME_DIR/.local/bin/clipboard-sync" \
          "$HOME_DIR/project/nix-tools/clipboard-sync/target/debug/clipboard-sync" \
          "$HOME_DIR/dufs-lan/project/nix-tools/clipboard-sync/target/debug/clipboard-sync"
        do
          if [ -x "$p" ]; then
            BIN="$p"
            break
          fi
        done
        if [ -z "$BIN" ]; then
          echo "clipboard-sync binary not found (checked ~/.local/bin and project target/debug)" >&2
          exit 1
        fi
        # 探测 Wayland 会话 socket（最多等 30s，避免登录前空跑）
        for i in $(seq 1 30); do
          if [ -S "''${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/''${WAYLAND_DISPLAY:-wayland-1}" ]; then
            break
          fi
          sleep 1
        done
        export WAYLAND_DISPLAY="''${WAYLAND_DISPLAY:-wayland-1}"
        export XDG_RUNTIME_DIR="''${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
        # DBus（通知走 notify-rust / mako）
        export DBUS_SESSION_BUS_ADDRESS="''${DBUS_SESSION_BUS_ADDRESS:-unix:path=''${XDG_RUNTIME_DIR}/bus}"
        # zenity（接收/拒绝对话框）不在 systemd 默认 PATH：
        # standalone hm 的 profile 在 ~/.local/state/nix/profiles/home-manager/home-path/bin，
        # NixOS 集成时在 /run/current-system/sw/bin
        export PATH="$HOME/.local/state/nix/profiles/home-manager/home-path/bin:/run/current-system/sw/bin:$PATH"
        exec "$BIN"
      ''}";
      Restart = "on-failure";
      RestartSec = "5";
      # 崩溃后最多等 30s（探测 Wayland）
      TimeoutStartSec = "35";
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };
}
