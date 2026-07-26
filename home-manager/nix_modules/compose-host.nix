{ lib, ... }:
{
  # Keep Podman itself available, but let deploy/compose*.yaml own the
  # application containers and their lifecycle.
  features.podman.enable = lib.mkDefault true;
  features.podman.legacyServices.enable = false;
  features.podman.hostTerminal.enable = true;
  features.caddy.enable = false;
  features.authelia.enable = false;
}
