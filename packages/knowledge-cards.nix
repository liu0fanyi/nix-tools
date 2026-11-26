{ pkgs }:
let
  packagePath = "/nix/store/lz5kb01m4rz0a5xbw45zzhwdkxy3nqvg-knowledge-cards-0.1.27";
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = packagePath;
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "knowledge-cards-0.1.27";
  paths = [ cached ];
  passthru.binaryPath = packagePath;
  meta = { description = "Local-first knowledge cards"; mainProgram = "knowledge-cards"; platforms = [ "x86_64-linux" ]; };
}
