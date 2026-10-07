# Read-only candidate factory. Imported only by the preflight build, never automatically.
{ tagAllSource, corePackage, frontendRoot }:
{ config, lib, ... }:
let
  root = "/home/liou/.local/share/tag-all/pc-native";
in {
  assertions = [ { assertion = config.networking.hostName == "liu-bigpc" && config.users.users.liou.uid == 1000; message = "Native PC candidate is limited to liu-bigpc user liou uid 1000."; } ];
  home-manager.users.liou = {
    imports = [ (import ../../home-manager/native-stack.nix { inherit tagAllSource; }) ];
    services.tag-native-stack = {
      enable = true;
      package = corePackage;
      inherit frontendRoot;
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
      tag-all-core.Unit.ConditionPathExists = [ (root + "/ready") ("!" + root + "/container-mode") ];
      tag-native-files.Unit.ConditionPathExists = [ (root + "/ready") ("!" + root + "/container-mode") ];
      tag-native-workspace.Unit.ConditionPathExists = [ (root + "/ready") ("!" + root + "/container-mode") ];
      pc-private-node-restore = {
        Install.WantedBy = lib.mkForce [];
        Unit.ConditionPathExists = lib.mkForce [ (root + "/container-mode") ];
      };
    };
  };
}
