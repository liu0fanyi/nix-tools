{
  lib,
  stdenvNoCC,
  fetchurl,
  dpkg,
  buildFHSEnv,
  makeDesktopItem,
  symlinkJoin,
  writeShellScript,
  legacyGtk,
}:
let
  version = "8.7.0";
  files = stdenvNoCC.mkDerivation {
    pname = "baidunetdisk-files";
    inherit version;
    src = fetchurl {
      url = "https://pkg-ant.baidu.com/issue/netdisk/LinuxGuanjia/${version}/baidunetdisk_${version}_amd64.deb";
      hash = "sha256-7HHCrRFRYJ/Q2LhtlRhMC0V9bbWqGIYeCxX8I8z+Afc=";
    };

    nativeBuildInputs = [ dpkg ];
    dontConfigure = true;
    dontBuild = true;
    unpackPhase = ''
      runHook preUnpack
      dpkg-deb -x "$src" unpacked
      runHook postUnpack
    '';
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/opt" "$out/share/icons/hicolor/scalable/apps"
      cp -a unpacked/opt/baidunetdisk "$out/opt/"
      install -Dm644 unpacked/usr/share/icons/hicolor/scalable/apps/baidunetdisk.svg \
        "$out/share/icons/hicolor/scalable/apps/baidunetdisk.svg"
      runHook postInstall
    '';
  };

  launcher = writeShellScript "baidunetdisk-launcher" ''
    exec "${files}/opt/baidunetdisk/baidunetdisk" "$@"
  '';

  runtime = buildFHSEnv {
    pname = "baidunetdisk";
    inherit version;
    targetPkgs = p: [
      p.alsa-lib
      p.at-spi2-atk
      p.at-spi2-core
      p.cairo
      p.cups
      p.dbus
      p.expat
      p.fontconfig
      p.freetype
      p.gdk-pixbuf
      p.glib
      p.gsettings-desktop-schemas
      p.gtk3
      legacyGtk.atkmm
      legacyGtk.cairomm
      legacyGtk.glibmm
      legacyGtk.gtk2
      legacyGtk.gtkmm2
      legacyGtk.libsigcxx
      legacyGtk.pangomm
      p.libappindicator-gtk3
      p.libdrm
      p.libgbm
      p.libglvnd
      p.libnotify
      p.libpulseaudio
      p.libsecret
      p.libX11
      p.libXScrnSaver
      p.libXcomposite
      p.libXcursor
      p.libXdamage
      p.libXext
      p.libXfixes
      p.libXi
      p.libXrandr
      p.libXrender
      p.libXt
      p.libXtst
      p.libxcb
      p.libxkbcommon
      p.mesa
      p.nspr
      p.nss
      p.pango
      p.stdenv.cc.cc.lib
      p.systemd
      p.wayland
      p.zlib
    ];
    runScript = launcher;
  };

  desktop = makeDesktopItem {
    name = "baidunetdisk";
    desktopName = "百度网盘";
    exec = "baidunetdisk %U";
    icon = "baidunetdisk";
    categories = [ "Network" ];
    mimeTypes = [ "x-scheme-handler/baiduyunguanjia" ];
    startupWMClass = "baidunetdisk";
  };
in
symlinkJoin {
  name = "baidunetdisk-${version}";
  paths = [ runtime desktop files ];
  meta = {
    description = "Baidu Netdisk desktop client";
    homepage = "https://yun.baidu.com/download";
    license = lib.licenses.unfree;
    platforms = [ "x86_64-linux" ];
    mainProgram = "baidunetdisk";
  };
}
