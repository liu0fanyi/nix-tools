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
      http://wttliou.top:5000 {
        reverse_proxy 127.0.0.1:5005
        log {
          output file %h/.local/share/caddy/access.log
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
