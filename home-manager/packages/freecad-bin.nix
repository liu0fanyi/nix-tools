{
  lib,
  fetchurl,
  appimageTools,
  makeDesktopItem,
}:
let
  pname = "freecad";
  version = "1.1.3";
  src = fetchurl {
    url = "https://github.com/FreeCAD/FreeCAD/releases/download/${version}/FreeCAD_${version}-Linux-x86_64-py311.AppImage";
    sha256 = "3a853eb69ee595f779f2255dbf80a765926981d8ff68903cefee4dfb03a8f5ef";
  };
  contents = appimageTools.extract { inherit pname version src; };
  desktop = makeDesktopItem {
    name = "freecad";
    desktopName = "FreeCAD";
    exec = "freecad %F";
    icon = "freecad";
    comment = "Parametric 3D modeler";
    categories = [
      "Graphics"
      "Engineering"
    ];
    mimeTypes = [ "application/x-extension-fcstd" ];
  };
in
appimageTools.wrapType2 {
  inherit pname version src;
  extraInstallCommands = ''
    install -Dm644 ${contents}/org.freecad.FreeCAD.svg "$out/share/icons/hicolor/scalable/apps/freecad.svg"
    install -Dm644 ${desktop}/share/applications/freecad.desktop "$out/share/applications/freecad.desktop"
  '';
  meta = {
    description = "FreeCAD official Linux binary for parametric 3D modeling";
    homepage = "https://www.freecad.org/";
    license = lib.licenses.lgpl2Plus;
    platforms = [ "x86_64-linux" ];
    mainProgram = "freecad";
  };
}
