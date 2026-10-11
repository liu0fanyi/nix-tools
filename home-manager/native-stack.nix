# Factory: consumer supplies the product's authoritative module source.
{ tagAllSource }:
{ config, lib, ... }:
let
  cfg = config.services.tag-native-stack;
  mappings = import (tagAllSource + "/nix/workspace-mounts.nix") { inherit lib; inherit (cfg) workspace; mounts = cfg.workspaceMounts; };
in {
  imports = [ (tagAllSource + "/nix/home-manager-core.nix") ./native-workspace.nix ];
  options.services.tag-native-stack = {
    enable = lib.mkEnableOption "authenticated native core and file workspace trial";
    applicationEntry = lib.mkEnableOption "application-owned PC HTTP entry (candidate only)";
    entryConfigurationFile = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    peerSocket = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    package = lib.mkOption { type = lib.types.package; };
    pdfContainer = import (tagAllSource + "/nix/pdf-container-option.nix") { inherit lib; };
    processingContainers = import (tagAllSource + "/nix/processing-containers-option.nix") { inherit lib; };
    toolRuntime = import (tagAllSource + "/nix/tool-runtime-option.nix") { inherit lib; };
    frontendRoot = lib.mkOption { type = lib.types.path; };
    workspace = lib.mkOption { type = lib.types.str; };
    authFile = lib.mkOption { type = lib.types.str; };
    localAuthentication = lib.mkOption { type = lib.types.enum [ "basic" "loopback" ]; default = "basic"; };
    gatewayPort = lib.mkOption { type = lib.types.port; default = 18006; };
    corePort = lib.mkOption { type = lib.types.port; default = 18081; };
    nodeId = lib.mkOption { type = lib.types.str; default = "pc-core-trial"; };
    configurationFile = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    syncMode = lib.mkOption { type = lib.types.enum [ "isolated" "configured" ]; default = "isolated"; };
    environmentFile = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    workspaceMounts = lib.mkOption { type = lib.types.attrsOf lib.types.str; default = {}; };
  };
  options.services.tag-native-stack.peer = lib.mkOption {
    type = lib.types.attrs; default = {};
    description = "Explicit peer TLS options forwarded to the private gateway; defaults disabled.";
  };
  config = lib.mkIf cfg.enable {
    services.tag-all-core = {
      enable = true;
      inherit (cfg) package pdfContainer processingContainers toolRuntime workspace nodeId configurationFile syncMode environmentFile workspaceMounts;
      port = if cfg.applicationEntry then cfg.gatewayPort else cfg.corePort;
      applicationEntry = lib.mkIf cfg.applicationEntry {
        enable = true;
        frontendRoot = cfg.frontendRoot;
        fileSocket = config.services.tag-native-workspace.fileSocket;
        configurationFile = cfg.entryConfigurationFile;
        authenticationFile = if cfg.localAuthentication == "basic" then cfg.authFile else null;
      };
    };
    services.tag-native-workspace = {
      enable = true;
      inherit (cfg) frontendRoot workspace authFile corePort gatewayPort localAuthentication applicationEntry peerSocket;
      peer = cfg.peer;
      administratorEnvironmentFile = cfg.environmentFile;
      workspaceBindPaths = mappings.paths;
      workspaceMountDirectories = mappings.directories;
    };
    systemd.user.targets.tag-native-stack = {
      Unit = {
        Description = "Native private workspace services";
        Wants = [ "tag-all-core.service" "tag-native-files.service" "tag-native-workspace.service" ] ++ lib.optional (cfg.toolRuntime != null) "tag-all-tools.service";
        Upholds = [ "tag-all-core.service" "tag-native-files.service" "tag-native-workspace.service" ] ++ lib.optional (cfg.toolRuntime != null) "tag-all-tools.service";
      };
      Install.WantedBy = [ "default.target" ];
    };
    systemd.user.services.tag-all-core = {
      Unit = {
        PartOf = [ "tag-native-stack.target" ];
        Requires = lib.mkIf cfg.applicationEntry [ "tag-native-files.service" ];
        After = lib.mkIf cfg.applicationEntry [ "tag-native-files.service" ];
      };
      Install.WantedBy = lib.mkForce [];
    };
    systemd.user.services.tag-all-tools = lib.mkIf (cfg.toolRuntime != null) { Unit.PartOf = [ "tag-native-stack.target" ]; };
    systemd.user.services.tag-native-files.Unit.PartOf = [ "tag-native-stack.target" ];
    systemd.user.services.tag-native-workspace = {
      Unit = {
        PartOf = [ "tag-native-stack.target" ];
        # Keep the authenticated gateway available while BindsTo restarts core
        # after a tools outage. Requires would stop it during the queued stop
        # transaction, where target Upholds cannot enqueue a conflicting start.
        Requires = lib.mkIf (cfg.toolRuntime != null) (lib.mkForce []);
        Wants = lib.mkIf (cfg.toolRuntime != null) [ "tag-all-core.service" "tag-native-files.service" ];
      };
      Install.WantedBy = lib.mkForce [];
    };
    assertions = [
      { assertion = !cfg.applicationEntry || cfg.entryConfigurationFile != null;
        message = "Application entry requires an explicit private runtime configuration."; }
      { assertion = !(config.services.tag-native-workspace.peer.enable) || (cfg.syncMode == "configured" && cfg.environmentFile != null);
        message = "Native peer entry requires explicit configured core mode and private administrator environment."; }
      { assertion = config.services.tag-all-core.workspace == config.services.tag-native-workspace.workspace;
        message = "Native core and files must serve the same workspace."; }
      { assertion = cfg.applicationEntry || config.services.tag-all-core.port == config.services.tag-native-workspace.corePort;
        message = "Native gateway must target the configured core port."; }
    ];
  };
}
