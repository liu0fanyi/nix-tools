{ lib, ... }:

{
  imports = [ ./hardware-configuration.nix ];

  networking.hostName = "liu-bigpc";

  # Preserve the state version of the existing installation. This does not
  # control the NixOS package version supplied by flake.lock.
  system.stateVersion = lib.mkForce "24.11";

  # The existing ESP and firmware already contain systemd-boot and Windows
  # Boot Manager entries. Update files on the ESP without rewriting firmware
  # NVRAM; bootctl variable updates fail on this dual-boot machine with ESRCH.
  boot.loader.grub.enable = false;
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = false;

  # GTX 1650 (Turing), already proven with the old NixOS installation.
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia = {
    modesetting.enable = true;
    open = true;
    nvidiaSettings = true;
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

  # The data filesystem root should remain writable by the primary user.
  systemd.tmpfiles.rules = [ "d /data 0755 liou users -" ];

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
