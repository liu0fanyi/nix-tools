{ config, pkgs, inputs, ... }:
{
  home.packages = [
    inputs.tool-updates.legacyPackages.${pkgs.stdenv.hostPlatform.system}.kicad
    (pkgs.callPackage ../packages/lceda-pro.nix {
      scaleFactor = config.features.desktopScaling.scale;
    })
    (pkgs.callPackage ../packages/jlc-assistant.nix {
      scaleFactor = config.features.desktopScaling.scale;
    })
  ];
}
