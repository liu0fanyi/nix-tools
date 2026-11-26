{ pkgs }:
let
  packagePath = "/nix/store/rfmsklixfivdgqswavpkxsvpwa8znhj9-knowledge-cards-0.1.26";
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = packagePath;
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "knowledge-cards-0.1.26";
  paths = [ cached ];
  passthru.binaryPath = packagePath;
  meta = { description = "Local-first knowledge cards"; mainProgram = "knowledge-cards"; platforms = [ "x86_64-linux" ]; };
}
