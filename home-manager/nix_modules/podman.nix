{ pkgs, lib, config, ... }:
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
      podman-tui
      skopeo
      buildah
      slirp4netns
      fuse-overlayfs
    ];

    home.activation.createPodmanVolumes = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      $DRY_RUN_CMD mkdir -p $VERBOSE_ARG \
        "$HOME/.config/ddns-go" \
        "$HOME/rustfs/data" \
        "$HOME/rustfs/logs"
    '';


    services.podman = {
      enable = true;
      containers = {
        ddns-go = {
          image = "docker.io/jeessy/ddns-go";
          network = "host";
          volumes = [
            "%h/.config/ddns-go:/root"
          ];
        };
        rustfs = {
          image = "docker.io/rustfs/rustfs:latest";
          ports = [
            "9000:9000"
            "9001:9001"
          ];
          volumes = [
            "%h/rustfs/data:/data:U"
            "%h/rustfs/logs:/logs:U"
          ];
        };
      };
    };

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
