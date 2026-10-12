# Keep the already migrated PC application units present in ordinary HM generations.
# Program/frontend upgrades remain owned by the hash-bound native release manager.
{ config, lib, pkgs, ... }:
let
  sourcePath = "/nix/store/ks216rpf09kfckjx4g06s7xhzpqxvc5m-home-manager-generation";
  source = builtins.appendContext sourcePath { "${sourcePath}" = { path = true; }; };
  unitSource = source + "/home-files/.config/systemd/user";
  names = [ "tag-all-core.service" "tag-all-tools.service" "tag-native-files.service" "tag-native-workspace.service" "tag-native-stack.target" ];
  root = "/home/liou/.local/share/tag-all/pc-native";
in {
  assertions = [ {
    assertion = config.networking.hostName == "liu-bigpc" && config.users.users.liou.uid == 1000;
    message = "Existing native application registration is limited to liu-bigpc/liou uid 1000.";
  } ];
  home-manager.users.liou = { lib, ... }: {
    xdg.configFile = builtins.listToAttrs (map (name: {
      name = "systemd/user/" + name;
      value.source = unitSource + "/" + name;
    }) names) // {
      "systemd/user/default.target.wants/tag-native-stack.target".source = unitSource + "/tag-native-stack.target";
    };
    # Files are stable immutable templates. Do not duplicate the native service
    # definitions or replace the release manager's version/boot guard drop-ins.
    home.activation.restoreExistingNativeApplication = lib.hm.dag.entryAfter [ "linkGeneration" "reloadSystemd" ] ''
      if [ -f ${root}/ready ] && [ ! -e ${root}/container-mode ]; then
        ${pkgs.systemd}/bin/systemctl --user daemon-reload
        ${pkgs.systemd}/bin/systemctl --user start tag-native-stack.target
      fi
    '';
  };
}
