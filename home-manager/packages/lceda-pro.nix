{
  lib,
  stdenvNoCC,
  fetchurl,
  libarchive,
  buildFHSEnv,
  makeDesktopItem,
  symlinkJoin,
  writeShellScript,
  scaleFactor ? null,
}:
let
  version = "3.2.203";
  files = stdenvNoCC.mkDerivation {
    pname = "lceda-pro-files";
    inherit version;
    src = fetchurl {
      url = "https://image.lceda.cn/files/lceda-pro-linux-x64-${version}.zip";
      sha256 = "c89f17a95d9828f39ce743afb6b322e43c2b897ddae5d47479ac6c1071d719ed";
    };
    nativeBuildInputs = [ libarchive ];
    env.LC_ALL = "C.UTF-8";
    # Upstream ZIP has inconsistent local/central Unicode filenames for its
    # Chinese EULA. libarchive handles this without suppressing extraction errors.
    unpackPhase = ''
      runHook preUnpack
      bsdtar -xf "$src"
      runHook postUnpack
    '';
    dontConfigure = true;
    dontBuild = true;
    # Preserve upstream Electron/native modules; run them in an FHS environment.
    dontFixup = true;
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/opt"
      cp -r lceda-pro "$out/opt/lceda-pro"
      chmod +x "$out/opt/lceda-pro/lceda-pro"
      for size in 16 24 32 48 64 96 128 256 512; do
        install -Dm644 "lceda-pro/icon/icon_''${size}x''${size}.png" \
          "$out/share/icons/hicolor/''${size}x''${size}/apps/lceda-pro.png"
      done
      runHook postInstall
    '';
  };
  launcher = writeShellScript "lceda-pro-launcher" ''
    exec "${files}/opt/lceda-pro/lceda-pro" \
      ${lib.optionalString (scaleFactor != null) "--force-device-scale-factor=${toString scaleFactor}"} \
      "$@"
  '';
  runtime = buildFHSEnv {
    pname = "lceda-pro";
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
        nssmdns
        pango
        stdenv.cc.cc.lib
        systemd
        wayland
        xdg-utils
        zlib
      ];
    # Do not run the upstream root installer or disable Electron's sandbox.
    runScript = "${launcher}";
  };
  desktop = makeDesktopItem {
    name = "lceda-pro";
    desktopName = "LCEDA Pro";
    genericName = "PCB Design";
    comment = "嘉立创 EDA 专业版";
    exec = "lceda-pro %U";
    icon = "lceda-pro";
    categories = [
      "Development"
      "Electronics"
    ];
    keywords = [
      "PCB"
      "EDA"
      "嘉立创"
      "立创"
    ];
    startupWMClass = "JLCEDA Pro";
    startupNotify = true;
  };
in
symlinkJoin {
  name = "lceda-pro-${version}";
  paths = [
    runtime
    desktop
    files
  ];
  passthru = { inherit files; };
  meta = {
    description = "嘉立创 EDA 专业版 (official Linux desktop client)";
    homepage = "https://lceda.cn/page/download";
    license = lib.licenses.unfree;
    platforms = [ "x86_64-linux" ];
    mainProgram = "lceda-pro";
  };
}
