{ pkgs }:

# v0.3.1 only reads /proxies; recent mihomo keeps subscription nodes under
# /providers/proxies. Pin the upstream 0.3.2 development fix until a release.
pkgs.clashtui.overrideAttrs (final: previous: {
  version = "0.3.2";
  src = pkgs.fetchFromGitHub {
    owner = "JohanChane";
    repo = "clashtui";
    rev = "8eb76a1253161434ae8d5c0ad68821cb84a7cd12";
    hash = "sha256-lIVvU3DZ58K7X+qOTyFXohU+Sj2aBTJOs8wLgCdQ/98=";
  };
  cargoDeps = pkgs.rustPlatform.fetchCargoVendor {
    inherit (final) src;
    name = "clashtui-${final.version}";
    hash = "sha256-hak8dEfQXJpGW+uhspeBilVNqfjv6skGLljI586kKA4=";
  };
})
