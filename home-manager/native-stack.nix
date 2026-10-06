# Factory: consumer supplies the product's authoritative module source.
{ tagAllSource }:
{ config, lib, ... }:
let cfg = config.services.tag-native-stack;
in {
  imports = [ (tagAllSource + "/nix/home-manager-core.nix") ./native-workspace.nix ];
  options.services.tag-native-stack = {
    enable = lib.mkEnableOption "authenticated native core and file workspace trial";
    package = lib.mkOption { type = lib.types.package; };
    frontendRoot = lib.mkOption { type = lib.types.path; };
    workspace = lib.mkOption { type = lib.types.str; };
    authFile = lib.mkOption { type = lib.types.str; };
    gatewayPort = lib.mkOption { type = lib.types.port; default = 18006; };
    corePort = lib.mkOption { type = lib.types.port; default = 18081; };
    nodeId = lib.mkOption { type = lib.types.str; default = "pc-core-trial"; };
    configurationFile = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    syncMode = lib.mkOption { type = lib.types.enum [ "isolated" "configured" ]; default = "isolated"; };
    environmentFile = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
  };
  config = lib.mkIf cfg.enable {
    services.tag-all-core = {
      enable = true;
      inherit (cfg) package workspace nodeId configurationFile syncMode environmentFile;
      port = cfg.corePort;
    };
    services.tag-native-workspace = {
      enable = true;
      inherit (cfg) frontendRoot workspace authFile corePort gatewayPort;
    };
    assertions = [
      { assertion = config.services.tag-all-core.workspace == config.services.tag-native-workspace.workspace;
        message = "Native core and files must serve the same workspace."; }
      { assertion = config.services.tag-all-core.port == config.services.tag-native-workspace.corePort;
        message = "Native gateway must target the configured core port."; }
    ];
  };
}
