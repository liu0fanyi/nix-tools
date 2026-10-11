# Produce opt-in user unit files only. This output never activates Home Manager or NixOS.
{ pkgs, homeManagerSource, tagAllSource, package, whisperPackage,
  toolArchive, toolImage, toolSha256, stateRoot ? "/home/liou/.local/share/tag-all/nuc-native",
  privateWorkspace ? "/home/liou/dufs-lan", readonlyWorkspace ? "/home/liou/dufs",
  media ? "/media/liou", models ? "/home/liou/.local/share/whisper.cpp/models",
  writingSsh ? "/home/liou/.config/dufs-plus/secrets/writing-git",
  applicationEntry ? false, frontendRoot ? null,
  applicationNames ? [ "devices" "transcriptions" "recorder-bean" "bevy-game" "bevy-sketch" "project-planner" "quick-note" ] }:
let
  lib = pkgs.lib;
  applications = map (name: { inherit name; root = "${stateRoot}/private/apps/${name}"; }) applicationNames;
  appMounts = map (app: "${privateWorkspace}/dist/${app.name}:${app.root}") applications;
  entryConfiguration = role: let private = role == "private"; port = if private then 5006 else 5008; in {
    lan = true;
    authorities = map (host: "${host}:${toString port}") [ "nuc.local" "nuc" "192.168.1.12" "localhost" "127.0.0.1" "[::1]" ];
    allowed_sources = (if private then [ "192.168.0.0/16" "10.0.0.0/8" "172.16.0.0/12" ] else [ "10.89.50.0/24" ]) ++ [ "127.0.0.0/8" "::1/128" ];
    device_profile = if private then "lan" else "disabled";
    peer_on_lan = private;
    external_socket = "${stateRoot}/sockets/${role}-web.sock";
    external_origins = if private then map (host: "https://${host}:5009") [ "nuc.local" "nas.wttliou.top" "home.wttliou.top" "localhost" "127.0.0.1" ] ++ [ "https://nas.wttliou.top" ]
      else [ "https://work.wttliou.top:5443" "https://workcdn.wttliou.top:5443" "https://work.wttliou.top:5008" "https://workcdn.wttliou.top:5008" "https://workcdn.wttliou.top" ];
    external_admin_groups = lib.optional private "admins";
  } // lib.optionalAttrs private {
    peer_socket = "${stateRoot}/sockets/private-peer.sock";
    peer_authorities = map (host: "${host}:5009") [ "nuc.local" "nas.wttliou.top" "home.wttliou.top" "localhost" "127.0.0.1" ] ++ [ "nas.wttliou.top" ];
    peer_devices = true;
    peer_write_delegation = true;
    terminal_socket = "/run/user/1000/ttyd/ttyd.sock";
    inherit applications;
  };
  templates = pkgs.formats.toml {};
  command = xs: lib.escapeShellArgs (map (x: lib.replaceStrings [ "%" "$" ] [ "%%" "$$" ] (toString x)) xs);
  instance = role: workspace: port:
    let
      root = "${stateRoot}/${role}";
      runtime = "${root}/tools";
      private = role == "private";
      evaluated = import (homeManagerSource + "/modules") {
        inherit pkgs;
        configuration = {
          imports = [ (tagAllSource + "/nix/home-manager-core.nix") ];
          home.username = "liou";
          home.homeDirectory = "/home/liou";
          home.stateVersion = "25.11";
          services.tag-all-core = {
            enable = true;
            inherit package workspace;
            port = if applicationEntry && private then 5006 else port;
            applicationEntry = lib.mkIf applicationEntry {
              enable = true;
              inherit frontendRoot;
              fileSocket = "${stateRoot}/sockets/${role}-files.sock";
              authenticationFile = "${root}/config/basic.entries";
              configurationFile = "${root}/config/application-entry.toml";
              readOnly = !private;
              listenAddress = "[::]";
            };
            stateDirectory = "${root}/state";
            nodeId = if private then "nuc" else "nuc-readonly";
            syncMode = if private then "configured" else "isolated";
            configurationFile = "${root}/config/node.toml";
            environmentFile = "${root}/config/service.env";
            workspaceMounts = lib.optionalAttrs private { inherit media; };
            toolRuntime = { image = toolImage; archive = toolArchive; archiveSha256 = toolSha256; stateDirectory = runtime; };
            processingContainers = builtins.listToAttrs (map (name: {
              inherit name; value = { image = toolImage; stateDirectory = "${root}/executors/${name}"; connection = "unix://${runtime}/runtime.sock"; };
            }) [ "pdf" "archive" "audioVideo" "epub" ]);
          };
          systemd.user.services.tag-all-core = {
            Service = {
              PrivateUsers = true;
              BindReadOnlyPaths = if private then [ models "${writingSsh}:${root}/git-home/.ssh" ] ++ lib.optionals applicationEntry appMounts else [ workspace ];
              ReadOnlyPaths = lib.optional (!private) workspace;
              Environment = lib.mkAfter (lib.optionals private [
                "DUFS_WHISPER_CLI=${whisperPackage}/bin/whisper-cli"
                "DUFS_WHISPER_MODEL=${models}/ggml-small-q5_1.bin"
                "HOME=${root}/git-home"
              ]);
            };
          };
        };
      };
      files = evaluated.config.xdg.configFile;
    in { inherit root runtime; core = files."systemd/user/tag-all-core.service".source;
         tools = files."systemd/user/tag-all-tools.service".source; };
  private = instance "private" privateWorkspace 18181;
  readonly = instance "readonly" readonlyWorkspace 18182;
  filesService = role: workspace: write: pkgs.writeText "nuc-${role}-files.service" ''
    [Unit]
    Description=NUC ${role} native DUFS
    PartOf=tag-native-nuc.target
    [Service]
    ExecStartPre=${command [ (pkgs.writeShellScript "nuc-${role}-socket-dir" ''
      set -eu
      directory=${lib.escapeShellArg (stateRoot + "/sockets")}
      test -d "$directory" && test ! -L "$directory"
      test "$(${pkgs.coreutils}/bin/stat -c %a "$directory")" = 700
      test "$(${pkgs.coreutils}/bin/stat -c %u "$directory")" = "$(${pkgs.coreutils}/bin/id -u)"
    '') ]}
    ExecStart=${command ([ "${pkgs.dufs}/bin/dufs" workspace "--bind" "${stateRoot}/sockets/${role}-files.sock" "--allow-symlink" "--allow-archive" ] ++ lib.optional write "--allow-all")}
    UMask=0077
    NoNewPrivileges=yes
    PrivateUsers=yes
    ${if write then "BindPaths=${media}:${workspace}/media" else "BindReadOnlyPaths=${workspace}"}
    ${lib.optionalString (!write) "ReadOnlyPaths=${workspace}"}
    Restart=on-failure
  '';
  bridgeConfig = pkgs.writeText "native-nuc-bridge.Caddyfile" ''
    { admin off
      auto_https off
    }
    :18191 {
      bind unix/${stateRoot}/sockets/private-api.sock
      reverse_proxy 127.0.0.1:18181
    }
    :18192 {
      bind unix/${stateRoot}/sockets/readonly-api.sock
      reverse_proxy 127.0.0.1:18182
    }
  '';
  bridge = pkgs.writeText "native-nuc-bridge.service" ''
    [Unit]
    Description=NUC private Unix API bridge (authenticated ingress only)
    PartOf=tag-native-nuc.target
    [Service]
    ExecStart=${command [ "${pkgs.caddy}/bin/caddy" "run" "--config" bridgeConfig "--adapter" "caddyfile" ]}
    UMask=0077
    NoNewPrivileges=yes
    Restart=on-failure
  '';
  names = lib.concatMap (role: map (kind: "tag-nuc-${role}-${kind}.service") [ "core" "tools" "files" ]) [ "private" "readonly" ] ++ lib.optional (!applicationEntry) "tag-nuc-bridge.service";
