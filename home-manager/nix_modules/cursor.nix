{ pkgs, lib, config, isNixOS ? false, osConfig ? null, ... }:
let
  cfg = config.features.cursor;
  isLiuBigpc = isNixOS && osConfig != null && osConfig.networking.hostName == "liu-bigpc";
  # 官方版本领先 nixpkgs 时仅覆盖发行包；保留已有 Nix 打包、输入法和 Wayland 参数。
  cursorVersion = "3.30.14";
  cursorSource = pkgs.fetchurl {
    url = "https://downloads.cursor.com/production/5f54c8173e5552412beb40702adac16275677fa0/linux/x64/Cursor-3.30.14-x86_64.AppImage";
    hash = "sha256-6gfkPW9kEnXIhd4LqzZXVBEMVyH+hSTNuDtoUIDoq7k=";
  };
  cursorPkg = (pkgs.code-cursor.override {
    commandLineArgs = "--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations --enable-wayland-ime=true --wayland-text-input-version=3";
  }).overrideAttrs (old: {
    version = cursorVersion;
    src = pkgs.appimageTools.extract {
      pname = "cursor";
      version = cursorVersion;
      src = cursorSource;
    };
    # Cursor now resolves ripgrep through its per-platform npm package.
    postPatch = builtins.replaceStrings
      [ "@vscode/ripgrep/bin/rg" ]
      [ "@cursor/ripgrep-linux-x64/bin/rg" ]
      old.postPatch;
    sourceRoot = "cursor-${cursorVersion}-extracted/usr/share/cursor";
  });
in
{
  options.features.cursor = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = isLiuBigpc;
      description = "Enable Cursor AI code editor with Wayland and fcitx5 input method support";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cursorPkg ];
  };
}
