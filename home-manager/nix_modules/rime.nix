{ pkgs, lib, config, ... }:
let
  cfg = config.features.ibus-rime;
in
{
  options.features.ibus-rime = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable IBus-Rime input method";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = with pkgs; [
      ibus
      ibus-engines.rime
      librime
    ];

    # Manually set environment variables for IBus
    # This is more robust on generic Linux where the HM i18n module might have issues
    home.sessionVariables = {
      GTK_IM_MODULE = "ibus";
      QT_IM_MODULE = "ibus";
      XMODIFIERS = "@im=ibus";
    };
  };
}
