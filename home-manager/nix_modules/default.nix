{ inputs, ... }:
{
  imports = [
    ./helix.nix
    ./alacritty.nix
    ./sakura.nix
    ./fcitx5.nix
    ./full.nix
    ./podman.nix
    ./caddy.nix
    # ./niri.nix
  ];
}
