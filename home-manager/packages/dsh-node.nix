{ lib, stdenvNoCC, fetchurl, autoPatchelfHook, stdenv }:

# dsh introspects Node machine code; nixpkgs hardening changes the getter
# instruction sequence that node-addon-require-builtin expects (#565667).
# Keep this official runtime private to dsh instead of replacing system Node.
stdenvNoCC.mkDerivation rec {
  pname = "dsh-node";
  version = "24.20.0";
  src = fetchurl {
    url = "https://nodejs.org/dist/v${version}/node-v${version}-linux-x64.tar.xz";
    sha256 = "2f2c0da162318f0de47665410c7c8c2ed3d36c8f3105de4bbc61176c70a7cbf2";
  };
  nativeBuildInputs = [ autoPatchelfHook ];
  buildInputs = [ stdenv.cc.cc.lib ];
  dontConfigure = true;
  dontBuild = true;
  dontStrip = true;
  installPhase = ''
    runHook preInstall
    mkdir -p "$out/bin" "$out/share/licenses/dsh-node"
    cp bin/node "$out/bin/node"
    cp LICENSE "$out/share/licenses/dsh-node/LICENSE"
    runHook postInstall
  '';
  doInstallCheck = true;
  installCheckPhase = ''
    "$out/bin/node" --version
    "$out/bin/node" --expose-internals -e 'require("internal/modules/esm/loader")'
  '';
  meta = {
    description = "Official Node.js runtime dedicated to DeepSeek Harness";
    homepage = "https://nodejs.org/";
    license = lib.licenses.mit;
    platforms = [ "x86_64-linux" ];
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
  };
}
