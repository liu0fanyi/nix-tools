{
  pkgs,
  lib,
  config,
  ...
}:

{
  home.packages = with pkgs; [
    podman
    skopeo
    buildah
    slirp4netns
    fuse-overlayfs
  ];

  # Enable Rootless Podman and initialize required containers
  services.podman = {
    enable = true;
    containers = {
      dufs = {
        image = "docker.io/sigoden/dufs";
        autoStart = true;
        autoUpdate = "registry";
        # Internal proxy port for Caddy
        ports = [ "127.0.0.1:5005:5000" ];
        # Mount host directory for storage
        volumes = [ "%h/dufs:/data" ];
        extraConfig = {
          Container = {
            # Pure read-only mode with symlink support. No -A or -w means no write access.
            Exec = "/data --allow-symlink";
          };
        };
      };

      tag-server = {
        # Using the tag-server container built via tag-all/Containerfile
        image = "tag-server:latest";
        autoStart = true;
        ports = [ "127.0.0.1:8081:8081" ];
        volumes = [
          "%h/dufs:/workspace"
          "%h/dufs:/data"
        ];
        extraConfig = {
          Container = {
            # Ensure absolute paths match the container volumes above
            # The database tag_all.db will now be located at ~/dufs/tag_all.db on the host
            Exec = "--database /data/tag_all.db --workspace /workspace --addr 0.0.0.0:8081";
          };
        };
      };
    };
  };

  # Podman socket logic
  systemd.user.sockets.podman = {
    Unit = {
      Description = "Podman API Socket";
    };
    Socket = {
      ListenStream = "%t/podman/podman.sock";
      SocketMode = "0660";
    };
    Install = {
      WantedBy = [ "sockets.target" ];
    };
  };

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

  # Podman PATH Injection Drop-ins
  home.file.".config/systemd/user/podman-dufs.service.d/override.conf".text = ''
    [Service]
    Environment="PATH=/usr/bin:/bin:${lib.makeBinPath [ pkgs.podman ]}"
  '';

  home.file.".config/systemd/user/podman-tag-server.service.d/override.conf".text = ''
    [Service]
    Environment="PATH=/usr/bin:/bin:${lib.makeBinPath [ pkgs.podman ]}"
  '';
}
