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
  # 用户只使用 1-6 工作区，移除官方默认的 Mod+7/8/9 绑定（避免切出动态工作区）。
  # 移除官方默认的 numlock 启动项（NumLock 状态应完全由键盘控制）。
  niriConfig =
    builtins.replaceStrings
      [
        "binds {"
        "    Mod+7 { focus-workspace 7; }\n    Mod+8 { focus-workspace 8; }\n    Mod+9 { focus-workspace 9; }\n"
        "        // Enable numlock on startup, omitting this setting disables it.\n        numlock\n"
      ]
      [
        ''
          binds {
              // ===== homebox 追加键位 =====
              // WiFi 选择（fuzzel 界面）
              Mod+N { spawn "networkmanager_dmenu" "--dmenu" "fuzzel"; }
        ''
        ""
        ""
      ]
      (builtins.readFile ./default-config.kdl)
    + ''
      // ===== homebox 追加（参考官方 wiki 与社区配置）=====

      // 命名工作区：仅 1-6（waybar 按数字显示，niri 0.1.6+ 声明式）
      workspace "1"
      workspace "2"
      workspace "3"
      workspace "4"
      workspace "5"
      workspace "6"

      // 鼠标光标主题（Nordzy，避免 waybar/niri 的 cursor theme 警告）
      cursor {
          xcursor-theme "Nordzy-cursors"
          xcursor-size 24
      }

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
      # 仅在 NixOS 默认启用（非 NixOS 分支需要 nixGL，其求值含 impure
      # builtins.currentTime，会导致 standalone 的 home-manager switch 失败）
      default = config.features.full.enable && isNixOS;
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

    # Waybar 状态栏配置（参考 0xNiri/社区：图标化 + 数字工作区）
    xdg.configFile."waybar/config.jsonc" = lib.mkIf isNixOS {
      text = ''
        {
          "layer": "top",
          "position": "top",
          "height": 30,
          "spacing": 8,
          "modules-left": ["niri/workspaces"],
          "modules-center": ["clock"],
          "modules-right": ["pulseaudio", "network", "cpu", "memory", "battery", "tray"],

          "niri/workspaces": {
            "format": "{name}",
            "tooltip": false
          },
          "clock": {
            "format": "󰥔 {:%H:%M  %m-%d}",
            "tooltip-format": "<tt><small>{calendar}</small></tt>",
            "interval": 60
          },
          "cpu": {
            "format": " {usage}%",
            "tooltip": true,
            "tooltip-format": "负载: {load}",
            "interval": 5
          },
          "memory": {
            "format": "󰍛 {percentage}%",
            "tooltip": true,
            "tooltip-format": "已用: {used}\n总量: {total}",
            "interval": 10
          },
          "network": {
            "format-wifi": "󰤨",
            "format-ethernet": "󰈀",
            "format-disconnected": "󰤮",
            "tooltip": true,
            "tooltip-format": "{ifname}\n{essid} 信号 {signalStrength}%\nIP: {ipaddr}",
            "interval": 15
          },
          "battery": {
            "format": "{icon} {capacity}%",
            "format-charging": "󰂄 {capacity}%",
            "format-icons": ["", "", "", "", ""],
            "interval": 30
          },
          "pulseaudio": {
            "format": "{icon} {volume}%",
            "format-muted": "󰝟",
            "format-icons": ["󰕿", "󰖀", "󰕾"],
            "on-click": "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle",
            "tooltip-format": "{desc}"
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
        /* 工作区按钮：数字居中，激活高亮 */
        #workspaces button {
          padding: 0 7px;
          margin: 3px 1px;
          color: #928374;
          background: #282828;
          border-radius: 4px;
        }
        #workspaces button.active {
          color: #1d2021;
          background: #ebdbb2;
        }
        #workspaces button:hover {
          color: #ebdbb2;
          background: #3c3836;
        }
        #clock, #tray, #cpu, #memory, #network, #battery, #pulseaudio {
          padding: 0 8px;
        }
        #battery.charging { color: #b8bb26; }
        #battery.warning { color: #fb4934; }
        #pulseaudio.muted { color: #fb4934; }
        #network.disconnected { color: #928374; }
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
