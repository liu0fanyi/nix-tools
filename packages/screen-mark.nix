{ pkgs }:
let
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/c0n5h4c9y5xihxj0ppfs2w8ixdcba1kl-screen-mark-0.1.0";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "screen-mark-0.1.0";
  paths = [ cached ];
  passthru.binaryPath = cached;
  meta = { description = "Screenshot editor with partial annotation eraser"; mainProgram = "screen-mark"; platforms = [ "x86_64-linux" ]; };
}
