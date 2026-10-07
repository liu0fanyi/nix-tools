{ infrastructure, tagAll, dufsPlus, hostSource ? "/home/liou/nix-tools", processing ? false }:
let
  host = builtins.getFlake hostSource;
  native = builtins.fromJSON (builtins.readFile (tagAll + "/.devenv/native-core-results.json"));
  processingReport = builtins.fromJSON (builtins.readFile
    (tagAll + "/specs/024-native-core-release/workspace-pdf-results.json"));
  selectedPackage = if processing then processingReport.package else native.package;
  pdfContainer = if processing then {
    image = processingReport.image_id;
    stateDirectory = "/home/liou/.local/share/tag-all/pc-native/pdf-executor";
    connection = "unix:///run/user/1000/podman/podman.sock";
  } else null;
  candidate = host.nixosConfigurations.liu-bigpc.extendModules {
    modules = [ (import (infrastructure + "/nixos/modules/native-pc-candidate.nix") {
      tagAllSource = tagAll;
      corePackage = builtins.storePath selectedPackage;
      inherit pdfContainer;
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
  processingSelection = pdfContainer;
  services = candidate.config.home-manager.users.liou.systemd.user.services;
  target = candidate.config.home-manager.users.liou.systemd.user.targets.tag-native-stack;
}
