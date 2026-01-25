{ config, pkgs, lib, inputs, ... }:

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
    home.packages = [
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
    home.file.".local/share/wayland-sessions/niri.desktop".text = ''
      [Desktop Entry]
      Name=Niri (NixGL)
      Comment=Niri Window Manager with NixGL
      Exec=${niri-session-wrapped}/bin/niri-session-wrapped
      Type=Application
      DesktopNames=niri
    '';
  };
}
