{ pkgs, lib, config, ... }:
let
  secrets = builtins.fromJSON (builtins.readFile ../../secrets.json);
in
{
  services.podman.containers.ddns-go = {
    image = "docker.io/jeessy/ddns-go";
    autoStart = true;
    autoUpdate = "registry";
    network = [ "host" ];
    volumes = [
      "%h/.config/ddns-go:/root"
    ];
    extraConfig = {
      Container = {
        Exec = "-l 127.0.0.1:9876 -f 300";
      };
    };
  };

  home.file.".config/systemd/user/podman-ddns-go.service.d/override.conf".text = ''
    [Service]
    Environment="PATH=/usr/bin:/bin:${lib.makeBinPath [ pkgs.podman ]}"
    # CONFIG: Ensure config file exists to prevent first-run failure
    ExecStartPre=${pkgs.bash}/bin/bash -c '[ -f %h/.config/ddns-go/.ddns_go_config.yaml ] || ${pkgs.coreutils}/bin/touch %h/.config/ddns-go/.ddns_go_config.yaml'
    # CONFIG: Reset password on every start (ensures consistent state)
    ExecStartPre=${pkgs.podman}/bin/podman run --rm -v %h/.config/ddns-go:/root docker.io/jeessy/ddns-go -resetPassword ${secrets.ddns_password}
  '';
}
