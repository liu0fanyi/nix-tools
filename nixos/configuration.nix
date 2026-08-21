# ==========================================================================
# NixOS 官方模板（nixpkgs master nixos-generate-config 内置模板，原样保留）
# 来源：nixpkgs/nixos/modules/installer/tools/tools.nix (defaultConfigTemplate)
# 文件末尾 "以下为追加" 分隔线之后为按需启用的功能。
# ==========================================================================

# Edit this configuration file to define what should be installed on
# your system. Help is available in the configuration.nix(5) man page, on
# https://search.nixos.org/options and in the NixOS manual (`nixos-help`).

{
  config,
  lib,
  pkgs,
  username,
  inputs,
  ...
}:
let
  # 合盖策略集中在这里切换：lock、suspend、hibernate 或
  # suspend-then-hibernate。当前远程 homebox 采用后者。
  lidSwitchAction = "suspend-then-hibernate";
  mihomoConfigDir = "/home/${username}/.config/clashtui/mihomo";
  # clashtui 以 liou 运行、mihomo 以 root 运行；让两者通过 users 组共享
  # 运行时文件。这个修复在每次 mihomo 启动前执行，因此首次打开 clashtui
  # 不需要再手动点击 “Fix now”。
  mihomoPermissionRepair = pkgs.writeShellScript "clashtui-mihomo-permissions" ''
    set -eu

    config_dir="${mihomoConfigDir}"
    providers_dir="$config_dir/providers"

    ${pkgs.coreutils}/bin/install -d -o ${username} -g users -m 2770 "$config_dir"
    ${pkgs.coreutils}/bin/chown "${username}:users" "$config_dir"
    ${pkgs.coreutils}/bin/chmod 2770 "$config_dir"

    if [ -d "$providers_dir" ]; then
      ${pkgs.coreutils}/bin/chown :users "$providers_dir"
      ${pkgs.coreutils}/bin/chmod 2770 "$providers_dir"
    fi

    while IFS= read -r -d "" file; do
      ${pkgs.coreutils}/bin/chown :users "$file"
      ${pkgs.coreutils}/bin/chmod g+rw "$file"
    done < <(${pkgs.findutils}/bin/find "$config_dir" -maxdepth 2 -type f -print0)
  '';
