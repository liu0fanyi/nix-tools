# PC-only UEFI/disko test. Upstream maps the real disk identity to virtual vdb/vda.
# No host block device is passed to QEMU; 32 GiB is sparse test storage only.
let
  flake = builtins.getFlake ("path:" + toString ../..);
  nuc = flake.nixosConfigurations.nuc;
  lib = flake.inputs.nixpkgs.lib;
in
flake.inputs.disko.lib.testLib.makeDiskoTest {
  name = "nuc-uefi-install";
  pkgs = nuc.pkgs;
  extendModules = nuc.extendModules;
  disko-config = builtins.removeAttrs nuc.config [ "_module" ];
  testMode = "direct";
  efi = true;
  extraInstallerConfig = {
    virtualisation.emptyDiskImages = lib.mkForce [ 32768 ];
    virtualisation.memorySize = 4096;
    virtualisation.cores = 4;
  };
  extraTestScript = ''
    machine.succeed("test -d /sys/firmware/efi")
    machine.succeed("findmnt -n -o FSTYPE / | grep -x ext4")
    machine.succeed("findmnt -n -o FSTYPE /boot | grep -x vfat")
    machine.succeed("bootctl is-installed")
    machine.succeed("test $(blkid -s TYPE -o value /dev/vda2) = swap")
    machine.succeed("test $(blockdev --getsize64 /dev/vda2) = 17179869184")
    machine.succeed("test $(blkid -s TYPE -o value /dev/vda3) = ext4")
  '';
}
