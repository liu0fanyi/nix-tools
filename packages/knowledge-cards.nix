{ pkgs }:
let
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/rd8qg93j7p95sqf6lj8s8f89lc5chhbi-knowledge-cards-0.1.3";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "knowledge-cards-0.1.3";
  paths = [ cached ];
  passthru.binaryPath = cached;
  meta = { description = "Local-first knowledge cards"; mainProgram = "knowledge-cards"; platforms = [ "x86_64-linux" ]; };
}
