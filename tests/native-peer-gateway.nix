{ infrastructure, tagAll, dufsPlus, settings }:
let
  lock = builtins.fromJSON (builtins.readFile (tagAll + "/devenv.lock"));
  pkgs = import (builtins.fetchTree lock.nodes.nixpkgs.locked).outPath { system = "x86_64-linux"; };
  params = builtins.fromJSON (builtins.readFile settings);
in import (infrastructure + "/packages/native-workspace.nix") {
  inherit pkgs;
  frontendRoot = dufsPlus + "/dist";
  peerAdministration = true;
  inherit (params) authFile fileSocket gatewayPort corePort peer;
}
