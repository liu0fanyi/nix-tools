{ infrastructure, tagAll, dufsPlus, enabled ? true, configured ? false }:
let
  lock = builtins.fromJSON (builtins.readFile (infrastructure + "/flake.lock"));
  hm = builtins.fetchTree lock.nodes.home-manager.locked;
  product = builtins.fromJSON (builtins.readFile (tagAll + "/devenv.lock"));
  pkgs = import (builtins.fetchTree product.nodes.nixpkgs.locked).outPath { system = "x86_64-linux"; };
  report = builtins.fromJSON (builtins.readFile (tagAll + "/.devenv/native-core-results.json"));
  evaluated = import (hm.outPath + "/modules") {
    inherit pkgs;
    configuration = {
      imports = [ (import (infrastructure + "/home-manager/native-stack.nix") { tagAllSource = tagAll; }) ];
      home.username = "nativecheck";
      home.homeDirectory = "/tmp/nativecheck";
      home.stateVersion = "25.11";
      services.tag-native-stack = if enabled then {
        enable = true;
        package = builtins.storePath report.package;
        frontendRoot = dufsPlus + "/dist";
        workspace = "/tmp/nativecheck/work space % $ 中文";
        authFile = "/tmp/nativecheck/auth.entries";
        syncMode = if configured then "configured" else "isolated";
        configurationFile = if configured then "/tmp/nativecheck/runtime node.toml" else null;
        environmentFile = if configured then "/tmp/nativecheck/private auth % $ 中文.env" else null;
      } else {};
    };
  };
in {
  generation = evaluated.activationPackage;
  assertions = map (item: item.assertion) evaluated.config.assertions;
  services = builtins.attrNames evaluated.config.systemd.user.services;
}
