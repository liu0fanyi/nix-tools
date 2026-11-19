{ pkgs }:
let
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/x75860n5c35i8r9rxc2bwqsrc858yrr2-screen-mark-0.2.0";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "screen-mark-0.2.0";
  paths = [ cached ];
  passthru.binaryPath = cached;
  meta = { description = "Image editor with annotation and manual color adjustments"; mainProgram = "screen-mark"; platforms = [ "x86_64-linux" ]; };
}
