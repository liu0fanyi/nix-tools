{ pkgs, lib, config, ... }:
let
  cfg = config.features.rustdesk;
in
{
  options.features.rustdesk = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable RustDesk remote desktop";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ pkgs.rustdesk ];
  };
}
