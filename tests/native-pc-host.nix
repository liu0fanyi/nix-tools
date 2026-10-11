{ infrastructure, tagAll, dufsPlus, hostSource ? "/home/liou/nix-tools", processing ? false, applicationEntry ? false }:
let
  host = builtins.getFlake hostSource;
  native = builtins.fromJSON (builtins.readFile (tagAll + "/.devenv/native-core-results.json"));
  processingReport = builtins.fromJSON (builtins.readFile
    (tagAll + (if applicationEntry then "/.devenv/application-entry-package-results.json" else "/.devenv/native-workspace-results.json")));
  selectedPackage = assert !applicationEntry || processing; if processing then processingReport.package else native.package;
  toolRoot = "/home/liou/.local/share/tag-all/pc-native/tools";
  toolRuntime = if processing then {
    image = processingReport.image_id;
    archive = builtins.storePath processingReport.tool_archive;
    archiveSha256 = processingReport.archive_sha256;
    stateDirectory = toolRoot;
  } else null;
  processingContainers = if processing then builtins.listToAttrs (map (name: {
    inherit name;
    value = {
      image = processingReport.image_id;
      stateDirectory = "/home/liou/.local/share/tag-all/pc-native/executors/" + name;
      connection = "unix://${toolRoot}/runtime.sock";
    };
  }) [ "pdf" "archive" "audioVideo" "epub" ]) else null;
  candidate = host.nixosConfigurations.liu-bigpc.extendModules {
    modules = [ (import (infrastructure + "/nixos/modules/native-pc-candidate.nix") {
      tagAllSource = tagAll;
      corePackage = builtins.storePath selectedPackage;
      inherit processingContainers toolRuntime applicationEntry;
      frontendRoot = builtins.path { path = dufsPlus + "/dist"; name = "dufs-plus-native-frontend"; };
    }) ];
  };
in {
  toplevel = candidate.config.system.build.toplevel;
  home = candidate.config.home-manager.users.liou.home.activationPackage;
  hostname = candidate.config.networking.hostName;
  hostSourceSnapshot = host.outPath;
  homeBackupExtension = candidate.config.home-manager.backupFileExtension;
  nativePackage = selectedPackage;
  processingSelection = processingContainers;
  toolRuntimeSelection = toolRuntime;
  services = candidate.config.home-manager.users.liou.systemd.user.services;
  entryConfiguration = if applicationEntry then {
    peer_socket = "/home/liou/.local/share/tag-all/pc-native/sockets/peer.sock";
    peer_authorities = [ "liu-bigpc.local:5009" ];
    peer_write_delegation = true;
  } else null;
  gateway = let cfg = candidate.config.home-manager.users.liou.services.tag-native-workspace; in
    import (infrastructure + "/packages/native-workspace.nix") {
      pkgs = host.inputs.nixpkgs.legacyPackages.x86_64-linux;
      inherit (cfg) frontendRoot authFile fileSocket gatewayPort corePort localAuthentication applicationEntry;
      peer = if cfg.peer.enable then cfg.peer else null;
      peerSocket = if cfg.applicationEntry then cfg.peerSocket else null;
      peerAdministration = cfg.administratorEnvironmentFile != null;
    };
  target = candidate.config.home-manager.users.liou.systemd.user.targets.tag-native-stack;
}
