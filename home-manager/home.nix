{ config, pkgs, ... }:
{
  imports = [
    ./nix_modules
  ];

  home.username = "liou";
  home.homeDirectory = "/home/liou";
  home.stateVersion = "25.11";

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
  ];

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
