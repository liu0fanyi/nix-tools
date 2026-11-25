{ pkgs }:
let
  packagePath = "/nix/store/8m2kcl18br9i82jjin7zs8r33vg99spn-knowledge-cards-0.1.25";
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = packagePath;
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "knowledge-cards-0.1.25";
  paths = [ cached ];
  passthru.binaryPath = packagePath;
  meta = { description = "Local-first knowledge cards"; mainProgram = "knowledge-cards"; platforms = [ "x86_64-linux" ]; };
}
