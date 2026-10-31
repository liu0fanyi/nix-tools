{ lib, stdenvNoCC, stdenv, fetchurl, autoPatchelfHook, makeWrapper,
  libxcb, libxkbcommon, wayland, libglvnd, vulkan-loader }:

stdenvNoCC.mkDerivation rec {
  pname = "disktree";
  version = "0.11.0";
  src = fetchurl {
    url = "https://github.com/tobi/disktree/releases/download/v${version}/disktree-${version}-x86_64-linux.tar.gz";
    # Verified against the official GitHub release asset.digest.
    sha256 = "7e75afa2283c8b4f9290d52eadbfc00d9f14c13aed2d224ccdf0f7826fcc05b2";
  };
  nativeBuildInputs = [ autoPatchelfHook makeWrapper ];
  buildInputs = [ libxcb libxkbcommon stdenv.cc.cc.lib ];
  dontConfigure = true;
  dontBuild = true;
  dontStrip = true;
  installPhase = ''
    runHook preInstall
    install -Dm755 disktree "$out/bin/disktree"
    install -Dm644 disktree.svg "$out/share/icons/hicolor/scalable/apps/disktree.svg"
    install -Dm644 LICENSE "$out/share/licenses/disktree/LICENSE"
    install -Dm644 disktree.desktop.in "$out/share/applications/disktree.desktop"
    substituteInPlace "$out/share/applications/disktree.desktop" \
      --replace-fail '@BINDIR@' "$out/bin" \
      --replace-fail '@VERSION@' '${version}'
    runHook postInstall
  '';
  postFixup = ''
    wrapProgram "$out/bin/disktree" --prefix LD_LIBRARY_PATH : \
      "${lib.makeLibraryPath [ wayland libglvnd vulkan-loader ]}"
  '';
  doInstallCheck = true;
  installCheckPhase = ''
    test "$(cat VERSION)" = '${version}'
    "$out/bin/disktree" --help > /dev/null
  '';
  meta = {
    description = "Graphical disk usage treemap";
    homepage = "https://github.com/tobi/disktree";
    license = lib.licenses.mit;
    platforms = [ "x86_64-linux" ];
    mainProgram = "disktree";
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
  };
}
