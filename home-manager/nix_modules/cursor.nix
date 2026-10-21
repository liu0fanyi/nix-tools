{ pkgs, lib, config, isNixOS ? false, osConfig ? null, ... }:
let
  cfg = config.features.cursor;
  isLiuBigpc = isNixOS && osConfig != null && osConfig.networking.hostName == "liu-bigpc";
  # 官方版本领先 nixpkgs 时仅覆盖发行包；保留已有 Nix 打包、输入法和 Wayland 参数。
  cursorVersion = "3.25.6";
  cursorSource = pkgs.fetchurl {
    url = "https://downloads.cursor.com/production/f0df777c412b670d09e3eaf214967d779e67c088/linux/x64/Cursor-3.25.6-x86_64.AppImage";
    hash = "sha256-aapO64z5z1J7gxx/1y5Pe0NyaItKXT2q6fsxwjmIgKk=";
  };
  cursorPkg = (pkgs.code-cursor.override {
    commandLineArgs = "--ozone-platform-hint=auto --enable-features=WaylandWindowDecorations --enable-wayland-ime=true --wayland-text-input-version=3";
  }).overrideAttrs {
    version = cursorVersion;
    src = pkgs.appimageTools.extract {
      pname = "cursor";
      version = cursorVersion;
      src = cursorSource;
    };
    sourceRoot = "cursor-${cursorVersion}-extracted/usr/share/cursor";
  };
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
