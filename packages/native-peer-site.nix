# Only trusted install parameters; no browser-selected upstream or administrator secret.
{ peer, corePort }:
''
  https://${peer.serverName}:${toString peer.port} {
    bind ${peer.listenAddress}
    ${if (peer.tlsMode or "files") == "internal" then "tls internal" else ''tls "${peer.certificateFile}" "${peer.privateKeyFile}"''}
    route {
      @peer {
        remote_ip ${builtins.concatStringsSep " " peer.allowedNetworks}
        path /tag-api/v1/peers/identity /tag-api/v1/peers/challenge /tag-api/v1/peers/requests/incoming /tag-api/v1/peers/requests/accepted /tag-api/v1/sync/* /tag-api/v1/locations /tag-api/v1/locations/* /tag-api/v1/proxy/* /tag-api/listing /tag-api/items /tag-api/v1/inspect
      }
      handle @peer {
        uri strip_prefix /tag-api
        reverse_proxy 127.0.0.1:${toString corePort} {
          header_up -X-Tag-Admin-Token
          header_up -Authorization
          header_up -X-Dufs-Device-Api
          header_up -X-Dufs-Device-Provisioning
        }
      }
      handle {
        respond "Not found" 404
      }
    }
  }
''
