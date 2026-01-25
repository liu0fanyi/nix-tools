{ pkgs, lib, config, ... }:
let
  cfg = config.features.fcitx5;
in
{
  options.features.fcitx5 = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable Fcitx5 input method with Rime engine";
    };
  };

  config = lib.mkIf cfg.enable {
    i18n.inputMethod = {
      enable = true;
      type = "fcitx5";
      fcitx5.addons = with pkgs; [
        fcitx5-rime
        fcitx5-gtk
        qt6Packages.fcitx5-chinese-addons
        rime-data
      ];
    };

    # Essential environment variables for generic Linux
    home.sessionVariables = {
      # GTK_IM_MODULE = "fcitx";
      QT_IM_MODULE = "fcitx";
      XMODIFIERS = "@im=fcitx";
      SDL_IM_MODULE = "fcitx";
      GLFW_IM_MODULE = "ibus"; # GLFW doesn't support fcitx directly often
    };
  };
}
