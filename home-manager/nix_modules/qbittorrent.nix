{ pkgs, lib, isNixOS ? false, osConfig ? null, ... }:
let
  enabled = isNixOS && osConfig != null && osConfig.networking.hostName == "liu-bigpc";
  # Native qBittorrent 5 subscription; mirror recommended by XIU2 upstream.
  # Seed a writable config once, so application preferences remain editable.
  initialConfig = pkgs.writeText "qbittorrent-initial.conf" ''
    [BitTorrent]
    Session\AddTrackersFromURLEnabled=true
    Session\AdditionalTrackersURL=https://jsd.onmicrosoft.cn/gh/XIU2/TrackersListCollection/best.txt
    Session\DHTEnabled=true
    Session\PeXEnabled=true
    Session\LSDEnabled=true

    [Preferences]
    General\Locale=zh_CN
  '';
in
{
  config = lib.mkIf enabled {
    home.packages = [ pkgs.qbittorrent ];
    xdg.mimeApps = {
      enable = true;
      defaultApplications = {
        "x-scheme-handler/magnet" = [ "org.qbittorrent.qBittorrent.desktop" ];
        "application/x-bittorrent" = [ "org.qbittorrent.qBittorrent.desktop" ];
      };
    };
    home.activation.qbittorrentConfig = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      if [ ! -e "$HOME/.config/qBittorrent/qBittorrent.conf" ]; then
        run mkdir -p "$HOME/.config/qBittorrent"
        run install -m 600 ${initialConfig} "$HOME/.config/qBittorrent/qBittorrent.conf"
      fi
    '';
  };
}
