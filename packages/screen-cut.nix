{ pkgs }:
let
  # Published desktop bundle; independent of the author's checkout and Cargo.
  cached = builtins.fetchClosure {
    fromStore = "https://liu0fanyi-nix.cachix.org";
    fromPath = "/nix/store/gdybxp8862gwmy6c5qfc70wzm0p072j2-screen-cut-0.1.0";
    inputAddressed = true;
  };
in pkgs.symlinkJoin {
  name = "screen-cut-0.1.0";
  paths = [ cached ];
  meta = {
    description = "Vim-style recording editor";
    mainProgram = "screen-cut";
    platforms = [ "x86_64-linux" ];
  };
}
