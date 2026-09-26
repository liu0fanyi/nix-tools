{ pkgs, lib, inputs, isNixOS ? false, osConfig ? null, ... }:
{
  home.packages = lib.optionals (
    isNixOS && osConfig != null && osConfig.networking.hostName == "liu-bigpc"
  ) [
    (pkgs.callPackage ../packages/baidunetdisk.nix {
      legacyGtk = inputs.nixpkgs-gtkmm2.legacyPackages.${pkgs.stdenv.hostPlatform.system};
    })
  ];
}
