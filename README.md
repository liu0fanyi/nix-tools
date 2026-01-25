# Nix Tools

This repository contains Nix configuration and tools.

## Installation

To install Nix on any Linux distribution, the recommended way is using the [Determinate Systems Nix Installer](https://github.com/DeterminateSystems/nix-installer):

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

## Usage

### Initial HomeManager

To run the `rerun.nu` script for the first time, use (replace `liou` with your current username):

```bash
nix shell nixpkgs#nushell -c nu ./rerun.nu liou
```

By default it enables all features. To use a "lite" version (without Fcitx5 & Podman), run:

```bash
nix shell nixpkgs#nushell -c nu ./rerun.nu liou --full=false
```

## GPU Setup (Non-NixOS)

If you are on a non-NixOS system and need GPU support (e.g., for Alacritty), you may need to run the following command with `sudo`:

```bash
sudo /nix/store/9mn5fg9rdw4p8kw0nqz0h5ymwjxhb6is-non-nixos-gpu/bin/non-nixos-gpu-setup
```

## Troubleshooting

### Applications not showing in menu

If you cannot see applications like Alacritty, Zellij, or Sakura in your system's application menu:

**Logout and Re-login**: On non-NixOS systems, the desktop environment often needs a fresh session to pick up the new paths in `XDG_DATA_DIRS`.

### Untrusted substituter warning

If you see a warning like `warning: ignoring untrusted substituter...`:

This happens because your user is not in the `trusted-users` list of your system's Nix configuration. Run the following command to fix it:

```bash
echo "trusted-users = root $USER" | sudo tee -a /etc/nix/nix.custom.conf
# Then restart the nix-daemon
sudo systemctl restart nix-daemon
```

### Podman services not starting

If `ddns-go` or `rustfs` are not starting automatically:

**Enable Linger**: On generic Linux, user services only run when you are logged in. To let them run from boot (and ensure they start correctly), enable linger:
    ```bash
    loginctl enable-linger $USER
    ```

### Error: "newuidmap" not found

If you see an error like `exec: "newuidmap": executable file not found in $PATH` in the logs:

Rootless Podman requires the `newuidmap` and `newgidmap` tools to be installed on the host system (not just via Nix) because they require setuid permissions. On Debian-based systems (like Pop!_OS, Ubuntu):

```bash
sudo apt update
sudo apt install uidmap
```

### Podman congifuration options

For more Podman configuration options in Home Manager, check: [Home Manager Options - Podman](https://home-manager-options.extranix.com/?query=podman&release=release-25.11)
