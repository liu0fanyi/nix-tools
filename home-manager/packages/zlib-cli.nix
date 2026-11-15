{ lib, stdenvNoCC, fetchurl }:

stdenvNoCC.mkDerivation rec {
  pname = "zlib-cli";
  version = "0.0.14";
  src = fetchurl {
    url = "https://github.com/heartleo/zlib/releases/download/v${version}/zlib_${version}_linux_x86_64.tar.gz";
    # Verified against the upstream GitHub release asset.digest.
    sha256 = "d9a066b7f97edc4f6046d342183cd82d095ba311e880fbf3bc1dd0b341362651";
  };
  sourceRoot = ".";
  dontConfigure = true;
  dontBuild = true;
  dontStrip = true;
  installPhase = ''
    runHook preInstall
    install -Dm755 zlib "$out/bin/zlib"
    install -Dm644 LICENSE "$out/share/licenses/zlib-cli/LICENSE"
    runHook postInstall
  '';
  doInstallCheck = true;
  installCheckPhase = ''
    runHook preInstallCheck
    "$out/bin/zlib" version | grep -F '${version}'
    "$out/bin/zlib" search --help > /dev/null
    "$out/bin/zlib" download --help > /dev/null
    runHook postInstallCheck
  '';
  meta = {
    description = "Command-line client for Z-Library";
    homepage = "https://github.com/heartleo/zlib";
    license = lib.licenses.mit;
    platforms = [ "x86_64-linux" ];
    mainProgram = "zlib";
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
  };
}