in assert !applicationEntry || frontendRoot != null;
assert lib.length applicationNames == lib.length (lib.unique applicationNames);
assert lib.all (name: builtins.elem name [ "devices" "transcriptions" "recorder-bean" "bevy-game" "bevy-sketch" "project-planner" "quick-note" ]) applicationNames;
pkgs.runCommand "tag-all-native-nuc-candidate" { inherit bridgeConfig; } ''
  mkdir -p $out/lib/systemd/user
  ${lib.concatMapStrings (role: let units = if role == "private" then private else readonly; in ''
    substitute ${units.core} $out/lib/systemd/user/tag-nuc-${role}-core.service \
      --replace-fail tag-all-tools.service tag-nuc-${role}-tools.service
    cp ${units.tools} $out/lib/systemd/user/tag-nuc-${role}-tools.service
    chmod 644 $out/lib/systemd/user/tag-nuc-${role}-tools.service
    cp ${filesService role (if role == "private" then privateWorkspace else readonlyWorkspace) (role == "private")} $out/lib/systemd/user/tag-nuc-${role}-files.service
    # Own target replaces standalone activation; no default target links are installed here.
    sed -i '/^WantedBy=/d' $out/lib/systemd/user/tag-nuc-${role}-core.service
    printf '\n[Unit]\nPartOf=tag-native-nuc.target\n${lib.optionalString applicationEntry "Requires=tag-nuc-${role}-files.service\nAfter=tag-nuc-${role}-files.service\n"}' >> $out/lib/systemd/user/tag-nuc-${role}-core.service
    printf '\n[Unit]\nPartOf=tag-native-nuc.target\n' >> $out/lib/systemd/user/tag-nuc-${role}-tools.service
  '') [ "private" "readonly" ]}
  ${lib.optionalString (!applicationEntry) "cp ${bridge} $out/lib/systemd/user/tag-nuc-bridge.service"}
  cat > $out/lib/systemd/user/tag-native-nuc.target <<TARGET
[Unit]
Description=NUC native application stack
Wants=${lib.concatStringsSep " " names}
Upholds=${lib.concatStringsSep " " names}
[Install]
WantedBy=default.target
TARGET
  ${if applicationEntry then lib.concatMapStrings (role: "cp ${templates.generate "nuc-${role}-entry.toml" (entryConfiguration role)} $out/${role}-entry.toml\n") [ "private" "readonly" ] else ''
    cp ${bridgeConfig} $out/bridge.Caddyfile
    ${pkgs.caddy}/bin/caddy adapt --config $out/bridge.Caddyfile --adapter caddyfile > $out/bridge.json
  ''}
''
