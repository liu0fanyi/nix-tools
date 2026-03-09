{
  pkgs,
  lib,
  config,
  ...
}:
let
  cfg = config.features.authelia;
  secrets = builtins.fromJSON (builtins.readFile ../../secrets.json);
in
{
  options.features.authelia = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable Authelia authentication service";
    };
  };

  config = lib.mkIf cfg.enable {
    # We use an activation script instead of xdg.configFile because Podman 
    # cannot follow symlinks pointing to the Nix store in volume mounts.
    home.activation.setupAutheliaFiles = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      $DRY_RUN_CMD mkdir -p $VERBOSE_ARG \
        "$HOME/.config/authelia" \
        "$HOME/.local/share/authelia"

      # Write Authelia main configuration using a quoted heredoc to prevent shell expansion of '$'
      # Nix interpolation happens before the shell script runs.
      cat > "$HOME/.config/authelia/configuration.yml" << 'AUTHELIA_CONFIG_EOF'
---
server:
  address: tcp://0.0.0.0:9091/authelia
  endpoints:
    authz:
      forward-auth:
        implementation: 'ForwardAuth'

log:
  level: info

identity_validation:
  reset_password:
    jwt_secret: ${secrets.authelia_jwt_secret}

authentication_backend:
  password_reset:
    disable: false
  file:
    path: /config/users_database.yml
    password:
      algorithm: argon2id
      iterations: 3
      memory: 65536
      parallelism: 4
      salt_length: 16
      key_length: 32

# Two-factor authentication settings
totp:
  issuer: wttliou.top
  period: 30
  skew: 1

webauthn:
  timeout: 60s
  display_name: NAS
  attestation_conveyance_preference: indirect
  selection_criteria:
    user_verification: preferred

# Session configuration
session:
  name: authelia_session
  secret: ${secrets.authelia_session_secret}
  expiration: 12h
  inactivity: 3h
  remember_me: 1M
  cookies:
    - domain: wttliou.top
      authelia_url: https://nas.wttliou.top/authelia/

# Persistent storage (SQLite)
storage:
  encryption_key: ${secrets.authelia_storage_key}
  local:
    path: /data/db.sqlite3

# Notifier: writes registration/reset links to a local file
notifier:
  disable_startup_check: false
  filesystem:
    filename: /config/notification.txt

# Access control: require two-factor for all resources by default
access_control:
  default_policy: two_factor
  rules:
    # Allow Authelia's own internal forward-auth verification endpoint
    - domain:
        - "nas.wttliou.top"
        - "home.wttliou.top"
      resources:
        - "^/authelia/api/authz/forward-auth.*$"
      policy: bypass
AUTHELIA_CONFIG_EOF

      # Write users database
      cat > "$HOME/.config/authelia/users_database.yml" << 'USERS_DB_EOF'
---
users:
  admin:
    displayname: "Admin"
    password: "${secrets.authelia_password_hash}"
    email: admin@wttliou.top
    groups:
      - admins
USERS_DB_EOF
      
      $VERBOSE_ARG chmod 600 "$HOME/.config/authelia/configuration.yml" "$HOME/.config/authelia/users_database.yml"
    '';

    # Podman container for Authelia
    services.podman.containers.authelia = {
      image = "docker.io/authelia/authelia:latest";
      autoStart = true;
      autoUpdate = "registry";
      # Only accessible from localhost; Caddy proxies to it
      ports = [ "127.0.0.1:9091:9091" ];
      volumes = [
        "%h/.config/authelia:/config"
        "%h/.local/share/authelia:/data"
      ];
      environment = {
        # Using env vars for trusted proxies to circumvent YAML parsing issues in v4.39.15
        AUTHELIA_SERVER_TRUSTED_PROXIES = "127.0.0.1,::1";
      };
    };

    home.file.".config/systemd/user/podman-authelia.service.d/override.conf".text = ''
      [Service]
      Environment="PATH=/usr/bin:/bin:${lib.makeBinPath [ pkgs.podman ]}"
    '';
  };
}
