# clipboard-sync systemd user service（home-manager 模块）
#
# homebox / nuc 共享（homeConfigurations.liou / liou-nuc 都 import home.nix）。
#
# 二进制由父 flake 的 buildRustPackage 构建，service 直接引用锁定的 Nix store 路径。

{ config, pkgs, lib, clipboardSyncPackage, ... }:

{
  home.packages = [ clipboardSyncPackage ];

  # 共享密钥仍只在 activation 运行时从已解锁仓库复制，绝不进入 Nix store。
  home.activation.clipboardSyncKey = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    install_key() {
      if [ -f "$1" ]; then
        mkdir -p "$HOME/.config/clipboard-sync"
        chmod 700 "$HOME/.config/clipboard-sync"
        install -m 600 "$1" "$HOME/.config/clipboard-sync/shared-key"
        echo "clipboard-sync: installed authentication key"
        return 0
      fi
      return 1
    }
    install_key "$HOME/project/nix-tools/secrets/clipboard-sync/shared-key" || \
      install_key "$HOME/dufs-lan/project/nix-tools/secrets/clipboard-sync/shared-key" || \
      echo "clipboard-sync: authentication key not found; service will not start" >&2
  '';

  systemd.user.services.clipboard-sync = {
    Unit = {
      Description = "clipboard-sync daemon (LAN clipboard/file sync)";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };
    Service = {
      # wrapper 负责补齐桌面会话环境，二进制直接来自锁定的 Nix package。
      ExecStart = "${pkgs.writeShellScript "clipboard-sync-start" ''
        set -eu
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
        exec "${clipboardSyncPackage}/bin/clipboard-sync"
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
