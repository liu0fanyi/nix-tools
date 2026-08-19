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

{
  imports =
    [
      # Include the results of the hardware scan.
      ./hardware-configuration.nix
      # 追加：nixos-anywhere 磁盘布局（官方 nixos-anywhere-examples）
      ./disk-config.nix
    ];

  # 官方模板此处按检测结果注入引导配置（UEFI → systemd-boot，BIOS → GRUB）。
  # 目标机引导方式未知，采用 nixos-anywhere 官方示例的 GRUB 双兼容方案
  # （EFI/BIOS 通吃，disko 自动把所有带 EF02 分区的设备加入设备列表）：
  boot.loader.grub = {
    efiSupport = true;
    efiInstallAsRemovable = true;
  };
  # 若确认目标机是纯 UEFI，可改回官方 systemd-boot 写法：
  # boot.loader.systemd-boot.enable = true;
  # boot.loader.efi.canTouchEfiVariables = true;

  networking.hostName = "homebox"; # Define your hostname.

  # Configure network connections interactively with nmcli or nmtui.
  networking.networkmanager.enable = true;

  # Set your time zone.
  time.timeZone = "Asia/Shanghai";

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

  # 日常用户（官方模板示例用户是 alice，这里按本机用户名启用）
  users.users.${username} = {
    isNormalUser = true;
    extraGroups = [
      "wheel" # Enable ‘sudo’ for the user.
      "networkmanager"
      "video"
      "input"
    ];
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
    # 锁定与 flake input 一致的 niri 版本（可选，去掉则用 nixpkgs 自带版本）
    package = inputs.niri.packages.${pkgs.system}.niri;
  };

  # 输入法（配合 home-manager 的 fcitx5 模块）
  i18n.inputMethod = {
    enable = true;
    type = "fcitx5";
    fcitx5.addons = with pkgs; [
      fcitx5-chinese-addons
    ];
  };

  # Podman（供 deploy/ 的 DUFS Plus compose 部署使用）
  virtualisation.podman = {
    enable = true;
    dockerCompat = true;
  };
  # rootless 容器需要非特权用户命名空间（NixOS 默认已开启，显式声明以防万一）
  boot.kernel.sysctl."kernel.unprivileged_userns_clone" = lib.mkDefault true;
}
