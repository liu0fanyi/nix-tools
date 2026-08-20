# This is a generic placeholder, not a machine-specific hardware report.
# nixos-anywhere overwrites it with nixos-generate-config during installation.
# Do not add disk UUIDs, CPU-specific modules, or other host details here.
{ lib, modulesPath, ... }:

{
  imports = [ (modulesPath + "/installer/scan/not-detected.nix") ];
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}
