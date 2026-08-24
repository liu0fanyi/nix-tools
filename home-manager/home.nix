{
  config,
  pkgs,
  lib,
  username,
  inputs,
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

  # 非 NixOS（standalone）时允许 unfree 包。
  # NixOS 集成（useGlobalPkgs = true）下完全不定义 nixpkgs.config：
  # 它由 nixos/configuration.nix 的全局 nixpkgs.config 提供，
  # 这里再设会触发 "nixpkgs.config while useGlobalPkgs" 警告。
  nixpkgs.config = lib.mkIf (!isNixOS) {
    allowUnfree = true;
  };

  # 简单的软件包安装方式
  home.packages = with pkgs; [
    ## libnotify：提供 notify-send（配合 mako 发桌面通知）
    libnotify
    ## zenity：clipboard-sync 接收/拒绝确认对话框（Linux 端统一交互）
    zenity

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
    glow

    ## git tools
    gitui
    ## git-crypt（解密仓库 secrets：secrets/**，restore 脚本依赖）
    git-crypt
    ## docker tools
    lazydocker
    ## fonts
    nerd-fonts.bigblue-terminal
    ## X11 终端（VMware 兼容）
    # 使用sakura

    ffmpeg
    devenv
    ## deploy/ 脚本（manage.py / release-apps.py）运行依赖
    python3
    localsend
    # GitHub CLI（创建/推送仓库、管理 issues 等）
    gh
    ## 解压工具（zip/7z/rar 等通用格式；tar/gzip/xz 系统已有）
    unzip
    zip
    p7zip
    # just：任务运行器（clipboard-sync 构建/分发/部署用，见 clipboard-sync/Justfile）
    just
    # Cross-device encrypted credential vault and its sync daemon.
    keepassxc
    syncthing
    # yazi
    bottom
    # OpenAI Codex CLI（社区滚动 flake：sadjow/codex-cli-nix，每小时更新）
    # 用 inputs.codex-cli-nix 而非 nixpkgs#codex——前者追平上游 release
    # （如 0.149.1），nixpkgs unstable 可能滞后多个版本。
    inputs.codex-cli-nix.packages.${pkgs.system}.codex
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
    # 加载 devenv 的 direnv 集成（提供 `use devenv`，即 use_devenv 函数），
    # 否则 .envrc 里的 `use devenv` 会报 "use_devenv: 未找到命令"。
    # stdlib 由 direnv 以 bash source 执行，进程替换 <(...) 可用。
    stdlib = ''
      source <(devenv direnvrc)
    '';
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

  # dsh/dsh-tui 需要 node --expose-internals。
  #
  # 为什么需要：
  #   dsh web 的 HMR（前端热更新）服务由 cordis-plugin-hmr 提供，它在启动时强制检查
  #     if (!this.ctx.loader.internal) throw new Error("--expose-internals is required for HMR service");
  #   loader.internal 是 Node 的内部模块加载器（node:internal/modules/esm/loader），
  #   只有加 --expose-internals 启动标志才会暴露给用户代码，HMR 用它做模块热替换。
  #   注意：dsh --version 等普通命令不需要此标志，只有启动 web GUI（带 HMR）时才需要。
  #
  # 为什么必须包装：
  #   npm 生成的 bin 链接（~/.npm-global/bin/dsh → lib/bin.js）是 shebang 软链，
  #   无法附加启动参数。用 .local/bin/dsh wrapper 包一层 exec node --expose-internals；
  #   .local/bin 在 PATH 中排在 .npm-global/bin 之前（见 programs.bash.initExtra），
  #   所以 `dsh` 命中 wrapper 而非 npm 裸链接。
  #
  # 仅 NixOS：npm 包装在 ~/.npm-global（用户目录可写），wrapper 覆盖到该路径。
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

  # dsh web 启动切换脚本（供 dsh-web.desktop 的 Mod+D 调用）：
  # - 未运行 → systemctl --user start（启动后 notify-send 弹 toast）
  # - 已运行 → systemctl --user restart（重启后弹 toast）
  # notify-send 用 pkgs.libnotify 的绝对路径（Nix 插值），不依赖 PATH——
  # .desktop 的 Exec 环境 PATH 不可靠，且 useUserPackages 下 per-user profile
  # 可能滞后。
  home.file.".local/bin/dsh-web-toggle" = lib.mkIf isNixOS {
    executable = true;
    text = ''
      #!/bin/sh
      notify="${pkgs.libnotify}/bin/notify-send"
      if systemctl --user is-active --quiet dsh-web; then
        echo "dsh-web: 已运行，重启中..."
        systemctl --user restart dsh-web
        action="重启"
      else
        echo "dsh-web: 启动中..."
        systemctl --user start dsh-web
        action="启动"
      fi
      # 等 service 进入 running 再发通知
      for i in 1 2 3 4 5 6 7 8 9 10; do
        systemctl --user is-active --quiet dsh-web && break
        sleep 1
      done
      "''$notify" "DSH Web 已''${action}" "http://127.0.0.1:3080" 2>/dev/null || true
    '';
  };

  # npm 全局安装配置（NixOS 上 npm prefix 默认指向只读 nix store，
  # 固定到用户目录 + 国内镜像；重装后 npm install 直接可用）
  home.file.".npmrc" = lib.mkIf isNixOS {
    text = ''
      prefix=/home/${username}/.npm-global
      registry=https://registry.npmmirror.com
    '';
  };

  # SSH 主机配置（~/.ssh/config）：供 dsh SSH 插件（dsh-remote-ssh /
  # dsh-ssh）识别导入。nuc 是 DUFS Plus 部署机，用 liou 免密登录。
  # 关键：HostName 用 mDNS 名 nuc.local（avahi 动态解析），而不是写死 IP——
  # 对方 IP 变化时无需改配置。nuc 是 mDNS 别名（同时注册 .local 解析）。
  # 用 programs.ssh.settings（matchBlocks 已弃用）。
  programs.ssh = {
    enable = true;
    # 不生成 home-manager 的默认配置段（defaults 由 settings."*" 自己控制）
    enableDefaultConfig = false;
    settings = {
      # 默认值：保持 home-manager 之前的默认行为
      "*" = {
        AddKeysToAgent = "no";
        Compression = "no";
        ControlMaster = "no";
        ControlPath = "~/.ssh/master-%r@%n:%p";
        ControlPersist = "no";
        ForwardAgent = "no";
        HashKnownHosts = "no";
        ServerAliveCountMax = 3;
        ServerAliveInterval = 0;
        UserKnownHostsFile = "~/.ssh/known_hosts";
      };
      # nuc（mDNS 名，防 IP 变化）
      "nuc" = {
        HostName = "nuc.local";
        User = "liou";
      };
      "nuc.local" = {
        HostName = "nuc.local";
        User = "liou";
      };
      # homebox（本机，mDNS 名；IP 是 DHCP 会变，用 mDNS 稳定）
      "homebox" = {
        HostName = "homebox.local";
        User = "liou";
      };
      "homebox.local" = {
        HostName = "homebox.local";
        User = "liou";
      };
      # 外网 SSH 到 nuc：经 aliyun VPS 跳板 + autossh 反向隧道（nuc 上跑，
      # 见 nix_modules/nuc-tunnel.nix）。aliyun 开 2222 → 隧道 → nuc:22。
      "nuc-remote" = {
        HostName = "localhost";
        User = "liou";
        Port = 2222;
        ProxyJump = "root@47.93.153.102";
        # 隧道断线/aliyun 重启后 autossh 会自动重连，无需人工
        ServerAliveInterval = 30;
        ServerAliveCountMax = 3;
      };
    };
  };

  # Rime 默认简体输出（switches 定义在方案级 schema，
  # 须 patch luna_pinyin.custom.yaml 而非 default.custom.yaml）
  home.file.".local/share/fcitx5/rime/luna_pinyin.custom.yaml" = lib.mkIf isNixOS {
    text = ''
      patch:
        "switches/@2/reset": 1
    '';
  };

  # Rime 的 userdb 是运行时 LevelDB，不能用只读 Nix store 直接托管。
  # 这里声明稳定的同步目录；scripts/sync-rime-userdb.sh 负责把快照安全地
  # 部署到远程 homebox，避免每次重装再手工 scp 一整个目录。
  home.activation.rimeSyncDir = lib.mkIf isNixOS (
    lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      rime_dir="$HOME/.local/share/fcitx5/rime"
      sync_dir="$rime_dir/sync"
      user_yaml="$rime_dir/user.yaml"
      install -d -m 700 "$rime_dir" "$sync_dir"

      if [ ! -e "$user_yaml" ]; then
        printf 'sync_dir: %s\n' "$sync_dir" > "$user_yaml"
        chmod 600 "$user_yaml"
      elif ! grep -q '^[[:space:]]*sync_dir:' "$user_yaml"; then
        tmp="$(mktemp)"
        printf 'sync_dir: %s\n' "$sync_dir" > "$tmp"
        cat "$user_yaml" >> "$tmp"
        install -m 600 "$tmp" "$user_yaml"
        rm -f "$tmp"
      fi
    ''
  );

  # dsh / dsh-tui 通过 npm 全局安装（~/.npm-global），home-manager 无法像
  # nix 包那样固定版本，这里在每次 switch 时检查 npm 最新版，仅在需要时更新，
  # 保证版本跟随上游（近似滚动更新）。插件装在 ~/.dsh/profiles/，独立于 npm 包，
  # 更新 dsh 不影响已装插件。
  home.activation.ensureDshLatest = lib.mkIf isNixOS (
    lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      # 不能在任何分支用 exit（activation 是顶层 shell 脚本，exit 会终止整个
      # activation，导致后续 linkGeneration 等步骤不执行），用 if 包裹。
      # activation 的 PATH 是固定 nix store 路径，不含系统 bin / npm-global，
      # 这里显式补充（npm 在 /run/current-system/sw/bin 或 ~/.npm-global/bin）。
      export PATH="/run/current-system/sw/bin:''$HOME/.npm-global/bin:''$PATH"
      if command -v npm >/dev/null 2>&1; then
        # .npmrc 已配置 prefix 与 npmmirror 镜像
        for pkg in "@deepseek-ai/dsh" "@deepseek-harness-tui/dsh-tui"; do
          # 当前版本：直接读已安装包的 package.json
          pkg_json="''$HOME/.npm-global/lib/node_modules/''$pkg/package.json"
          current=""
          if [ -f "''$pkg_json" ]; then
            current="''$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "''$pkg_json" | head -n1)"
          fi
          latest="''$(npm view "''$pkg" version 2>/dev/null || echo "")"
          if [ -z "''$latest" ]; then
            echo "ensureDshLatest: 无法获取 ''$pkg 最新版（网络/镜像问题），跳过"
            continue
          fi
          if [ "''$current" != "''$latest" ]; then
            echo "ensureDshLatest: 更新 ''$pkg ''$current → ''$latest"
            # --legacy-peer-deps：npm 11 arborist 对 dsh-tui 依赖树有 bug
            # （Cannot read properties of null），该标志绕过严格 peer 解析
            npm install -g --legacy-peer-deps "''$pkg@''$latest" >/dev/null 2>&1 && echo "  ✓ 已更新" || echo "  ✗ 更新失败（保留当前版本）"
          else
            echo "ensureDshLatest: ''$pkg 已是最新（''$current）"
          fi
        done
      else
        echo "ensureDshLatest: npm 不可用，跳过"
      fi
    ''
  );

  # dsh profile 插件（如 SSH 插件）由 dsh 自己管理（dsh plugin add/rm/update，
  # 转发 pnpm），home-manager 不接管——插件是动态的、有依赖顺序，声明式管理
  # 会与手动操作冲突。需要时手动执行：
  #   dsh plugin --profile web add dsh-better-sidebar
  #   dsh plugin --profile web add @zhangfengshun/dsh-remote-ssh

  # fcitx5 输入法列表（对齐本机：keyboard-us + pinyin + rime，默认 rime）
  xdg.configFile."fcitx5/profile" = lib.mkIf isNixOS {
    # fcitx5 运行时也会生成此文件，接管需强制
    force = true;
    text = ''
      [Groups/0]
      # Group Name
      Name=默认
      # Layout
      Default Layout=us
      # Default Input Method
      DefaultIM=rime

      [Groups/0/Items/0]
      # Name
      Name=keyboard-us
      # Layout
      Layout=

      [Groups/0/Items/1]
      # Name
      Name=pinyin
      # Layout
      Layout=

      [Groups/0/Items/2]
      # Name
      Name=rime
      # Layout
      Layout=

      [GroupOrder]
      0=默认
    '';
  };

  # 光标主题环境变量（配合 niri cursor 块与 nordzy-cursor-theme）
  home.sessionVariables = lib.mkIf isNixOS {
    XCURSOR_THEME = "Nordzy-cursors";
    XCURSOR_SIZE = "24";
  };

  # mihomo 内核服务已移至系统级（NixOS 配置 systemd.services.clashtui-mihomo，
  # TUN 透明代理需要 root + CAP_NET_ADMIN）。

  # KeePassXC stores all shared credentials in an encrypted .kdbx file.
  # Syncthing only replicates that ciphertext between the user's devices;
  # plaintext exports live in ~/.config/secrets and are never managed by Nix
  # or committed here.
  home.activation.secretVaultDirs = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    install -d -m 700 "$HOME/Sync/secrets" "$HOME/.config/secrets"
  '';

  # Use the same user service on Pop!_OS and NixOS.  The NixOS Syncthing
  # module would create a separate system service, while this vault belongs
  # to liou and is intentionally managed by the shared Home Manager config.
  systemd.user.services.syncthing = {
    Unit = {
      Description = "Syncthing - Open Source Continuous File Synchronization";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };
    Service = {
      ExecStart = "${pkgs.syncthing}/bin/syncthing serve --no-browser --no-restart --log-format-timestamp=\"\"";
      UMask = "0077";
      # The vault is shared only with explicitly paired trusted peers.  Other
      # LAN devices can still be paired later; public discovery, relays and
      # UPnP are disabled. Syncthing v2 stores these options in its runtime
      # config, so enforce them after every start instead of relying on an
      # unmanaged first-run GUI click.
      ExecStartPost = "${pkgs.writeShellScript "syncthing-lan-settings" ''
        set -eu
        attempts=0
        while ! ${pkgs.syncthing}/bin/syncthing cli config options natenabled set false >/dev/null 2>&1; do
          attempts=$((attempts + 1))
          if [ "$attempts" -ge 30 ]; then
            echo "Syncthing API did not become ready for LAN-only settings." >&2
            exit 1
          fi
          ${pkgs.coreutils}/bin/sleep 1
        done
        ${pkgs.syncthing}/bin/syncthing cli config options global-ann-enabled set false
        ${pkgs.syncthing}/bin/syncthing cli config options relays-enabled set false
        ${pkgs.syncthing}/bin/syncthing cli config options local-ann-enabled set true
      ''}";
      Restart = "on-failure";
      RestartSec = 5;
    };
    Install.WantedBy = [ "default.target" ];
  };

  # clashtui 配置（声明式；订阅 URL 在 mihomo/config.yaml，属 secrets 不在此）
  xdg.configFile."clashtui/config.yaml" = lib.mkIf isNixOS {
    text = ''
      mihomo:
        core:
          config_dir: ${config.home.homeDirectory}/.config/clashtui/mihomo
          bin_path: /run/current-system/sw/bin/mihomo
          config_path: ${config.home.homeDirectory}/.config/clashtui/mihomo/config.yaml
        core_service:
          service_name: clashtui-mihomo
          is_user: false
      singbox:
        core:
          config_dir: ${config.home.homeDirectory}/.config/clashtui/sing-box/config
          bin_path: /run/current-system/sw/bin/sing-box
          config_path: ${config.home.homeDirectory}/.config/clashtui/sing-box/config/config.json
        core_service:
          service_name: clashtui_singbox
          is_user: false
      timeout: null
      extra:
        edit_cmd: xdg-open "%s"
        open_dir_cmd: xdg-open "%s"
    '';
  };

  # The local Home Manager options manual is not used here. Disabling it also
  # avoids an upstream options.json derivation that loses Nix store context.
  manual.manpages.enable = false;

  # DSH Web GUI 作为 systemd user service 管理（代替裸进程 + pkill）。
  # Mod+D（fuzzel → dsh-web.desktop）调用 `systemctl --user start dsh-web`：
  # 已运行则 no-op，未运行则启动；停止用 `systemctl --user stop dsh-web`。
  # 不 enable：保持手动启动语义，不开机自启。
  systemd.user.services.dsh-web = {
    Unit = {
      Description = "DeepSeek Harness Web GUI";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };
    Service = {
      # 用 home-manager 生成的 wrapper（带 --expose-internals，HMR 需要）
      ExecStart = "${config.home.homeDirectory}/.local/bin/dsh web";
      Restart = "on-failure";
      RestartSec = "3";
      # 限制文件权限，避免 dsh 生成的 profile 文件权限过宽
      UMask = "0077";
    };
    Install = { };
  };

  # Ensure systemd user services are started/restarted on switch
  # Use the host client on non-NixOS; nixpkgs systemctl may be newer than the
  # running host daemon and fail to connect to its user bus.
  # NixOS 上 systemctl 位于 /run/current-system/sw/bin，使用默认值即可。
  systemd.user.systemctlPath = lib.mkIf (!isNixOS) "/usr/bin/systemctl";
  systemd.user.startServices = "sd-switch";
}
