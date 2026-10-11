{ tagAll ? /data/project/tag-all }:
let
  lock = builtins.fromJSON (builtins.readFile (tagAll + "/devenv.lock"));
  pkgs = import (builtins.fetchTree lock.nodes.nixpkgs.locked).outPath { system = "x86_64-linux"; };
in pkgs.symlinkJoin {
  name = "tag-entry-trust-test-tools";
  paths = [ pkgs.authelia pkgs.haproxy ];
}
