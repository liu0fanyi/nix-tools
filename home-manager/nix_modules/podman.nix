{
  pkgs,
  lib,
  config,
  ...
}:
let
  cfg = config.features.podman;
in
{
  options.features.podman = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable Podman container tools";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = with pkgs; [
      podman
      podman-compose
      podman-tui
      skopeo
      buildah
      slirp4netns
      fuse-overlayfs
      ttyd
    ];

    # Enable the Podman socket for TUI/GUI tools
    systemd.user.sockets.podman = {
      Unit = {
        Description = "Podman API Socket";
      };
      Socket = {
        ListenStream = "%t/podman/podman.sock";
        SocketMode = "0660";
      };
      Install.WantedBy = [ "sockets.target" ];
    };

    # Corresponding service for the socket
    systemd.user.services.podman = {
      Unit = {
        Description = "Podman API Service";
        Requires = [ "podman.socket" ];
        After = [ "podman.socket" ];
      };
      Service = {
        Type = "exec";
        KillMode = "process";
        ExecStart = "${pkgs.podman}/bin/podman system service";
      };
    };

  };
}
