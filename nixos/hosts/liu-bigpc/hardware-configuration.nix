# Captured from liu-bigpc on NixOS 25.05. Keep filesystem UUIDs specific to
# this dual-boot machine; do not replace this with homebox hardware data.
{ config, lib, modulesPath, ... }:

{
  imports = [ (modulesPath + "/installer/scan/not-detected.nix") ];

  boot.initrd.availableKernelModules = [
    "xhci_pci"
    "ahci"
    "nvme"
    "usbhid"
    "usb_storage"
    "sd_mod"
  ];
  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ "kvm-intel" ];
  boot.extraModulePackages = [ ];

  fileSystems."/" = {
    device = "/dev/disk/by-uuid/428f77c1-1fe1-47f4-8457-9944aec9e0e9";
    fsType = "ext4";
  };

  # This ESP is shared with Windows. It must be mounted, never reformatted.
  fileSystems."/boot" = {
    device = "/dev/disk/by-uuid/332B-F609";
    fsType = "vfat";
    options = [
      "fmask=0077"
      "dmask=0077"
    ];
  };

  # The dedicated 500 GB data disk is formatted separately with label data.
  fileSystems."/data" = {
    device = "/dev/disk/by-label/data";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.device-timeout=5s"
    ];
  };

  swapDevices = [
    { device = "/dev/disk/by-uuid/ef3a79ac-83ff-4bbb-ba48-1b371418d9e3"; }
  ];

  networking.useDHCP = lib.mkDefault true;
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
  hardware.cpu.intel.updateMicrocode =
    lib.mkDefault config.hardware.enableRedistributableFirmware;
}
