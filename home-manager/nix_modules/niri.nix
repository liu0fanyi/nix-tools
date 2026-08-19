{ config, pkgs, lib, inputs, isNixOS ? false, ... }:

let
  cfg = config.features.niri;
  nixGL = inputs.nix-gl.packages.${pkgs.system}.nixGLDefault;
  niriPackage = inputs.niri.packages.${pkgs.system}.niri;

  # Wrapper script to run niri-session with necessary environment variables
  niri-session-wrapped = pkgs.writeShellScriptBin "niri-session-wrapped" ''
    export GBM_BACKENDS_PATH="${pkgs.mesa}/lib/gbm"
    exec ${nixGL}/bin/nixGL ${niriPackage}/bin/niri-session "$@"
  '';

  # 官方默认配置（完整键位/音量/媒体/亮度键/截图等基础）+ 本机追加段。
  # 注：官方默认已含 XF86 音量/媒体/亮度键绑定，无需重复。
  # binds 节点只能出现一次，自定义键位注入官方 binds 块开头。
  niriConfig =
    builtins.replaceStrings
      [ "binds {" ]
      [
        ''
          binds {
              // ===== homebox 追加键位 =====
              // WiFi 选择（fuzzel 界面）
              Mod+N { spawn "networkmanager_dmenu" "--dmenu" "fuzzel"; }
        ''
      ]
      (builtins.readFile ./default-config.kdl)
    + ''
      // ===== homebox 追加（参考官方 wiki 与社区配置）=====

      // 通知、壁纸（纯色）
      spawn-at-startup "mako"
      spawn-at-startup "swaybg" "-c" "#1e1e2e"
      // 剪贴板历史（cliphist，配合 fuzzel 可搜索历史）
      spawn-sh-at-startup "wl-paste --watch cliphist store"
      // 空闲自动锁屏（10 分钟无操作）
      spawn-sh-at-startup "swayidle -w timeout 600 'swaylock -f'"
    '';
in
{
  options.features.niri = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable Niri window manager with NixGL support";
    };
  };

  config = lib.mkIf cfg.enable {
    # NixOS 上由系统模块 programs.niri 提供 niri 包与登录会话，
    # home 这里只负责配置文件；非 NixOS 才装包和 nixGL 包装。
    home.packages = lib.optionals (!isNixOS) [
      niriPackage
      niri-session-wrapped
    ];

    # 配置 = 官方默认（全部键位）+ 追加段
    xdg.configFile."niri/config.kdl".text = niriConfig;

    # networkmanager-dmenu 配置（Mod+N WiFi 选择；fuzzel + alacritty）
    xdg.configFile."networkmanager-dmenu/config.ini" = lib.mkIf isNixOS {
      text = ''
        [dmenu]
        dmenu_command = fuzzel
        prompt = Networks

        [editor]
        terminal = alacritty
      '';
    };

    # Waybar 状态栏配置（工作区 + 系统信息 + 音量 + 网络 + 电池 + 托盘）
    xdg.configFile."waybar/config.jsonc" = lib.mkIf isNixOS {
      text = ''
        {
          "layer": "top",
          "position": "top",
          "height": 30,
          "modules-left": ["niri/workspaces"],
          "modules-center": ["clock"],
          "modules-right": ["pulseaudio", "network", "cpu", "memory", "battery", "tray"],
          "niri/workspaces": { "format": "{name}" },
          "clock": { "format": "{:%H:%M  %m-%d}" },
          "cpu": { "format": "CPU {usage}%", "interval": 5 },
          "memory": { "format": "RAM {percentage}%", "interval": 10 },
          "network": {
            "format-wifi": "WIFI {essid}",
            "format-ethernet": "NET {ifname}",
            "format-disconnected": "NET OFF",
            "interval": 15
          },
          "battery": {
            "format": "{capacity}%",
            "format-charging": "⚡ {capacity}%",
            "tooltip-format": "{time}"
          },
          "pulseaudio": {
            "format": "VOL {volume}%",
            "format-muted": "MUTE",
            "on-click": "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"
          },
          "tray": { "spacing": 8 }
        }
      '';
    };
    xdg.configFile."waybar/style.css" = lib.mkIf isNixOS {
      text = ''
        * {
          font-family: "BigBlueTermPlus Nerd Font Mono";
          font-size: 13px;
          border: none;
          border-radius: 0;
          min-height: 0;
        }
        window#waybar {
          background: rgba(30, 30, 46, 0.9);
          color: #ebdbb2;
        }
        #workspaces button {
          padding: 0 8px;
          color: #928374;
        }
        #workspaces button.active {
          color: #ebdbb2;
          background: #3c3836;
        }
        #clock, #tray, #cpu, #memory, #network, #battery, #pulseaudio {
          padding: 0 10px;
        }
        #battery.charging { color: #b8bb26; }
        #battery.warning { color: #fb4934; }
        #pulseaudio.muted { color: #fb4934; }
      '';
    };
    
    # Create the custom .desktop file in the user's profile
    # (NixOS 的 niri 系统模块已提供 session 文件，这里仅非 NixOS 需要)
    home.file.".local/share/wayland-sessions/niri.desktop" = lib.mkIf (!isNixOS) {
      text = ''
        [Desktop Entry]
        Name=Niri (NixGL)
        Comment=Niri Window Manager with NixGL
        Exec=${niri-session-wrapped}/bin/niri-session-wrapped
        Type=Application
        DesktopNames=niri
      '';
    };
  };
}
