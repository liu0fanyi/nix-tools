{ pkgs }:
let
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/1xy105v07acm26xzbjclpi3iw51wn4wf-knowledge-cards-0.1.0";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "knowledge-cards-0.1.0";
  paths = [ cached ];
  passthru.binaryPath = cached;
  meta = { description = "Local-first knowledge cards"; mainProgram = "knowledge-cards"; platforms = [ "x86_64-linux" ]; };
}
