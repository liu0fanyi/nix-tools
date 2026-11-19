{ pkgs }:
let
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/cbdpwacnqxv1w2zvr0wxw2mgkscp9jil-knowledge-cards-0.1.9";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "knowledge-cards-0.1.9";
  paths = [ cached ];
  passthru.binaryPath = cached;
  meta = { description = "Local-first knowledge cards"; mainProgram = "knowledge-cards"; platforms = [ "x86_64-linux" ]; };
}
