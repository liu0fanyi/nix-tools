# Trusted gateway configuration; upstreams are fixed loopback core and private Unix DUFS socket, never URL input.
{ pkgs, frontendRoot, authFile, fileSocket, gatewayPort ? 18006, corePort ? 18081, peer ? null, peerAdministration ? false }:
let
  config = pkgs.writeText "tag-native-workspace.Caddyfile" ''
    {
      admin off
      ${if peer != null && (peer.tlsMode or "files") == "internal" then ''
        auto_https disable_redirects
        skip_install_trust
        storage file_system "${peer.storageDirectory}"
      '' else "auto_https off"}
    }
    http://127.0.0.1:${toString gatewayPort} {
      bind 127.0.0.1
      route {
        basic_auth {
          import "${authFile}"
        }
        handle /.dufs-plus/capabilities.json {
          header Content-Type application/json
          header Cache-Control no-store
          respond `{"dufs_write":true,"tag_write":true,"bevy_sketch":false,"game_tools":false,"terminal":false}` 200
        }
        ${if peerAdministration then ''
          @peer_admin path /tag-api/peer-manager /tag-api/v1/peers/web/* /tag-api/v1/peers/candidates /tag-api/v1/peers/requests /tag-api/v1/peers/requests/* /tag-api/v1/peers/approvals /tag-api/v1/peers/approvals/*
          handle @peer_admin {
            uri strip_prefix /tag-api
            reverse_proxy 127.0.0.1:${toString corePort} {
              header_up X-Tag-Admin-Token {env.TAG_PEER_ADMIN_TOKEN}
              header_up -X-Dufs-Device-Api
              header_up -X-Dufs-Device-Provisioning
            }
          }
        '' else ""}
        handle_path /tag-api/* {
          reverse_proxy 127.0.0.1:${toString corePort} {
            header_up -X-Dufs-Device-Api
            header_up -X-Dufs-Device-Provisioning
          }
        }
        @private_apps path /device-api /device-api/* /devices /devices/* /transcriptions /transcriptions/* /recorder-bean /recorder-bean/* /dist/devices /dist/devices/* /dist/transcriptions /dist/transcriptions/* /dist/recorder-bean /dist/recorder-bean/*
        handle @private_apps {
          respond "Not available in core workspace" 404
        }
        @listing expression {query}=='json'||{query}.startsWith('json&')
        handle @listing {
          reverse_proxy unix/${fileSocket}
        }
        root * "${frontendRoot}"
        @entry {
          method GET HEAD
          path / /index.html
        }
        handle @entry {
          header Cache-Control "no-cache, must-revalidate"
          rewrite * /index.html
          file_server
        }
        handle_path /dist/* {
          file_server
        }
        @asset {
          method GET HEAD
          file
        }
        handle @asset {
          file_server
        }
        handle {
          reverse_proxy unix/${fileSocket}
        }
      }
    }
    ${if peer == null then "" else import ./native-peer-site.nix { inherit peer corePort; }}
  '';
in {
  inherit config;
  caddy = pkgs.caddy;
  dufs = pkgs.dufs;
}
