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
    # clipboard-sync systemd user service（homebox/nuc 共享）
    ./clipboard-sync.nix
    # wayland need newer linux try later
    # ./rustdesk.nix
  ];
}
