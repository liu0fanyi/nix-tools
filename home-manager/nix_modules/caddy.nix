{
  pkgs,
  config,
  lib,
  ...
}:

let
  cfg = config.features.caddy;
in
{
  options.features.caddy = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable Caddy web server";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ pkgs.caddy ];

    xdg.configFile."caddy/Caddyfile".text = ''
      {
        # Global trusted proxies for LAN, loopback, and EdgeOne CDN
        servers {
          trusted_proxies static private_ranges 2408:873d::/32 2408:874c::/32
        }

        # 关键修改 1: 禁用 HTTP 到 HTTPS 的自动重定向
        # 这样 Caddy 就不会去尝试绑定 80 端口了，避免 permission denied
        auto_https disable_redirects

        # 关键修改 2: 禁止自动安装信任证书
        # 避免日志里出现 sudo 报错
        skip_install_trust
      }

      https://work.wttliou.top:5008, https://workcdn.wttliou.top:5008 {
        tls internal

        # Map base URL based on host to handle accelerated vs direct access
        map {host} {base_url} {
            workcdn.wttliou.top  workcdn.wttliou.top
            default              {host}
        }

        # Redirect origin domain to CDN domain (stripping port for acceleration)
        @origin_host host work.wttliou.top
        redir @origin_host https://workcdn.wttliou.top{uri} permanent

        # Proxy to the read-only dufs container (no authentication)
        reverse_proxy 127.0.0.1:5005

        log {
          output file ${config.home.homeDirectory}/.local/share/caddy/access.log
        }
      }

      http://:5006 {
        # Access Control: Only allow private IP ranges (LAN)
        @lan {
          remote_ip 192.168.0.0/16 172.16.0.0/12 10.0.0.0/8 127.0.0.1/8 ::1
        }
        handle @lan {
          @not_options {
            not method OPTIONS
          }
          basic_auth @not_options {
            admin $2a$14$jQ8iy6ybRwnQVDxCFAxEO.VoyPMR7GZVbYgyjcimvUMU1lePXP7NK
          }
          
          root * /home/liou/dufs-lan/dist
          
          # 1. API Priority: Requests with ?json MUST go to Dufs
          @api {
            expression {query}.contains('json')
          }
          handle @api {
            reverse_proxy 127.0.0.1:5007
          }

          # 2. UI Entry: Exact root path without ?json
          @ui_root {
            method GET HEAD
            path /
            not expression {query}.contains('json')
          }
          handle @ui_root {
            rewrite * /index.html
            file_server
          }

          # 3. Static Assets: Files that exist in dist/
          @static {
            method GET HEAD
            file
          }
          handle @static {
            file_server
          }
          
          # 4. Tag-Server Proxy
          handle_path /tag-api/* {
            reverse_proxy 127.0.0.1:8081
          }

          # 5. Fallback: Everything else (nested API, file downloads) to Dufs
          handle {
            reverse_proxy 127.0.0.1:5007
          }
        }
        # Reject everyone else (Public Internet / IPv6 Global)
        handle {
          abort
        }
      }

      https://nas.wttliou.top:5009, https://home.wttliou.top:5009, https://localhost:5009, https://127.0.0.1:5009 {
        tls internal

        # Map base URL based on host to handle accelerated vs direct access
        map {host} {base_url} {
            nas.wttliou.top  nas.wttliou.top
            default          {host}
        }

        # Redirect origin domain to CDN domain (stripping port for acceleration)
        @origin_host host home.wttliou.top
        redir @origin_host https://nas.wttliou.top{uri} permanent

        # Authelia portal and verify endpoint
        handle /authelia/* {
          reverse_proxy 127.0.0.1:9091 {
            header_up X-Real-IP {client_ip}
            header_up X-Forwarded-Proto {scheme}
            header_up X-Forwarded-Host {host}
            header_up X-Forwarded-For {client_ip}
          }
        }

        # All other routes: require Authelia authentication
        @not_options {
          not method OPTIONS
          not path /authelia/*
        }
        forward_auth @not_options 127.0.0.1:9091 {
          uri /authelia/api/authz/forward-auth?authelia_url=https://{base_url}/authelia/
          header_up X-Forwarded-Method {method}
          header_up X-Forwarded-Proto {scheme}
          header_up X-Forwarded-Host {host}
          header_up X-Forwarded-Uri {uri}
          header_up X-Forwarded-For {client_ip}
          copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
        }

        # Catch 401 and redirect to Authelia portal with return URL
        handle_errors {
          @401 {
            expression {err.status_code} == 401
          }
          handle @401 {
            redir https://{base_url}/authelia/?rd={scheme}://{host}{uri}
          }
        }
        
        root * /home/liou/dufs-lan/dist
        
        # 1. API Priority: Requests with ?json MUST go to Dufs
        @api {
          expression {query}.contains('json')
        }
        handle @api {
          reverse_proxy 127.0.0.1:5007
        }

        # Route tag-api to tag-server
        handle_path /tag-api/* {
          reverse_proxy 127.0.0.1:8081
        }

        # 2. UI Entry: Exact root path without ?json
        @ui_root {
          method GET HEAD
          path /
          not expression {query}.contains('json')
        }
        handle @ui_root {
          rewrite * /index.html
          file_server
        }

        # 3. Static Assets: Files that exist in dist/
        @static {
          method GET HEAD
          file
        }
        handle @static {
          file_server
        }
        
        # 4. Fallback: Everything else (nested API, file downloads) to Dufs
        handle {
          reverse_proxy 127.0.0.1:5007
        }
      }

    '';

    systemd.user.services.caddy = {
      Unit = {
        Description = "Caddy Web Server";
        After = [ "network.target" ];
      };
      Service = {
        ExecStart = "${pkgs.caddy}/bin/caddy run --config %h/.config/caddy/Caddyfile --adapter caddyfile";
        ExecReload = "${pkgs.caddy}/bin/caddy reload --config %h/.config/caddy/Caddyfile --adapter caddyfile";
        Restart = "on-failure";
      };
      Install = {
        WantedBy = [ "default.target" ];
      };
    };
  };
}