in
{
  imports =
    [
      # 追加：nixos-anywhere 磁盘布局（官方 nixos-anywhere-examples）
      ./disk-config.nix
    ]
    # hardware-configuration.nix 由 nixos-anywhere 在目标机上临时生成；仓库中
    # 只保留通用占位文件，安装脚本退出时会恢复它。本地存在时用于当前 rebuild。
    ++ lib.optional (builtins.pathExists ./hardware-configuration.nix) ./hardware-configuration.nix;

  # 目标机已确认使用 UEFI，且 efivars 可写；让 GRUB 注册正常的 NVRAM
  # 启动项，避免固件找不到磁盘项时退到 PXE 网络启动。
  boot.loader.efi.canTouchEfiVariables = true;
  boot.loader.grub = {
    efiSupport = true;
    device = "nodev";
    efiInstallAsRemovable = false;
  };

  networking.hostName = "homebox"; # Define your hostname.

  # Configure network connections interactively with nmcli or nmtui.
  networking.networkmanager.enable = true;

  # Set your time zone.
  time.timeZone = "Asia/Shanghai";

  # 电源与合盖策略（目标机是远程笔记本 NixOS，不影响当前开发主机）。
  # 外接显示器时保持当前会话，避免合盖后远程桌面被意外挂起。
  services.logind.settings.Login = {
    HandleLidSwitch = lidSwitchAction;
    HandleLidSwitchExternalPower = lidSwitchAction;
    HandleLidSwitchDocked = "ignore";
  };
  systemd.sleep.settings.Sleep.HibernateDelaySec = "1h";

  # hibernate 必须使用磁盘 swap；zram 不能作为恢复设备。
  # homebox 现有根 LV 已占满 VG，因此使用根 ext4 上的 16 GiB swapfile。
  # resume_offset 是当前 homebox 上 swapfile 的首个物理块偏移；若重装/移动
  # swapfile，需要重新执行 filefrag 并更新这里。
  swapDevices = [
    {
      device = "/var/lib/swapfile";
      size = 16384;
    }
  ];
  boot.resumeDevice = "/dev/mapper/pool-root";
  boot.kernelParams = [ "resume_offset=60665856" ];

  # Configure network proxy if necessary
  # networking.proxy.default = "http://user:password@proxy:port/";
  # networking.proxy.noProxy = "127.0.0.1,localhost,internal.domain";

  # Select internationalisation properties.
  i18n.defaultLocale = "zh_CN.UTF-8";
  # console = {
  #   font = "Lat2-Terminus16";
  #   keyMap = "us";
  #   useXkbConfig = true; # use xkb.options in tty.
  # };

  # Enable the X11 windowing system.
  # services.xserver.enable = true;

  # Configure keymap in X11
  # services.xserver.xkb.layout = "us";
  # services.xserver.xkb.options = "eurosign:e,caps:escape";

  # Enable CUPS to print documents.
  # services.printing.enable = true;

  # Enable sound.
  # services.pulseaudio.enable = true;
  # OR
  # services.pipewire = {
  #   enable = true;
  #   pulse.enable = true;
  # };

  # Enable touchpad support (enabled default in most desktopManager).
  # services.libinput.enable = true;

  # Define a user account. Don't forget to set a password with ‘passwd’.
  # users.users.alice = {
  #   isNormalUser = true;
  #   extraGroups = [ "wheel" ]; # Enable ‘sudo’ for the user.
  #   packages = with pkgs; [
  #     tree
  #   ];
  # };

  # programs.firefox.enable = true;

  # List packages installed in system profile.
  # You can use https://search.nixos.org/ to find more packages (and options).
  # environment.systemPackages = with pkgs; [
  #   vim # Do not forget to add an editor to edit configuration.nix! The Nano editor is also installed by default.
  #   wget
  # ];

  # Some programs need SUID wrappers, can be configured further or are
  # started in user sessions.
  # programs.mtr.enable = true;
  # programs.gnupg.agent = {
  #   enable = true;
  #   enableSSHSupport = true;
  # };

  # List services that you want to enable:

  # Enable the OpenSSH daemon.
  services.openssh.enable = true;

  # Open ports in the firewall.
  # networking.firewall.allowedTCPPorts = [ ... ];
  # networking.firewall.allowedUDPPorts = [ ... ];
  # Or disable the firewall altogether.
  # networking.firewall.enable = false;

  # Copy the NixOS configuration file and link it from the resulting system
  # (/run/current-system/configuration.nix). This is useful in case you
  # accidentally delete configuration.nix.
  # system.copySystemConfiguration = true;

  # This option defines the first version of NixOS you have installed on this particular machine,
  # and is used to maintain compatibility with application data (e.g. databases) created on older NixOS versions.
  #
  # Most users should NEVER change this value after the initial install, for any reason,
  # even if you've upgraded your system to a new NixOS release.
  #
  # This value does NOT affect the Nixpkgs version your packages and OS are pulled from,
  # so changing it will NOT upgrade your system - see https://nixos.org/manual/nixos/stable/#sec-upgrading for how
  # to actually do that.
  #
  # This value being lower than the current NixOS release does NOT mean your system is
  # out of date, out of support, or vulnerable.
  #
  # Do NOT change this value unless you have manually inspected all the changes it would make to your configuration,
  # and migrated your data accordingly.
  #
  # For more information, see `man configuration.nix` or https://nixos.org/manual/nixos/stable/options#opt-system.stateVersion .
  system.stateVersion = "26.11"; # Did you read the comment?

  # ==========================================================================
  # 以下为在官方模板基础上追加的功能
  # ==========================================================================

  # mDNS：解析局域网 .local 主机名（如 nuc.local、homebox.local）。
  # avahi 提供 mDNS 广播/发现，nssmdns 让 getent/ping/浏览器解析 .local 名。
  services.avahi = {
    enable = true;
    nssmdns4 = true; # 通过 NSS 让系统解析 IPv4 的 .local 域名
    nssmdns6 = true; # IPv6 的 .local 域名（可选；部分网络只有 v4）
    publish = {
      enable = true; # 广播本机主机名，方便其他机器发现 homebox
      addresses = true;
      workstation = true;
    };
  };

  # hosts 兜底：nuc（DUFS Plus 部署机）只广播了 IPv4，浏览器若优先
  # 尝试 IPv6 会导致 nuc.local 解析失败。显式映射 IPv4，确保 nuc.local
  # 始终可用（绕过 mDNS 的 v6 查询）。
  networking.hosts = {
    "192.168.1.3" = [ "nuc" "nuc.local" ];
  };

  # SSH 加固（官方模板仅 enable=true）
  services.openssh.settings = {
    PasswordAuthentication = false;
    # root 仅允许密钥登录（nixos-rebuild --target-host 直接 root 登录）
    PermitRootLogin = "prohibit-password";
  };

  # root 公钥（官方 nixos-anywhere 惯例：安装与远程 rebuild 用 root）
  users.users.root.openssh.authorizedKeys.keys = [
    # change this to your ssh key
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHbQy+HyFFvmiI4lFuugbrRLrEa2/TUMvh9RUYK4o73j liu_fanyi@hotmail.com"
  ];

  # 用户管理（官方 users-groups 模块语义）
  # mutableUsers 保持默认 true：密码由用户用 passwd 自行管理，
  # rebuild 不会覆盖已存在用户的密码（密码哈希不进 git）。
  # 如需完全声明式管理密码，可设 users.mutableUsers = false +
  # hashedPassword（此时改密码 = 改配置 + rebuild）。

  # 日常用户（官方模板示例用户是 alice，这里按本机用户名启用）
  users.users.${username} = {
    isNormalUser = true;
    extraGroups = [
      "wheel" # Enable ‘sudo’ for the user.
      "networkmanager"
      "video"
      "input"
    ];
    # 首次安装时的初始密码（仅全新创建用户时生效，用于图形登录；SSH 仍只走密钥）。
    # 已存在的用户不受影响——在这台机器上登录后请用 passwd 修改密码。
    initialPassword = "1234";
    openssh.authorizedKeys.keys = [
      # change this to your ssh key
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHbQy+HyFFvmiI4lFuugbrRLrEa2/TUMvh9RUYK4o73j liu_fanyi@hotmail.com"
    ];
  };
  security.sudo.wheelNeedsPassword = false;

  # 本地化（追加 supportedLocales 以支持中文）
  i18n.supportedLocales = [
    "en_US.UTF-8/UTF-8"
    "zh_CN.UTF-8/UTF-8"
  ];

  # Nix 设置
  nixpkgs.config.allowUnfree = true;
  nix.settings = {
    experimental-features = [ "nix-command" "flakes" ];
    trusted-users = [ "root" username ];
    extra-substituters = [ "https://mirrors.tuna.tsinghua.edu.cn/nix-channels/store" ];
  };

  # niri 桌面（Wayland 平铺，不需要 NixOS 默认桌面）
  hardware.graphics.enable = true;
  programs.niri = {
    enable = true;
    # 与 Home Manager/Niri 配置模板使用同一个 flake 上游版本，避免
    # nixpkgs 的 Niri 与仓库中的配置模板发生版本错配。
    package = inputs.niri.packages.${pkgs.system}.niri;
  };

  # 登录管理器：greetd + tuigreet（轻量 TUI 登录界面，niri 生态标准搭配）
  services.greetd = {
    enable = true;
    settings = {
      default_session = {
        # 登录后直接启动 niri 会话
        command = "${pkgs.tuigreet}/bin/tuigreet --time --cmd niri-session";
      };
    };
  };

  # 输入法（与本机 Ubuntu 的 fcitx5 模块对齐：Rime + 拼音）
  i18n.inputMethod = {
    enable = true;
    type = "fcitx5";
    fcitx5.addons = with pkgs; [
      fcitx5-rime
      rime-data
      fcitx5-gtk
      qt6Packages.fcitx5-chinese-addons
    ];
  };

  # Podman（供 deploy/ 的 DUFS Plus compose 部署使用）
  virtualisation.podman = {
    enable = true;
    dockerCompat = true;
  };
  # rootless 容器需要非特权用户命名空间（NixOS 默认已开启，显式声明以防万一）
  boot.kernel.sysctl."kernel.unprivileged_userns_clone" = lib.mkDefault true;

  # mihomo 系统服务（TUN 透明代理需要 root + CAP_NET_ADMIN；
  # 配置目录在 liou 的 clashtui 目录，root 可读，clashtui 仍可管理订阅/节点）
  systemd.services.clashtui-mihomo = {
    description = "mihomo Daemon (TUN, managed via clashtui)";
    after = [ "network-online.target" ];
    wants = [ "network-online.target" ];
    wantedBy = [ "multi-user.target" ];
    # mihomo 的完整配置属于 git-crypt secrets，由重装后的 post-install
    # 步骤恢复；没有它时不要让 mihomo 自动生成只监听 7890 的初始配置，
    # 否则 clashtui 会误报 controller connection refused。
    unitConfig.ConditionPathExists = "/home/liou/.config/clashtui/mihomo/config.yaml";
    # mihomo 的 auto-route 需要 nft 命令（服务 PATH 默认不含系统目录）
    path = [ pkgs.nftables ];
    serviceConfig = {
      Type = "simple";
      Restart = "always";
      UMask = "0007";
      ExecStartPre = [
        "${mihomoPermissionRepair}"
        "${pkgs.coreutils}/bin/test -s ${mihomoConfigDir}/config.yaml"
      ];
      ExecStart = "${pkgs.mihomo}/bin/mihomo -d ${mihomoConfigDir}";
      ExecReload = "/bin/kill -HUP $MAINPID";
      # root 运行：不收缩 CapabilityBoundingSet（否则丢失 CAP_DAC_OVERRIDE，
      # 无法读取 700 权限的 /home/liou）；CAP_NET_ADMIN 由 root 天然持有
    };
  };

  # allow-lan：放行代理端口，供 podman 容器与局域网设备访问
  networking.firewall.allowedTCPPorts = [ 7897 ];

  # 用户服务开机自启（podman 用户 socket 等）：
  # loginctl enable-linger 的声明式等价（创建 linger 标记文件）
  systemd.tmpfiles.rules = [
    "f /var/lib/systemd/linger/${username} 0644 root root -"
    "d /home/${username}/.config/clashtui 0750 ${username} users -"
    "d /home/${username}/.config/clashtui/mihomo 2770 ${username} users -"
    "d /home/${username}/.config/clashtui/mihomo/providers 2770 ${username} users -"
  ];

  # ==========================================================================
  # niri 桌面配套（参考 niri 官方 wiki Important-Software / Integrating-niri）
  # ==========================================================================

  # 声音：PipeWire + WirePlumber
  services.pipewire = {
    enable = true;
    wireplumber.enable = true;
    pulse.enable = true;
  };

  # Portals（官方推荐 gtk + gnome，gnome 提供屏幕录制；文件选择器用 nautilus）
  xdg.portal = {
    enable = true;
    extraPortals = with pkgs; [
      xdg-desktop-portal-gtk
      xdg-desktop-portal-gnome
    ];
    config.common.default = [ "gnome" "gtk" ];
  };
  services.gnome.gnome-keyring.enable = true;

  # 桌面组件包（waybar 状态栏、fuzzel 启动器、mako 通知、swaybg 壁纸、
  # swaylock 锁屏、grim+slurp 截图、wl-clipboard 剪贴板、nautilus 文件选择器、
  # brightnessctl 亮度、playerctl 媒体控制、cliphist 剪贴板历史、swayidle 自动锁屏）
  environment.systemPackages = with pkgs; [
    waybar
    fuzzel
    mako
    swaybg
    swaylock
    grim
    slurp
    wl-clipboard
    nautilus
    brightnessctl
    playerctl
    cliphist
    swayidle
    wlopm
    # Node.js 运行时（dsh/dsh-tui 等 npm 全局工具）
    nodejs_24
    # WiFi 选择器（Mod+N，fuzzel 界面；nmtui/nmcli 亦可直接使用）
    networkmanager_dmenu
    # 代理：clashtui（TUI 管理）+ mihomo 内核 + fzf（clashtui 依赖）
    clashtui
    mihomo
    fzf
    # mihomo auto-route 需要 nft 命令（fwmark 打标 + DNS 劫持）
    nftables
    # 鼠标光标主题（waybar/niri 的 cursor theme 警告）
    nordzy-cursor-theme
    # Zen Browser（Firefox 内核，独立于 firefox，无需另装 firefox）
    inputs.zen-browser.packages.${pkgs.system}.zen-browser
  ];
  # waybar 电池模块需要 upower
  services.upower.enable = true;
}
