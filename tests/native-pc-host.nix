{ infrastructure, tagAll, dufsPlus, hostSource ? "/home/liou/nix-tools" }:
let
  host = builtins.getFlake hostSource;
  native = builtins.fromJSON (builtins.readFile (tagAll + "/.devenv/native-core-results.json"));
  candidate = host.nixosConfigurations.liu-bigpc.extendModules {
    modules = [ (import (infrastructure + "/nixos/modules/native-pc-candidate.nix") {
      tagAllSource = tagAll;
      corePackage = builtins.storePath native.package;
      frontendRoot = builtins.path { path = dufsPlus + "/dist"; name = "dufs-plus-native-frontend"; };
    }) ];
  };
in {
  toplevel = candidate.config.system.build.toplevel;
  home = candidate.config.home-manager.users.liou.home.activationPackage;
  hostname = candidate.config.networking.hostName;
  hostSourceSnapshot = host.outPath;
  homeBackupExtension = candidate.config.home-manager.backupFileExtension;
  services = candidate.config.home-manager.users.liou.systemd.user.services;
  target = candidate.config.home-manager.users.liou.systemd.user.targets.tag-native-stack;
}
