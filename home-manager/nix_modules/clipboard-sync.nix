# clipboard-sync systemd user service（home-manager 模块）
#
# homebox / nuc 共享（homeConfigurations.liou / liou-nuc 都 import home.nix）。
#
# 二进制来源：activation 从已知的 nix-tools/bin 位置同步 release 二进制到
# ~/.local/bin/clipboard-sync，service 始终只运行这个稳定路径。
# 这样 nix-tools 换位置也不影响，~/.local/bin 位置稳定。

{ config, pkgs, lib, ... }:

{
  # switch 时把 nix-tools/bin/clipboard-sync 同步到 ~/.local/bin/
  # （若存在；不存在则保留上一次成功安装的 release 二进制）
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
      # wrapper：只运行 activation 安装的稳定 release 二进制。
      ExecStart = "${pkgs.writeShellScript "clipboard-sync-start" ''
        set -eu
        HOME_DIR="''${HOME:-/home/$(id -un)}"
        BIN="$HOME_DIR/.local/bin/clipboard-sync"
        if [ ! -x "$BIN" ]; then
          echo "clipboard-sync release binary not found: $BIN" >&2
          exit 1
        fi
        # 不假设 compositor 固定使用 wayland-1。若 user manager 没继承变量，
        # 从 runtime dir 中选择真实存在的 socket；X11 则保留 DISPLAY。
        export XDG_RUNTIME_DIR="''${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
        if [ -z "''${WAYLAND_DISPLAY:-}" ]; then
          for socket in "$XDG_RUNTIME_DIR"/wayland-*; do
            if [ -S "$socket" ]; then
              export WAYLAND_DISPLAY="''${socket##*/}"
              break
            fi
          done
        fi
        # DBus（通知走 notify-rust / mako）
        export DBUS_SESSION_BUS_ADDRESS="''${DBUS_SESSION_BUS_ADDRESS:-unix:path=''${XDG_RUNTIME_DIR}/bus}"
        # 运行期工具都从当前 Home Manager generation 获取，不依赖 NixOS profile。
        export PATH="${lib.makeBinPath [ pkgs.zenity pkgs.iproute2 ]}:$PATH"
        exec "$BIN"
      ''}";
      Restart = "on-failure";
      RestartSec = "5";
      TimeoutStartSec = "15";
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };
}
