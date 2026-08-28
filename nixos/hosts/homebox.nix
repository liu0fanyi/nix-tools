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
  # Syncthing is paired only across the trusted IPv4 LAN. Keep these ports
  # closed to global IPv6 and all non-LAN IPv4 sources.
  networking.firewall.extraCommands = ''
    iptables -w -A nixos-fw -s 192.168.1.0/24 -p tcp --dport 22000 -j nixos-fw-accept
    iptables -w -A nixos-fw -s 192.168.1.0/24 -p udp --dport 22000 -j nixos-fw-accept
    iptables -w -A nixos-fw -s 192.168.1.0/24 -p udp --dport 21027 -j nixos-fw-accept
  '';

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
