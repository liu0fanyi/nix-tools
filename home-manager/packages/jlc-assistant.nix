{
  lib,
  stdenvNoCC,
  fetchurl,
  unzip,
  buildFHSEnv,
  makeDesktopItem,
  symlinkJoin,
  writeShellScript,
  scaleFactor ? null,
}:
let
  version = "5.0.69";
  files = stdenvNoCC.mkDerivation {
    pname = "jlc-assistant-files";
    inherit version;
    src = fetchurl {
      # Cache-bust the CDN's Brotli-compressed response: Nix's fetcher needs
      # the original ZIP bytes for the fixed-output hash.
      url = "https://download1.sz-jlc.com/pcAssit/${version}/JLCPcAssit-linux-x64-${version}.zip?raw=1";
      sha256 = "d943ebf9ee328a657cd608bdf301f637ea48988b57adeae1ae770fae944caacd";
      curlOptsList = [ "-H" "Accept-Encoding: identity" ];
    };
    nativeBuildInputs = [ unzip ];
    unpackPhase = ''
      runHook preUnpack
      unzip -q "$src"
      runHook postUnpack
    '';
    dontConfigure = true;
    dontBuild = true;
    dontFixup = true;
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/opt"
      cp -r "jlc-assistant-linux-x64-${version}/jlc-assistant" "$out/opt/jlc-assistant"
      # The upstream ZIP has no Unix mode bits; its installer chmods the
      # entire tree 777. Chromium must be able to exec both helpers.
      chmod 755 \
        "$out/opt/jlc-assistant/jlc-assistant" \
        "$out/opt/jlc-assistant/chrome_crashpad_handler" \
        "$out/opt/jlc-assistant/chrome-sandbox"
      for size in 16 32 48 64 128 256 512; do
        install -Dm644 "jlc-assistant-linux-x64-${version}/jlc-assistant/icon/png/$size.png" \
          "$out/share/icons/hicolor/''${size}x''${size}/apps/jlc-assistant.png"
      done
      runHook postInstall
    '';
  };
  launcher = writeShellScript "jlc-assistant-launcher" ''
    exec "${files}/opt/jlc-assistant/jlc-assistant" \
      ${lib.optionalString (scaleFactor != null) "--force-device-scale-factor=${toString scaleFactor}"} \
      "$@"
  '';
  runtime = buildFHSEnv {
    pname = "jlc-assistant";
    inherit version;
    targetPkgs =
      p: with p; [
        alsa-lib
        at-spi2-atk
        at-spi2-core
        atk
        cairo
        cups
        dbus
        expat
        fontconfig
        freetype
        gdk-pixbuf
        glib
        gsettings-desktop-schemas
        gtk3
        libdrm
        libgbm
        libglvnd
        libnotify
        libpulseaudio
        libsecret
        libX11
        libXScrnSaver
        libXcomposite
        libXcursor
        libXdamage
        libXext
        libXfixes
        libXi
        libXrandr
        libXrender
        libXtst
        libxcb
        libxkbcommon
        mesa
        nspr
        nss
        pango
        stdenv.cc.cc.lib
        systemd
        wayland
        xdg-utils
        zlib
      ];
    runScript = "${launcher}";
  };
  desktop = makeDesktopItem {
    name = "jlc-assistant";
    desktopName = "嘉立创下单助手";
    genericName = "PCB Ordering";
    exec = "jlc-assistant %U";
    icon = "jlc-assistant";
    categories = [ "Office" ];
    keywords = [ "嘉立创" "下单" "PCB" "JLC" ];
    startupNotify = true;
  };
in
symlinkJoin {
  name = "jlc-assistant-${version}";
  paths = [ runtime desktop files ];
  passthru = { inherit files; };
  meta = {
    description = "嘉立创下单助手官方 Linux 客户端";
    homepage = "https://download1.sz-jlc.com/download/jlc-order-assistant.html";
    license = lib.licenses.unfree;
    platforms = [ "x86_64-linux" ];
    mainProgram = "jlc-assistant";
  };
}
