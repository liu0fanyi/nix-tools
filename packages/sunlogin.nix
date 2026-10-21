{ pkgs, legacyGtk, scaleFactor ? 1.0 }:
let
  version = "15.2.0.63062";
  appDir = "/opt/apps/com.oray.sunlogin.client";
  files = pkgs.stdenvNoCC.mkDerivation {
    pname = "sunlogin-files";
    inherit version;
    src = pkgs.fetchurl {
      url = "https://dl.oray.com/sunlogin/linux/com.oray.sunlogin.client-${version}-amd64.deb";
      hash = "sha256-8MsClXlaDlwy3c/VaapmjCodZoULcKOSnBhAz9taY0c=";
    };
    nativeBuildInputs = [ pkgs.dpkg ];
    unpackPhase = ''
      dpkg-deb -x "$src" unpacked
    '';
    dontConfigure = true;
    dontBuild = true;
    installPhase = ''
      mkdir -p "$out"
      cp -a unpacked/opt "$out/"
    '';
  };
  mkRuntime = name: command: arguments: pkgs.buildFHSEnv {
    pname = name;
    inherit version;
    targetPkgs = p: with p; [
      alsa-lib atk cairo dbus expat fontconfig freetype legacyGtk.gnome2.GConf gdk-pixbuf
      glib gtk3 libglvnd libpulseaudio libxcrypt-legacy libuuid
      libX11 libXScrnSaver libXcomposite libXcursor libXdamage libXext
      libXfixes libXi libXinerama libXrandr libXrender libXtst libxcb
      nspr nss pango stdenv.cc.cc.lib systemd zlib
    ];
    # Keep the vendor's absolute resource paths inside the FHS environment.
    # Account/configuration state stays writable outside the immutable store.
    extraPreBwrapCmds = ''
      ignored+=(/opt)
    '';
    extraBwrapArgs = [
      "--tmpfs /opt"
      "--ro-bind ${files}${appDir} ${appDir}"
      "--bind /var/lib/sunlogin/orayconfig.conf /etc/orayconfig.conf"
    ];
    runScript = pkgs.writeShellScript "${name}-launcher" ''
      export GDK_BACKEND=x11
      cd ${appDir}/files/bin
      exec ${appDir}/files/bin/${command} ${arguments} "$@"
    '';
  };
  client = mkRuntime "sunloginclient" "sunloginclient"
    "--force-device-scale-factor=${toString scaleFactor}";
  daemon = mkRuntime "sunlogin-daemon" "oray_rundaemon" "";
  desktop = pkgs.makeDesktopItem {
    name = "sunloginclient";
    desktopName = "向日葵远程控制";
    exec = "sunloginclient";
    icon = "${files}${appDir}/entries/icons/sunlogin_client.png";
    categories = [ "Network" "RemoteAccess" ];
  };
in
pkgs.symlinkJoin {
  name = "sunlogin-${version}";
  paths = [ client daemon desktop ];
  meta = {
    description = "Oray Sunlogin personal remote desktop client";
    homepage = "https://sunlogin.oray.com/download/linux";
    license = pkgs.lib.licenses.unfree;
    platforms = [ "x86_64-linux" ];
    mainProgram = "sunloginclient";
  };
}
