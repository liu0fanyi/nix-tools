{ ... }:
{
  # NUC8i5BEH Samsung 970 EVO 250GB ONLY. User explicitly chose no encryption.
  disko.devices.disk.system = {
    type = "disk";
    device = "/dev/disk/by-id/nvme-eui.0025385691b22dce";
    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "1G";
          type = "EF00";
          content = { type = "filesystem"; format = "vfat"; mountpoint = "/boot"; mountOptions = [ "umask=0077" ]; };
        };
        swap = { size = "16G"; content = { type = "swap"; }; };
        root = {
          size = "100%";
          content = { type = "filesystem"; format = "ext4"; mountpoint = "/"; };
        };
      };
    };
  };
}
