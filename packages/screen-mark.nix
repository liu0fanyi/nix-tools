{ pkgs }:
let
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/j1cvwiafizx98f8qzwj2n6szalsqldm8-screen-mark-0.1.0";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "screen-mark-0.1.0";
  paths = [ cached ];
  passthru.binaryPath = cached;
  meta = { description = "Screenshot editor with partial annotation eraser"; mainProgram = "screen-mark"; platforms = [ "x86_64-linux" ]; };
}
