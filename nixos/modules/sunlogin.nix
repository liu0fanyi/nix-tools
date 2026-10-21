{ config, pkgs, inputs, ... }:
let
  sunlogin = import ../../packages/sunlogin.nix {
    inherit pkgs;
    legacyGtk = inputs.nixpkgs-gtkmm2.legacyPackages.${pkgs.stdenv.hostPlatform.system};
    scaleFactor = config.home-manager.users.liou.features.desktopScaling.scale;
  };
in
{
  environment.systemPackages = [ sunlogin ];

  # The official desktop client requires its system daemon. No vendor
  # post-install script runs: NixOS owns the service and persistent paths.
  systemd.tmpfiles.rules = [
    "d /var/lib/sunlogin 0750 root users -"
    "f /var/lib/sunlogin/orayconfig.conf 0660 root users -"
    "d /var/log/sunlogin 0770 root users -"
  ];
  systemd.services.sunlogin = {
    description = "Sunlogin remote desktop daemon";
    after = [ "network.target" "systemd-tmpfiles-setup.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      ExecStart = "${sunlogin}/bin/sunlogin-daemon -m server";
      Restart = "on-failure";
      RestartSec = "5s";
    };
  };
}
