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
        # 关键修改 1: 禁用 HTTP 到 HTTPS 的自动重定向
        # 这样 Caddy 就不会去尝试绑定 80 端口了，避免 permission denied
        auto_https disable_redirects

        # 关键修改 2: 禁止自动安装信任证书
        # 避免日志里出现 sudo 报错
        skip_install_trust
      }

      http://:5008 {
        # tls internal
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

        # [NEW] Route tag-api to tag-server
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
