{ config, lib, pkgs, isNixOS ? false, osConfig ? null, ... }:
let
  cfg = config.features.desktopScaling;
  dpi = builtins.floor (96 * cfg.scale + 0.5);
  resources = pkgs.writeText "xwayland-dpi.Xresources" ''
    Xft.dpi: ${toString dpi}
  '';
in
{
  options.features.desktopScaling = {
    enable = lib.mkEnableOption "shared XWayland and application UI scaling" // {
      default = isNixOS && osConfig != null
        && osConfig.networking.hostName == "liu-bigpc" && config.features.niri.enable;
    };
    scale = lib.mkOption {
      type = lib.types.numbers.positive;
      default = config.features.niri.primaryOutputScale;
      description = "Shared readable UI scale for X11 and explicitly scaled desktop apps";
    };
  };

  config = lib.mkIf cfg.enable {
    # Satellite chooses the smallest output DPI on mixed-scale monitors.
    # Own XSETTINGS instead, so all cooperating X11 apps use the primary scale.
    services.xsettingsd = {
      enable = true;
      settings = {
        "Xft/DPI" = dpi * 1024;
        "Gdk/UnscaledDPI" = dpi * 1024;
        "Gdk/WindowScalingFactor" = 1;
        "Net/FontName" = "Sans 11";
      };
    };
    systemd.user.services.xsettingsd.Service = {
      # Xft resources also cover X11 clients that do not use XSETTINGS.
      # This connects to Niri's imported DISPLAY and starts satellite on demand.
      ExecStartPre = "${pkgs.xrdb}/bin/xrdb -merge ${resources}";
      Restart = lib.mkForce "on-failure";
      RestartSec = "5s";
    };
    home.packages = [ pkgs.xsettingsd pkgs.xrdb pkgs.xprop ];
  };
}
