{ config, pkgs, ... }:
{
  home.packages = [
    pkgs.kicad
    (pkgs.callPackage ../packages/lceda-pro.nix {
      scaleFactor = config.features.niri.primaryOutputScale;
    })
  ];
}
