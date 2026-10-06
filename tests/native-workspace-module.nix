{ infrastructure, tagAll, dufsPlus }: 
let
  lock = builtins.fromJSON (builtins.readFile (infrastructure + "/flake.lock"));
  source = builtins.fetchTree lock.nodes.home-manager.locked;
  productLock = builtins.fromJSON (builtins.readFile (tagAll + "/devenv.lock"));
  nixpkgs = builtins.fetchTree productLock.nodes.nixpkgs.locked;
  pkgs = import nixpkgs.outPath { system = "x86_64-linux"; };
  report = builtins.fromJSON (builtins.readFile (tagAll + "/.devenv/native-core-results.json"));
  evaluate = enabled: import (source.outPath + "/modules") {
    inherit pkgs;
    configuration = { ... }: {
      imports = [ (tagAll + "/nix/home-manager-core.nix") (infrastructure + "/home-manager/native-workspace.nix") ];
      home.username = "nativecheck";
      home.homeDirectory = "/tmp/nativecheck";
      home.stateVersion = "25.11";
      services.tag-native-workspace = if enabled then { enable = true; frontendRoot = (dufsPlus + "/dist"); workspace = "/tmp/work space % $ 中文"; authFile = "/tmp/nativecheck/auth.entries"; } else {};
      services.tag-all-core = if enabled then {
        enable = true;
        package = builtins.storePath report.package;
        workspace = "/tmp/work space % $ 中文";
      } else {};
    };
  };
  enabled = (evaluate true).config;
  disabled = (evaluate false).config;
in {
  assertions = map (item: item.assertion) enabled.assertions;
  disabledHasService = builtins.hasAttr "tag-all-core" disabled.systemd.user.services;
  service = enabled.systemd.user.services.tag-native-workspace;
  files = enabled.systemd.user.services.tag-native-files;
  disabledHasGateway = builtins.hasAttr "tag-native-workspace" disabled.systemd.user.services;
}
