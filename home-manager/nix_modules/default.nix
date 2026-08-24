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
    # mako 通知守护进程配置（通知统一自动消失，不常驻）
    ./mako.nix
    # clipboard-sync systemd user service（homebox/nuc 共享）
    ./clipboard-sync.nix
    # wayland need newer linux try later
    # ./rustdesk.nix
  ];
}
