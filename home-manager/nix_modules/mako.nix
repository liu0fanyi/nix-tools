# mako 通知守护进程配置（与 niri.nix 的 spawn-at-startup "mako" 配合）。
#
# 普通通知自动消失；需要用户决定的蓝牙请求保留操作入口。
#
# 背景：clipboard-sync 的 notify_accept_ok 用 notify-rust 且不设 timeout，
# notify-rust 默认 Timeout::Never → D-Bus expire_timeout=-1（永不超时），
# mako 对 -1 会一直显示直到被 dismiss；其他 daemon 也可能发 -1。
#
# 方案：ignore-timeout = true 让 mako 忽略应用声明的超时，
# 普通通知按 default-timeout（5 秒）消失，蓝牙交互请求例外。
#
# 仅在 NixOS（homebox）启用：非 NixOS（nuc）走 standalone home-manager，
# 其 niri 不启用（niri.nix 的 features.niri.enable = full.enable && isNixOS），
# 也不 spawn mako，因此 mako 配置不应作用于 nuc。
{ config, pkgs, lib, isNixOS ? false, ... }:
let
  bluetoothActions = pkgs.writeShellScript "mako-bluetooth-actions" ''
    export PATH=${lib.makeBinPath [ pkgs.jq pkgs.coreutils ]}:"$PATH"
    exec ${pkgs.mako}/bin/makoctl menu -n "$1" -- ${pkgs.fuzzel}/bin/fuzzel --dmenu --prompt='蓝牙操作： '
  '';
in
{
  config = lib.mkIf isNixOS {
    services.mako = {
      enable = true;
      settings = {
        # 所有通知统一 5 秒后自动消失（毫秒）
        default-timeout = 5000;
        # 忽略应用发的 expire_timeout（含 -1 永不超时），一律按 default-timeout
        ignore-timeout = true;

        # 外观：与 waybar 的 gruvbox 暗色主题协调
        font = "BigBlueTermPlus Nerd Font Mono 12";
        background-color = "#282828";
        text-color = "#ebdbb2";
        border-color = "#504945";
        border-size = 2;
        border-radius = 6;
        width = 380;
        height = 120;
        margin = 12;
        padding = 10;
        anchor = "top-right";
        # 最新通知排最前
        sort = "-time";

        # Mako 不绘制 action buttons；点击通知弹出该通知自己的动作菜单。
        # 不直接确认、不默认信任；Esc 可取消菜单，右键仍只关闭通知。
        "app-name=blueman actionable" = {
          # Blueman may leave an earlier request behind when replacing its
          # active notification. Never leave actionable authentication UI forever.
          default-timeout = 60000;
          ignore-timeout = true;
          history = false;
          height = 200;
          format = "<b>%s</b>\\n%b\\n<span foreground='#fabd2f'>点击选择操作（Confirm 确认 / Deny 拒绝）</span>";
          on-button-left = ''exec ${bluetoothActions} "$id"'';
          on-touch = ''exec ${bluetoothActions} "$id"'';
        };

        # 勿扰模式：通知仍进入历史记录，但不在屏幕上弹出。
        "mode=do-not-disturb" = {
          invisible = true;
        };
      };
    };

    # services.mako 模块生成的 xdg.configFile."mako/config" 默认不覆盖已有文件；
    # 声明式接管该路径（覆盖之前手动写入的临时配置），switch 时不报 clobber。
    xdg.configFile."mako/config".force = true;
  };
}
