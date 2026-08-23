# clipboard-sync systemd user service（home-manager 模块）
#
# homebox / nuc 共享（homeConfigurations.liou / liou-nuc 都 import home.nix）。
#
# 说明：
# - 二进制是项目内 cargo 编译的（非 nix 包），两台机器路径不同：
#   - homebox: ~/project/clipboard-sync/target/debug/clipboard-sync
#   - nuc:     ~/dufs-lan/project/clipboard-sync/target/debug/clipboard-sync
#   wrapper 按顺序探测两个候选路径，找到哪个用哪个。
# - 需要图形会话（Wayland 剪贴板 + 通知），wrapper 探测 socket 就绪

{ config, pkgs, lib, ... }:

{
  systemd.user.services.clipboard-sync = {
    Unit = {
      Description = "clipboard-sync daemon (LAN clipboard/file sync)";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };
    Service = {
      # wrapper：等 Wayland socket 就绪后启动（graphical 会话已起）
      ExecStart = "${pkgs.writeShellScript "clipboard-sync-start" ''
        set -eu
        HOME_DIR="''${HOME:-/home/$(id -un)}"
        # 候选二进制路径（homebox / nuc 布局不同）
        BIN=""
        for p in \
          "$HOME_DIR/project/clipboard-sync/target/debug/clipboard-sync" \
          "$HOME_DIR/dufs-lan/project/clipboard-sync/target/debug/clipboard-sync"
        do
          if [ -x "$p" ]; then
            BIN="$p"
            break
          fi
        done
        if [ -z "$BIN" ]; then
          echo "clipboard-sync binary not found (checked ~/project and ~/dufs-lan/project)" >&2
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
