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

  # Migrated from the old 120 GB SATA SSD to the KIOXIA 480 GB SATA SSD.
  fileSystems."/" = {
    device = "/dev/disk/by-uuid/587d3eb3-3d34-47b5-bec1-391bbf56e634";
    fsType = "ext4";
  };

  # Dedicated NixOS ESP on the KIOXIA SSD. The pre-existing Windows ESP on
  # partition 3 is deliberately kept separate and must never be reformatted.
  fileSystems."/boot" = {
    device = "/dev/disk/by-uuid/2909-BA9A";
    fsType = "vfat";
    options = [
      "fmask=0077"
      "dmask=0077"
    ];
  };

  # The dedicated 500 GB ext4 data disk is identified by filesystem UUID.
  fileSystems."/data" = {
    device = "/dev/disk/by-uuid/92af0d70-de16-4502-93fb-651392709a7b";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.device-timeout=5s"
    ];
  };

  # Reused old 120 GB NixOS SSD, now a standalone data filesystem.
  fileSystems."/data-ssd" = {
    device = "/dev/disk/by-uuid/b2f8be6a-6739-46c7-8b85-070ac915c206";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.device-timeout=5s"
    ];
  };

  swapDevices = [
    { device = "/dev/disk/by-uuid/bb4a5c9c-268f-4ddd-816a-2d3d062a6137"; }
  ];

  networking.useDHCP = lib.mkDefault true;
  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
  hardware.cpu.intel.updateMicrocode =
    lib.mkDefault config.hardware.enableRedistributableFirmware;
}
