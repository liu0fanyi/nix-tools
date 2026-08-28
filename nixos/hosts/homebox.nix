{ ... }:

let
  lidSwitchAction = "suspend-then-hibernate";
in
{
  imports = [
    ../disk-config.nix
    ../hardware-configuration.nix
  ];

  networking.hostName = "homebox";

  boot.loader.efi.canTouchEfiVariables = true;
  boot.loader.grub = {
    enable = true;
    efiSupport = true;
    device = "nodev";
    efiInstallAsRemovable = false;
  };

  services.logind.settings.Login = {
    HandleLidSwitch = lidSwitchAction;
    HandleLidSwitchExternalPower = lidSwitchAction;
    HandleLidSwitchDocked = "ignore";
  };
  systemd.sleep.settings.Sleep.HibernateDelaySec = "1h";

  # The installed homebox has no free VG extents, so it resumes from a
  # swapfile. Fresh-install outputs override this with a dedicated swap LV.
  swapDevices = [
    {
      device = "/var/lib/swapfile";
      size = 16384;
    }
  ];
  boot.resumeDevice = "/dev/mapper/pool-root";
  boot.kernelParams = [ "resume_offset=60665856" ];
}
