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

    # Basic configuration file
    xdg.configFile."niri/config.kdl".text = ''
      // Basic Niri configuration
      input {
        keyboard {
          xkb {
            layout "us"
          }
        }
        touchpad {
          tap
          natural-scroll
        }
      }
      
      binds {
        Mod+Shift+E { quit; }
        Mod+Q { close-window; }
        Mod+Return { spawn "alacritty"; }
        Mod+D { spawn "fuzzel"; }
      }
    '';
    
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
