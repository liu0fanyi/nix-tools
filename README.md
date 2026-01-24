# Nix Tools

This repository contains Nix configuration and tools.

## Installation

To install Nix on any Linux distribution, the recommended way is using the [Determinate Systems Nix Installer](https://github.com/DeterminateSystems/nix-installer):

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

## Usage

### Initial HomeManager

To run the `rerun.nu` script for the first time, use:

```bash
nix shell nixpkgs#nushell -c nu ./rerun.nu liou
```

By default it enables all features. To use a "lite" version (without IBus-Rime), run:

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

1.  **Logout and Re-login**: On non-NixOS systems, the desktop environment often needs a fresh session to pick up the new paths in `XDG_DATA_DIRS`.
2.  **Manual XDG Path**: If they still don't show up, add the following to your shell profile (e.g., `~/.bashrc` or `~/.zshrc`):

    ```bash
    export XDG_DATA_DIRS="$HOME/.nix-profile/share:$XDG_DATA_DIRS"
    ```

    Note: Home Manager with `targets.genericLinux.enable = true;` (already enabled in this config) tries to handle this, but some desktop environments require a manual export or a full session restart.

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

1.  **Enable Linger**: On generic Linux, user services only run when you are logged in. To let them run from boot (and ensure they start correctly), enable linger:
    ```bash
    loginctl enable-linger $USER
    ```
2.  **Check Status**: Check if the services are running or why they failed:
    ```bash
    systemctl --user status ddns-go
    systemctl --user status rustfs
    ```
3.  **Manual Start**: You can manually start them once to test:
    ```bash
    systemctl --user enable --now ddns-go rustfs
    ```

### Error: "newuidmap" not found

If you see an error like `exec: "newuidmap": executable file not found in $PATH` in the logs:

Rootless Podman requires the `newuidmap` and `newgidmap` tools to be installed on the host system (not just via Nix) because they require setuid permissions. On Debian-based systems (like Pop!_OS, Ubuntu):

```bash
sudo apt update
sudo apt install uidmap
```

### Why is this different from the NixOS Wiki?

The [NixOS Wiki for Podman](https://nixos.wiki/wiki/Podman) assumes you are using **NixOS**. On NixOS, the system handles `subuid`/`subgid` and kernel configuration automatically via `virtualisation.podman.enable`.

On **Generic Linux (Ubuntu/Pop!_OS)**:
- We use Home Manager's `systemd.user.services` instead of `virtualisation.oci-containers`.
- We must manually install `uidmap` on the host because Nix cannot provide the `setuid` binaries required for rootless mode.
- We use `systemd.user.startServices = "sd-switch";` to ensure services update when you run `rerun.nu`.
