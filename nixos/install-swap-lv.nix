# Installation-only overrides for nixos-anywhere.
# The running homebox keeps its swapfile because its existing VG has no free
# extents. A fresh disko install can reserve a dedicated LVM swap LV instead.
{ lib, installSwapSizeGiB ? 16, ... }:

{
  disko.devices.lvm_vg.pool.lvs.swap = {
    size = "${toString installSwapSizeGiB}G";
    content = {
      type = "swap";
      resumeDevice = true;
    };
  };

  # configuration.nix is shared with the already-installed machine. Replace
  # its swapfile/resume settings for a fresh install with the disko LV.
  swapDevices = lib.mkForce [
    {
      device = "/dev/mapper/pool-swap";
    }
  ];
  boot.resumeDevice = lib.mkForce "/dev/mapper/pool-swap";
  # boot.resumeDevice alone is not enough for this install profile: the
  # explicit override must also retain the kernel resume parameter. Without
  # it, hibernation can write an image to swap but the next boot starts cold.
  boot.kernelParams = lib.mkForce [ "resume=/dev/mapper/pool-swap" ];
}
