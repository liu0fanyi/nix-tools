{ infrastructure ? /home/liou/nix-tools, tagAll ? /data/project/tag-all, whisperPackage, applicationEntry ? false, dufsPlus ? /data/project/dufs-plus,
  stateRoot ? "/home/liou/.local/share/tag-all/nuc-native" }:
let
  product = builtins.fromJSON (builtins.readFile (tagAll + "/devenv.lock"));
  pkgs = import (builtins.fetchTree product.nodes.nixpkgs.locked).outPath { system = "x86_64-linux"; };
  lock = builtins.fromJSON (builtins.readFile (infrastructure + "/flake.lock"));
  hm = builtins.fetchTree lock.nodes.home-manager.locked;
  report = builtins.fromJSON (builtins.readFile (tagAll + (if applicationEntry then "/.devenv/application-entry-package-results.json" else "/.devenv/native-workspace-results.json")));
in import (infrastructure + "/packages/native-nuc-candidate.nix") {
  inherit pkgs stateRoot applicationEntry;
  frontendRoot = if applicationEntry then builtins.path { path = dufsPlus + "/dist"; name = "dufs-plus-nuc-frontend"; } else null;
  tagAllSource = tagAll;
  homeManagerSource = hm.outPath;
  package = builtins.storePath report.package;
  whisperPackage = builtins.storePath whisperPackage;
  toolArchive = builtins.storePath report.tool_archive;
  toolImage = report.image_id;
  toolSha256 = report.archive_sha256;
}
