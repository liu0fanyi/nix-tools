{ lib, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
    # 数位笔"侧键+划动=滚轮"手势守护进程（systemd 系统服务；该文件顶部记录了
    # 为什么不能用 home-manager 用户服务）
    ../../modules/pen-scroll.nix
  ];

  networking.hostName = "liu-bigpc";

  # USB Bluetooth adapter: kernel btusb is already detected; enable BlueZ
  # and the graphical pairing manager without enabling discoverability.
  hardware.bluetooth = {
    enable = true;
    powerOnBoot = true;
  };
  services.blueman.enable = true;

  # Legacy Windows RF configuration tools and RAR extraction support.
  environment.systemPackages = [
    pkgs.unar
    pkgs.wineWow64Packages.stable
  ];

  # 数位笔"侧键+划动=滚轮"手势需要 uinput 才能合成带滚轮的虚拟笔设备。
  # hardware.uinput 提供 /dev/uinput（0660 root:uinput）与 uinput 组。
  #
  # 设备权限由 systemd 系统服务的 SupplementaryGroups 授予，**不依赖登录会话**：
  # 本机启用了 linger，`user@1000.service` 不随注销停止、会一直持有旧组快照，
  # 所以"重新登录"对用户服务无效；而用户服务又因 systemd --user 无 CAP_SETGID
  # 无法用 SupplementaryGroups 自救（216/GROUP）。详见 nixos/modules/pen-scroll.nix。
  #
  # extraGroups 仍保留：便于在终端手工运行脚本调试时直接访问 /dev/uinput。
  hardware.uinput.enable = true;
  users.users.liou.extraGroups = [ "uinput" ];

  # 手势守护进程本体（系统服务）。
  features.penScroll.enable = true;

  # Syncthing is paired only across the trusted IPv4 LAN. Keep these ports
  # closed to global IPv6 and all non-LAN IPv4 sources.
  networking.firewall.extraCommands = ''
    iptables -w -A nixos-fw -s 192.168.1.0/24 -p tcp --dport 22000 -j nixos-fw-accept
    iptables -w -A nixos-fw -s 192.168.1.0/24 -p udp --dport 22000 -j nixos-fw-accept
    iptables -w -A nixos-fw -s 192.168.1.0/24 -p udp --dport 21027 -j nixos-fw-accept
  '';

  # Preserve the state version of the existing installation. This does not
  # control the NixOS package version supplied by flake.lock.
  system.stateVersion = lib.mkForce "24.11";

  # NixOS and Windows use separate ESPs on the KIOXIA SSD. Keep firmware NVRAM
  # writes disabled: bootctl variable updates fail on this machine with ESRCH,
  # while the removable/fallback EFI path remains bootable from firmware.
  boot.loader.grub.enable = false;
  boot.loader.systemd-boot.enable = true;
  # Newer systemd-boot updates use a Varlink path that can surface firmware
  # errors such as ESRCH even when NVRAM writes are disabled.  Keep those
  # non-essential EFI operations from aborting the whole NixOS activation.
  boot.loader.systemd-boot.graceful = true;
  boot.loader.efi.canTouchEfiVariables = false;

  # GTX 1650 (Turing), already proven with the old NixOS installation.
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia = {
    modesetting.enable = true;
    open = true;
    nvidiaSettings = true;
    powerManagement = {
      enable = true;
      # 在 595 open 驱动下，开启内核挂起通知器与显存保护（NVreg_PreserveVideoMemoryAllocations=1
      # 与 NVreg_UseKernelSuspendNotifiers=1），从驱动层保证睡眠前备份显存、唤醒后恢复，
      # 消除丢失显存导致的 Xid 13 与 DRM Flip event timeout 黑屏死锁。
      kernelSuspendNotifier = true;
    };
  };

  # uv（home-manager programs.uv）下载的 python-build-standalone 解释器和
  # 部分带 C 扩展的 wheel 是面向通用 Linux 的预编译二进制，硬编码 FHS 路径，
  # 在 NixOS 上找不到动态链接器（Could not start dynamically linked
  # executable）。nix-ld 提供 /lib64/ld-linux-x86-64.so.2 垫片把它们重定向
  # 到 nix store 的链接器与库。specify-cli 等纯 python 工具通常不触发，
  # 但 uv 装带原生扩展的工具时必需。libraries 缺啥补啥（libstdc++ 最常见）。
  programs.nix-ld = {
    enable = true;
    libraries = with pkgs; [
      stdenv.cc.cc.lib # libstdc++.so.6 — 大多数 wheel 需要
      zlib
      openssl
      libffi
      glibc
    ];
  };

  # 挂起策略：启用系统挂起，使用 s2idle (freeze) 代替 S3 deep。
  # 原因：Turing TU106 (GTX 1650) 在 S3 deep 唤醒时 PCIe 掉电会导致 GSP 固件失联
  # 与 DRM plane fence 信号量初始化失败（Error code: -11）；而 s2idle 保持 PCIe 总线供电，
  # 显存完整自刷新，唤醒即时且稳定。
  # 保持 hibernate / hybrid-sleep 禁用。
  systemd.sleep.settings.Sleep = {
    AllowSuspend = "yes";
    AllowHibernation = "no";
    AllowHybridSleep = "no";
    AllowSuspendThenHibernate = "no";
    SuspendState = "freeze";
  };

  # The data filesystem roots should remain writable by the primary user.
  systemd.tmpfiles.rules = [
    "d /data 0755 liou users -"
    "d /data-ssd 0755 liou users -"
  ];

  # Ensure this controller can still deploy after the liu -> liou rename.
  users.users.liou = {
    uid = 1000;
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJnZ+9jLuW94fQKt+kP7X4uoAverEG5/CwQ0waVFZG9x"
    ];
  };
  users.users.root.openssh.authorizedKeys.keys = [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJnZ+9jLuW94fQKt+kP7X4uoAverEG5/CwQ0waVFZG9x"
  ];
}
