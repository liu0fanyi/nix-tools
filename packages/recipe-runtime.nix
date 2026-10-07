# Recipe processing without OCR libraries, models or OCR launchers.
let
  flake = builtins.getFlake (toString ../.);
  pkgs = import flake.inputs.nixpkgs { system = builtins.currentSystem; };
in pkgs.buildEnv {
  name = "recipe-runtime";
  paths = [ pkgs.python312 pkgs.uv pkgs.ffmpeg pkgs.yt-dlp ];
}
