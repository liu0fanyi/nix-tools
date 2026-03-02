{
  pkgs,
  config,
  lib,
  ...
}:

{
  home.packages = [ pkgs.caddy ];

  xdg.configFile."caddy/Caddyfile".text = ''
    {
      # Global options
      # Uncomment and set your email to enable Let's Encrypt / ZeroSSL automatic HTTPS registration
      email liu_fanyi@hotmail.com
    }

    # Replace example.com with your actual public domain
    # e.g., mydomain.com {
    wttliou.top {
      # Apply basic auth to the entire site
      # basicauth {
      #   admin $2a$14$jQ8iy6ybRwnQVDxCFAxEO.VoyPMR7GZVbYgyjcimvUMU1lePXP7NK
      # }

      root * /root/dufs/dist

      # Route tag-api requests to Tag Server container
      handle_path /tag-api/* {
        reverse_proxy 127.0.0.1:8081
      }

      # 1. API Priority: Requests with ?json MUST go to Dufs
      @api {
        expression {query}.contains('json')
      }
      handle @api {
        reverse_proxy 127.0.0.1:5005
      }

      # 2. UI Entry: Exact root path without ?json
      @ui_root {
        path /
        not expression {query}.contains('json')
      }
      handle @ui_root {
        rewrite /index.html
        file_server
      }

      # 3. Static Assets: Files that exist in dist/
      @static {
        file
      }
      handle @static {
        file_server
      }

      # 4. Fallback: Everything else (nested API, file downloads) to Dufs
      handle {
        reverse_proxy 127.0.0.1:5005
      }
    }
  '';

  systemd.user.services.caddy = {
    Unit = {
      Description = "Caddy Web Server";
      After = [ "network.target" ];
    };
    Service = {
      # Note: To allow Caddy to bind to ports 80 and 443 with an unprivileged user,
      # ensure `sysctl net.ipv4.ip_unprivileged_port_start=80` is set on the host Linux machine.
      ExecStartPre = "-${pkgs.coreutils}/bin/mkdir -p %h/.local/share/caddy";
      ExecStart = "${pkgs.caddy}/bin/caddy run --config %h/.config/caddy/Caddyfile --adapter caddyfile";
      ExecReload = "${pkgs.caddy}/bin/caddy reload --config %h/.config/caddy/Caddyfile --adapter caddyfile";
      Restart = "on-failure";
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };
}
