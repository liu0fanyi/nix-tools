{ pkgs, lib, isNixOS ? false, osConfig ? null, ... }:
let
  enabled = isNixOS && osConfig != null && osConfig.networking.hostName == "liu-bigpc";
  initialConfig = pkgs.writeText "amule-initial.conf" ''
    [eMule]
    AppVersion=${pkgs.amule.version}
    Nick=aMule
    Language=zh_CN
    Port=4662
    UDPPort=4672
    UDPEnable=1
    ConnectToED2K=1
    ConnectToKad=1
    Autoconnect=1
    Reconnect=1
    UPnPEnabled=1
    MaxUpload=1024
    MaxDownload=0
    MaxConnections=300
    MaxSourcesPerFile=300
    Serverlist=1
    AddServerListFromServer=0
    AddServerListFromClient=0
    Ed2kServersUrl=https://upd.emule-security.org/server.met
    KadNodesUrl=https://upd.emule-security.org/nodes.dat
    IncomingDir=/data/Downloads/aMule/Incoming
    TempDir=/data/Downloads/aMule/Temp
    CheckDiskspace=1
    MinFreeDiskSpace=10240
    NewVersionCheck=0

    [Obfuscation]
    IsClientCryptLayerSupported=1
    IsCryptLayerRequested=1
    IsClientCryptLayerRequired=0

    [ExternalConnect]
    AcceptExternalConnections=0

    [WebServer]
    Enabled=0
  '';
  addresses = pkgs.writeText "amule-addresses.dat" ''
    https://upd.emule-security.org/server.met
  '';
in
{
  config = lib.mkIf enabled {
    home.packages = [ pkgs.amule ];
    xdg.mimeApps.defaultApplications."x-scheme-handler/ed2k" = [ "org.amule.aMule.desktop" ];

    # Seed writable state only once. aMule maintains its own preferences and
    # learned Kad contacts; future activations must preserve both.
    home.activation.amuleConfig = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run mkdir -p "$HOME/.aMule" /data/Downloads/aMule/Incoming /data/Downloads/aMule/Temp
      if [ ! -e "$HOME/.aMule/amule.conf" ]; then
        run install -m 600 ${initialConfig} "$HOME/.aMule/amule.conf"
      fi
      if [ ! -e "$HOME/.aMule/addresses.dat" ]; then
        run install -m 600 ${addresses} "$HOME/.aMule/addresses.dat"
      fi
      if [ ! -e "$HOME/.aMule/server.met" ]; then
        run install -m 600 ${../../ref/amule-bootstrap/server.met} "$HOME/.aMule/server.met"
      fi
      if [ ! -e "$HOME/.aMule/nodes.dat" ]; then
        run install -m 600 ${../../ref/amule-bootstrap/nodes.dat} "$HOME/.aMule/nodes.dat"
      fi
    '';
  };
}
