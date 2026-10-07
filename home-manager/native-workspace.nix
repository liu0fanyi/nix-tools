# Optional companion to tag-all's independently packaged core service.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.tag-native-workspace;
  gateway = import ../packages/native-workspace.nix {
    inherit pkgs;
    inherit (cfg) frontendRoot authFile fileSocket gatewayPort corePort;
  };
  unitArg = value: lib.replaceStrings [ "%" "$" ] [ "%%" "$$" ] (toString value);
  command = args: lib.escapeShellArgs (map unitArg args);
in {
  options.services.tag-native-workspace = {
    enable = lib.mkEnableOption "isolated authenticated native workspace gateway";
    frontendRoot = lib.mkOption { type = lib.types.path; description = "Previously built dufs-plus dist, immutable in production."; };
    workspace = lib.mkOption { type = lib.types.str; description = "Explicit existing workspace, matching native core."; };
    authFile = lib.mkOption { type = lib.types.str; description = "Runtime private Caddy basic_auth entries; never copied to the Nix store."; };
    gatewayPort = lib.mkOption { type = lib.types.port; default = 18006; };
    corePort = lib.mkOption { type = lib.types.port; default = 18081; };
    fileSocket = lib.mkOption { type = lib.types.str; default = "${config.xdg.dataHome}/tag-all/native-workspace/files.sock"; };
    workspaceBindPaths = lib.mkOption { type = lib.types.listOf lib.types.str; default = [];
      description = "Validated mappings from the authoritative native stack module."; };
    workspaceMountDirectories = lib.mkOption { type = lib.types.listOf lib.types.str; default = []; };
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      { assertion = builtins.stringLength cfg.fileSocket < 108;
        message = "Native DUFS Unix socket path must fit the Linux 107-byte limit."; }
      { assertion = cfg.gatewayPort != cfg.corePort;
        message = "Native gateway and core require distinct loopback ports."; }
      { assertion = lib.hasPrefix "/" cfg.workspace && lib.hasPrefix "/" cfg.authFile;
        message = "Native workspace/auth file must be explicit absolute paths."; }
      { assertion = !lib.hasPrefix (cfg.workspace + "/") cfg.authFile;
        message = "Native gateway credentials must remain outside the served workspace."; }
      { assertion = lib.hasPrefix "/" cfg.fileSocket && !lib.hasPrefix (cfg.workspace + "/") cfg.fileSocket;
        message = "Native DUFS socket must be absolute and outside the served workspace."; }
    ];
    systemd.user.services.tag-native-files = {
      Unit = {
        Description = "Native workspace file service (private Unix socket)";
        ConditionPathIsDirectory = map (path: lib.replaceStrings [ "%" ] [ "%%" ] path) cfg.workspaceMountDirectories;
      };
      Service = {
        ExecStartPre = command [ (pkgs.writeShellScript "native-file-socket-dir" ''
          set -eu
          umask 077
          directory=${lib.escapeShellArg (builtins.dirOf cfg.fileSocket)}
          test ! -L "$directory"
          ${pkgs.coreutils}/bin/mkdir -p -- "$directory"
          test "$(${pkgs.coreutils}/bin/stat -c %u -- "$directory")" = "$(${pkgs.coreutils}/bin/id -u)"
          test "$(${pkgs.coreutils}/bin/stat -c %a -- "$directory")" = 700
          socket=${lib.escapeShellArg cfg.fileSocket}
          test ! -L "$socket"
          if test -e "$socket"; then test -S "$socket"; fi
          workspace=$(${pkgs.coreutils}/bin/realpath -e -- ${lib.escapeShellArg cfg.workspace})
          actual=$(${pkgs.coreutils}/bin/realpath -m -- "$socket")
          case "$actual" in "$workspace"|"$workspace"/*) exit 2 ;; esac
        '') ];
        ExecStart = command [ "${gateway.dufs}/bin/dufs" cfg.workspace "--bind" cfg.fileSocket
          "--allow-upload" "--allow-delete" "--allow-search" "--allow-archive" ];
        Restart = "on-failure";
        UMask = "0077";
        NoNewPrivileges = true;
        PrivateTmp = true;
        PrivateUsers = lib.mkIf (cfg.workspaceBindPaths != []) true;
        BindPaths = cfg.workspaceBindPaths;
      };
    };
    systemd.user.services.tag-native-workspace = {
      Unit = {
        Description = "Native workspace authenticated gateway";
        Requires = [ "tag-all-core.service" "tag-native-files.service" ];
        After = [ "tag-all-core.service" "tag-native-files.service" ];
      };
      Service = {
        ExecStartPre = command [ (pkgs.writeShellScript "native-workspace-auth-check" ''
          set -eu
          file=${lib.escapeShellArg cfg.authFile}
          test -f "$file" && test ! -L "$file"
          test "$(${pkgs.coreutils}/bin/stat -c %u -- "$file")" = "$(${pkgs.coreutils}/bin/id -u)"
          test "$(${pkgs.coreutils}/bin/stat -c %a -- "$file")" = 600
          workspace=$(${pkgs.coreutils}/bin/realpath -e -- ${lib.escapeShellArg cfg.workspace})
          actual=$(${pkgs.coreutils}/bin/realpath -e -- "$file")
          case "$actual" in "$workspace"|"$workspace"/*) exit 2 ;; esac
        '') ];
        ExecStart = command [ "${gateway.caddy}/bin/caddy" "run" "--config" gateway.config "--adapter" "caddyfile" ];
        Restart = "on-failure";
        UMask = "0077";
        NoNewPrivileges = true;
        PrivateTmp = true;
        Environment = map (value: lib.escapeShellArg (lib.replaceStrings [ "%" ] [ "%%" ] value)) [
          "XDG_CONFIG_HOME=${config.xdg.dataHome}/tag-all/native-workspace/config"
          "XDG_DATA_HOME=${config.xdg.dataHome}/tag-all/native-workspace/data"
        ];
      };
      Install.WantedBy = [ "default.target" ];
    };
  };
}
