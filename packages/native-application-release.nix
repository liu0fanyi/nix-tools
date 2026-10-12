{ nixpkgsPath }:
let
  pkgs = import nixpkgsPath { system = "x86_64-linux"; };
in pkgs.runCommand "tag-native-release-manager" {} ''
  mkdir -p $out/bin $out/libexec
  cp ${../scripts/native_application_release.py} $out/libexec/native_application_release.py
  cp ${../scripts/application_entry_transaction.py} $out/libexec/application_entry_transaction.py
  cat > $out/bin/tag-native-release <<EOF
#!${pkgs.bash}/bin/bash
export PATH=/run/wrappers/bin:${pkgs.lib.makeBinPath [ pkgs.systemd pkgs.nix pkgs.podman pkgs.coreutils ]}:\''${PATH:-}
exec ${pkgs.python3}/bin/python3 $out/libexec/native_application_release.py "\$@"
EOF
  chmod 755 $out/bin/tag-native-release
''
