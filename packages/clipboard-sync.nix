{
  lib,
  rustPlatform,
  pkg-config,
  libxcb,
  libxkbcommon,
  wayland,
  dbus,
  glib,
  pango,
  cairo,
  gdk-pixbuf,
  gtk3,
  src,
}:

rustPlatform.buildRustPackage {
  pname = "clipboard-sync";
  version = "0.2.0";
  inherit src;

  cargoHash = "sha256-MK5hCh9/ZAfrA/4SRr5WZa6fqA7i+E8WyA3RDx5Hcak=";

  nativeBuildInputs = [ pkg-config ];
  buildInputs = [
    libxcb
    libxkbcommon
    wayland
    dbus
    glib
    pango
    cairo
    gdk-pixbuf
    gtk3
  ];

  doCheck = true;

  meta = {
    description = "Cross-device encrypted clipboard and file sync daemon";
    homepage = "https://github.com/liu0fanyi/clipboard-sync";
    license = lib.licenses.mit;
    mainProgram = "clipboard-sync";
    platforms = lib.platforms.linux;
  };
}
