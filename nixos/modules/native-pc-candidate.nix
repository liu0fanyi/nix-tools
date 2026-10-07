# Read-only candidate factory. Imported only by the preflight build, never automatically.
{ tagAllSource, corePackage, frontendRoot, pdfContainer ? null }:
{ config, lib, pkgs, ... }:
let
  guard = mode: "${pkgs.python3}/bin/python3 ${../../scripts/native_pc_mode_guard.py} --mode ${mode} --podman ${pkgs.podman}/bin/podman --systemctl ${pkgs.systemd}/bin/systemctl";
  root = "/home/liou/.local/share/tag-all/pc-native";
in {
  assertions = [ { assertion = config.networking.hostName == "liu-bigpc" && config.users.users.liou.uid == 1000; message = "Native PC candidate is limited to liu-bigpc user liou uid 1000."; } ];
  home-manager.users.liou = {
    imports = [ (import ../../home-manager/native-stack.nix { inherit tagAllSource; }) ];
    services.tag-native-stack = {
      enable = true;
      package = corePackage;
      inherit frontendRoot pdfContainer;
      nodeId = "pc";
      workspace = "/home/liou/dufs-lan";
      workspaceMounts.project = "/data/project";
      gatewayPort = 5006;
      corePort = 18081;
      configurationFile = root + "/config/node.toml";
      environmentFile = root + "/config/peer-admin.env";
      authFile = root + "/config/basic.entries";
      syncMode = "configured";
      peer = {
        enable = true;
        tlsMode = "internal";
        storageDirectory = root + "/peer-caddy/caddy";
        serverName = "liu-bigpc.local";
        listenAddress = "192.168.1.100";
        port = 5009;
        allowedNetworks = [ "192.168.1.0/24" ];
      };
    };
    services.tag-all-core.stateDirectory = root + "/data";
    # Candidate activation alone cannot create an empty replacement database.
    systemd.user.targets.tag-native-stack.Unit.ConditionPathExists = [ (root + "/ready") ("!" + root + "/container-mode") ];
    systemd.user.services = {
      tag-all-core.Unit.After = [ "podman.socket" ];
      tag-all-core.Unit.Wants = [ "podman.socket" ];
      tag-native-files.Unit.After = [ "podman.socket" ];
      tag-native-files.Unit.Wants = [ "podman.socket" ];
      tag-native-workspace.Unit.After = [ "podman.socket" ];
      tag-native-workspace.Unit.Wants = [ "podman.socket" ];
      tag-all-core.Service.ExecCondition = guard "native";
      tag-native-files.Service.ExecCondition = guard "native";
      tag-native-workspace.Service.ExecCondition = guard "native";
      tag-all-core.Unit.ConditionPathExists = [ (root + "/ready") ("!" + root + "/container-mode") ];
      tag-native-files.Unit.ConditionPathExists = [ (root + "/ready") ("!" + root + "/container-mode") ];
      tag-native-workspace.Unit.ConditionPathExists = [ (root + "/ready") ("!" + root + "/container-mode") ];
      pc-private-node-restore = {
        Install.WantedBy = lib.mkForce [ "default.target" ];
        Service.ExecCondition = guard "container";
        Service.ExecStart = lib.mkForce "${pkgs.writeShellScript "restore-native-pc-fallback" ''
          set -eu
          ${pkgs.podman}/bin/podman --remote --url unix:///run/user/1000/podman/podman.sock start \
            dufs-plus-pc_tag-server_1 dufs-plus-pc_peer-discovery_1 \
            dufs-plus-pc_peer-gateway_1 dufs-plus-pc_dufs_1 dufs-plus-pc_caddy_1
        ''}";
        Unit.ConditionPathExists = lib.mkForce [ (root + "/ready") (root + "/container-mode") ];
      };
    };
  };
}
