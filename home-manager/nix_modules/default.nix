{ inputs, ... }:
{
  imports = [
    ./helix.nix
    ./alacritty.nix
    ./sakura.nix
    ./fcitx5.nix
    ./full.nix
    ./podman.nix
    ./niri.nix
    # wayland need newer linux try later
    # ./rustdesk.nix
  ];
}
