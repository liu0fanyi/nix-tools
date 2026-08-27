{
  inputs,
  lib,
  pkgs,
  ...
}:

let
  chatgptFiles = pkgs.stdenvNoCC.mkDerivation {
    pname = "chatgpt-desktop-files";
    version = "latest";
    src = inputs.chatgpt-deb;

    nativeBuildInputs = [ pkgs.dpkg ];
    dontConfigure = true;
    dontBuild = true;

    unpackPhase = ''
      runHook preUnpack
      dpkg-deb -x "$src" unpacked
      runHook postUnpack
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p "$out/bin" "$out/lib"
      cp -a unpacked/usr/bin/. "$out/bin/"
      cp -a unpacked/usr/lib/chatgpt "$out/lib/chatgpt"
      runHook postInstall
    '';
  };

  chatgptFhs = pkgs.buildFHSEnv {
    name = "chatgpt";
    targetPkgs = p: [
      chatgptFiles
      p.alsa-lib
      p.at-spi2-atk
      p.at-spi2-core
      p.atk
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
      p.libdrm
      p.libgbm
      p.libglvnd
      p.libnotify
      p.libpulseaudio
      p.libsecret
      p.libusb1
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
      p.libXtst
      p.libxcb
      p.libxkbcommon
      p.mesa
      p.nspr
      p.nss
      p.pango
      p.pipewire
      p.stdenv.cc.cc.lib
      p.systemd
      p.wayland
      p.xz
      p.zlib
      p.zstd
    ];
    runScript = "${chatgptFiles}/bin/chatgpt";
  };

  desktopAssets = pkgs.stdenvNoCC.mkDerivation {
    pname = "chatgpt-desktop-assets";
    version = "latest";
    src = inputs.chatgpt-deb;

    nativeBuildInputs = [ pkgs.dpkg ];
    dontConfigure = true;
    dontBuild = true;

    unpackPhase = ''
      runHook preUnpack
      dpkg-deb -x "$src" unpacked
      runHook postUnpack
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p "$out/share/applications" "$out/share/pixmaps" \
        "$out/share/icons/hicolor/256x256/apps"
      cp -a unpacked/usr/share/applications/. "$out/share/applications/"
      cp -a unpacked/usr/share/pixmaps/. "$out/share/pixmaps/"
      install -Dm644 unpacked/usr/share/pixmaps/chatgpt.png \
        "$out/share/icons/hicolor/256x256/apps/chatgpt.png"
      runHook postInstall
    '';
  };

  chatgptDesktop = pkgs.buildEnv {
    name = "chatgpt-desktop";
    paths = [
      chatgptFhs
      desktopAssets
    ];
    meta = {
      description = "OpenAI ChatGPT desktop app with Codex support";
      homepage = "https://learn.chatgpt.com/docs/linux/linux-app";
      license = lib.licenses.unfree;
      mainProgram = "chatgpt";
      platforms = [ "x86_64-linux" ];
    };
  };
in
{
  home.packages = [ chatgptDesktop ];
}
