{
  config,
  pkgs,
  lib,
  username,
  isNixOS ? false,
  ...
}:
{
  imports = [
    ./nix_modules
  ];

  home.username = username;
  home.homeDirectory = "/home/${username}";
  home.stateVersion = "26.11";

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
  # NixOS 上由 nixos 目标接管，无需启用
  targets.genericLinux.enable = lib.mkIf (!isNixOS) true;

  # 启用 XDG MIME 类型关联
  # 原理：让 Nix 安的应用能正确处理文件类型关联（如双击文件时用正确的程序打开）
  xdg.mime.enable = true;

  nixpkgs.config.allowUnfree = lib.mkIf (!isNixOS) true;

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

    ffmpeg
    devenv
    # yazi
    bottom
    # codex
  ];
  programs.yazi = {
    enable = true;
    # Keep the existing wrapper command stable across Home Manager upgrades.
    shellWrapperName = "yy";

    settings = {
      plugin = {
        # 直接让视频预览和预加载统统去执行一个不存在的命令 "noop"
        # 彻底阻断 ffmpeg 的唤醒，一劳永逸解决卡顿
        prepend_previewers = [
          {
            mime = "video/*";
            run = "noop";
          }
        ];
        prepend_preloaders = [
          {
            mime = "video/*";
            run = "noop";
          }
        ];
      };
    };
  };

  programs.direnv = {
    enable = true;
    enableBashIntegration = true; # see note on other shells below
    nix-direnv.enable = true;
  };

  programs.bash = {
    enable = true;
    initExtra = ''
      # npm global installs (e.g. dsh, dsh-tui)
      export PATH="$HOME/.npm-global/bin:$PATH"

      # local bin wrappers take priority (e.g. dsh with --expose-internals)
      export PATH="$HOME/.local/bin:$PATH"

      # nvm
      export NVM_DIR="$HOME/.nvm"
      [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
      [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

      # bun
      export BUN_INSTALL="$HOME/.bun"
      export PATH="$BUN_INSTALL/bin:$PATH"
    '';
  };

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
  programs.nushell = {
    enable = true;
    extraConfig = ''
      # 这里放你刚才看到的 direnv hook 代码
      $env.config = (
        $env.config | upsert hooks {
          pre_prompt: [{ ||
            if (which direnv | is-empty) {
              return
            }
            direnv export json | from json | default {} | load-env
          }]
        }
      )
    '';
    extraEnv = ''
      $env.NVM_DIR = ($env.HOME | path join ".nvm")
      $env.BUN_INSTALL = ($env.HOME | path join ".bun")
      $env.PATH = (
        $env.PATH
        | prepend ($env.NVM_DIR | path join "versions" "node" "v24.15.0" "bin")
        | prepend ($env.BUN_INSTALL | path join "bin")
        | prepend ($env.HOME | path join ".npm-global" "bin")
        | prepend ($env.HOME | path join ".local" "bin")
      )
        $env.config.buffer_editor = "hx"
        $env.EDITOR = "hx"
      # $env.NAVI_PATH = "/home/liu/nix_config/nix_modules/navi";
    '';
  };
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

  programs.git = {
    enable = true;
    lfs.enable = true;
    # Declare identity so reinstalling/switch does not lose ~/.gitconfig
    settings = {
      user = {
        name = "liou";
        email = "liu_fanyi@hotmail.com";
      };
      core.sshCommand = "ssh -4";
    };
  };

  programs.home-manager.enable = true;

  # dsh/dsh-tui 需要 node --expose-internals（HMR 插件要求）；
  # npm 的 bin 链接无法带参数，用包装脚本（仅 NixOS，npm 包在 ~/.npm-global）
  home.file.".local/bin/dsh" = lib.mkIf isNixOS {
    executable = true;
    text = ''
      #!/bin/sh
      exec node --expose-internals ${config.home.homeDirectory}/.npm-global/lib/node_modules/@deepseek-ai/dsh/lib/bin.js "$@"
    '';
  };
  home.file.".local/bin/dsh-tui" = lib.mkIf isNixOS {
    executable = true;
    text = ''
      #!/bin/sh
      exec node --expose-internals ${config.home.homeDirectory}/.npm-global/lib/node_modules/@deepseek-harness-tui/dsh-tui/bin/dsh-tui.js "$@"
    '';
  };

  # The local Home Manager options manual is not used here. Disabling it also
  # avoids an upstream options.json derivation that loses Nix store context.
  manual.manpages.enable = false;

  # Ensure systemd user services are started/restarted on switch
  # Use the host client on non-NixOS; nixpkgs systemctl may be newer than the
  # running host daemon and fail to connect to its user bus.
  # NixOS 上 systemctl 位于 /run/current-system/sw/bin，使用默认值即可。
  systemd.user.systemctlPath = lib.mkIf (!isNixOS) "/usr/bin/systemctl";
  systemd.user.startServices = "sd-switch";
}
