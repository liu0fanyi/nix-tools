# Standalone local runtime; does not change the host or Home Manager.
let
  flake = builtins.getFlake (toString ../.);
  pkgs = import flake.inputs.nixpkgs { system = builtins.currentSystem; };
  runner = pkgs.writeShellScriptBin "ocr-run" ''
    export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.zlib ]}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
    exec "$@"
  '';
in pkgs.buildEnv {
  name = "subtitle-ocr-runtime";
  paths = [ pkgs.python312 pkgs.uv pkgs.ffmpeg runner ];
}
