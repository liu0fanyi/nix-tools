# Actual NUC scan captured 2026-09-06 on the running Pop!_OS host with the
# pinned nixpkgs nixos-generate-config --show-hardware-config --no-filesystems.
# Keep the raw report separate; disk-config.nix alone owns the new disk layout.
# dm-snapshot is a detected module, not a LUKS or old filesystem declaration.
{ ... }:
{
  imports = [ ./hardware-detected.nix ];
}
