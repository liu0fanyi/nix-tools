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
    # OpenAI 官方 ChatGPT/Codex Linux 桌面应用（官方 .deb 的 NixOS FHS 包装）
    ./chatgpt-desktop.nix
    # AnyDesk 远程桌面客户端（unfree 官方二进制；客户端跑在用户会话）
    ./anydesk.nix
    # Google Antigravity IDE + CLI（nixpkgs 内置，unfree 官方二进制）
    ./antigravity.nix
    # wayland need newer linux try later
    # ./rustdesk.nix
  ];
}
