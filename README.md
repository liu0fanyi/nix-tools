# Nix Tools

Host development configuration and the container deployment control plane for
DUFS Plus.

## Home Manager

Install Nix with the
[Determinate Systems installer](https://github.com/DeterminateSystems/nix-installer),
then apply the host configuration:

```bash
nix shell nixpkgs#nushell -c nu ./rerun.nu liou
```

Home Manager installs development applications, Podman tooling, ttyd, and the
Podman API socket. It does not own Caddy, DUFS, Tag Server, Authelia, DDNS-Go,
or their systemd services.

On non-NixOS hosts, rootless Podman also requires the distribution package that
provides `newuidmap` and `newgidmap` (for example `uidmap` on Debian/Ubuntu).

## DUFS Plus deployment

Application services are exclusively managed by the shared Compose deployment:

```bash
python3 deploy/scripts/manage.py config
python3 deploy/scripts/manage.py ps
python3 deploy/scripts/release-apps.py all
```

See [deploy/README.md](deploy/README.md) for instance configuration, bootstrap,
backup, validation, and release commands. Runtime secrets are supplied outside
Git under `deploy/secrets/`.

For user services to start without an interactive login:

```bash
loginctl enable-linger "$USER"
```
