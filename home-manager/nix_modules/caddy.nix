{ pkgs, config, lib, ... }:

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
      :5000 {
        reverse_proxy 127.0.0.1:5005
        log {
          output file %h/.local/share/caddy/access.log
        }
      }

      :5006 {
        # Access Contorl: Only allow private IP ranges (LAN)
        @lan {
          remote_ip 192.168.0.0/16 172.16.0.0/12 10.0.0.0/8 127.0.0.1/8 ::1
        }
        handle @lan {
          reverse_proxy 127.0.0.1:5007
        }
        # Reject everyone else (Public Internet / IPv6 Global)
        handle {
          abort
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
