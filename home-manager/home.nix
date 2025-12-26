{ config, pkgs, username, ... }:
{
  imports = [
    ./nix_modules
  ];

  home.username = username;
  home.homeDirectory = "/home/${username}";
  home.stateVersion = "25.11";

  # 配置 Nix 使用清华源加速（追加到现有 substituters，不覆盖默认配置）
  # 如果多用户，需要把用户加入信任列表/etc/nix/nix.custom.conf
  # echo "trusted-users = root industio" | sudo tee /etc/nix/nix.custom.conf
  # sudo systemctl restart nix-daemon
  home.file.".config/nix/nix.conf".text = ''
    extra-substituters = https://mirrors.tuna.tsinghua.edu.cn/nix-channels/store
  '';

  # 启用非 NixOS Linux 发行版（如 Ubuntu）的桌面集成
  # 原理：设置 XDG_DATA_DIRS 环境变量，使系统应用菜单能扫描到
  # ~/.nix-profile/share/applications/ 下的 .desktop 文件
  # 这样 Nix 安装的 GUI 应用（如 foot）就会出现在 Ubuntu 的快速启动中
  targets.genericLinux.enable = true;

  # 启用 XDG MIME 类型关联
  # 原理：让 Nix 安装的应用能正确处理文件类型关联（如双击文件时用正确的程序打开）
  xdg.mime.enable = true;

  # 简单的软件包安装方式
  home.packages = with pkgs; [
    zellij
    helix
    starship
    nushell
    zoxide

    alacritty

    fzf
    bat
    dust
    ripgrep

    ## git tools
    gitui
    ## docker tools
    lazydocker
    ## fonts
    nerd-fonts.bigblue-terminal
    ## X11 终端（VMware 兼容）
    # 使用sakura
  ];

  # foot 终端配置（Wayland 原生，适用于支持 Wayland 的系统）
  programs.foot = {
    enable = true;
    # 启用服务器模式（可选，能让启动稍微再快一点）
    server.enable = true;

    settings = {
      main = {
        # 1. 设置字体
        # 格式为 "字体名:size=字号"，确保名字和 fc-list 查到的一致
        font = "BigBlueTermPlus Nerd Font Mono:size=12";

        # 2. 核心：启动时自动运行 Zellij
        # Foot 的 shell 参数可以直接指定启动命令
        shell = "zellij";
      };

      colors = {
        # 如果你喜欢复古感，可以在这里调色，或者保持默认
        alpha = 0.9; # 稍微有点透明度
      };
    };
  };

  # 如果你想让 Nix 管理这些程序的配置，可以使用 programs 选项
  programs.nushell.enable = true;
  programs.helix.enable = true;
  # zellij 目前在 home-manager 中也有配置项，也可以开启
  programs.zellij = {
    enable = true;
    settings = {
      theme = "gruvbox-dark";
      default_shell = "nu";
      scrollback_editor = "hx";
    };
  };

  programs.zoxide = {
    enable = true;
    enableNushellIntegration = true;
  };

  programs.starship = {
    enable = true;
    enableNushellIntegration = true;
  };

  programs.home-manager.enable = true;
}
