{ inputs, ... }:
{
  imports = [
    ./helix.nix
    ./alacritty.nix
    ./sakura.nix
    ./rime.nix
    ./full.nix
    ./podman.nix
  ];
}
