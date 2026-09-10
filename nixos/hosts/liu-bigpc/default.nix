{ lib, pkgs, ... }:

{
  imports = [ ./hardware-configuration.nix ];

  networking.hostName = "liu-bigpc";

  # Legacy Windows RF configuration tools and RAR extraction support.
  environment.systemPackages = [
    pkgs.unar
    pkgs.wineWow64Packages.stable
  ];

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

  # The previous NixOS generation resumed from deep S3 but immediately logged
  # NVIDIA Xid 13 errors in niri and LocalSend, leaving the display black.
  # Keep display power saving in the user session, but disable system sleep
  # until NVIDIA suspend/resume is tested deliberately on the new generation.
  systemd.sleep.settings.Sleep = {
    AllowSuspend = "no";
    AllowHibernation = "no";
    AllowHybridSleep = "no";
    AllowSuspendThenHibernate = "no";
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
