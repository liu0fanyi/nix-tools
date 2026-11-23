{ pkgs }:
let
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/jlsspnfixa73zlrw0ykgw8whngkkmkkk-knowledge-cards-0.1.19";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "knowledge-cards-0.1.19";
  paths = [ cached ];
  passthru.binaryPath = cached;
  meta = { description = "Local-first knowledge cards"; mainProgram = "knowledge-cards"; platforms = [ "x86_64-linux" ]; };
}
