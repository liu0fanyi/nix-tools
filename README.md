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

## Windows clipboard-sync

Run this from the repository root, or double-click it in Explorer:

```powershell
.\win-setup.cmd
```

The wrapper installs the prebuilt `bin/clipboard-sync.exe` through
`clipboard-sync/setup-windows.nu` and configures login startup.

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

## Remote NixOS reinstall

The current `192.168.1.6` host uses a dedicated 16 GiB swap LV. For a future full reinstall,
the repository includes a nixos-anywhere entry point that lets disko reserve a
dedicated swap LV. The script selects a 16/24/32/64 GiB tier from target RAM, or
you can override it with `NIXOS_ANYWHERE_SWAP_GIB` or `NIXOS_ANYWHERE_FLAKE`:

```bash
bash scripts/install-nixos-anywhere.sh
```

It defaults to `root@192.168.1.6` and requires typing `REINSTALL` before
destructive disk operations. After verifying backups, `bash
scripts/install-nixos-anywhere.sh --yes` skips that prompt.
The automatic profiles currently require x86_64, writable UEFI efivars, and a
single internal `/dev/sda`; other disk layouts, BIOS systems, or architectures
are rejected before any destructive operation and need a dedicated flake first.

The installer auto-detects the local Clash Verge/mihomo proxy at
`127.0.0.1:7897`, adds the Tsinghua Nix substituter, and by default pushes the
closure from the local machine instead of making the kexec environment fetch
large dependencies itself. Set `NIXOS_ANYWHERE_PROXY_MODE=off` to disable the
proxy, or `NIXOS_ANYWHERE_USE_DESTINATION_SUBSTITUTERS=1` to restore destination
substitution.

The default kexec mode also downloads the official installer image through the
local proxy and caches it under `~/.cache/nixos-anywhere`, then passes it to
`nixos-anywhere --kexec`. This avoids the target's temporary installer system
directly downloading GitHub's 418 MiB image. Reuse or override it with
`NIXOS_ANYWHERE_KEXEC_PATH`, change the cache with
`NIXOS_ANYWHERE_KEXEC_CACHE_DIR`, or explicitly set
`NIXOS_ANYWHERE_KEXEC_MODE=remote` if the target can download it directly. See
the upstream [`--kexec` documentation](https://github.com/nix-community/nixos-anywhere/blob/main/docs/howtos/custom-kexec.md).

The target and both proxy addresses are external settings, so changing the
Clash Verge port does not require editing the script:

```bash
NIXOS_ANYWHERE_TARGET=root@192.168.1.23 \
NIXOS_ANYWHERE_PROXY_URL=http://127.0.0.1:8890 \
NIXOS_ANYWHERE_REMOTE_PROXY_URL=http://192.168.1.3:8890 \
  bash scripts/install-nixos-anywhere.sh --check
```

`NIXOS_ANYWHERE_PROXY_URL` is used by the local installer;
`NIXOS_ANYWHERE_REMOTE_PROXY_URL` is the LAN-reachable URL used temporarily by
the target after installation. If omitted, the latter is derived by replacing
the loopback address with the local route address. Set
`NIXOS_ANYWHERE_REMOTE_PROXY_CHECK=required` when the target must reach that
proxy or the script should stop before wiping. `NIXOS_ANYWHERE_TARGET` can also
be composed from `NIXOS_ANYWHERE_SSH_USER` and `NIXOS_ANYWHERE_SSH_HOST`.

The Tsinghua substituter is enabled both for the installer invocation and in
the resulting NixOS configuration. Override the one-time installer value with
`NIXOS_ANYWHERE_EXTRA_SUBSTITUTERS`; use `NIXOS_ANYWHERE_SWAP_GIB` to select a
different predefined swap tier.

When `nix-tools-git-crypt.key` and the unlocked runtime secrets are available, the
installer also restores mihomo/clashtui, Rime user data, and npm tools after the
NixOS switch. The restore helper downloads and caches mihomo's `geosite.dat` and
`geoip.dat` through the local proxy, uploads them with the config, and temporarily
passes the target-reachable LAN proxy only for initial subscription downloads;
that systemd environment is removed afterward. After nixos-anywhere reboots the
target, the installer waits for SSH to return before running this restore. The
default `NIXOS_ANYWHERE_RESTORE_SECRETS=required` refuses to
erase the target if those secrets are unavailable; use `=off` only for a base
system without runtime secrets.

Personal credentials are kept outside the repository. The default KeePassXC
database is `~/Sync/secrets/secrets.kdbx`; Syncthing replicates only this
encrypted database. Plaintext exports needed by local programs live under
`~/.config/secrets/<group>/`, with the git-crypt key at
`~/.config/secrets/nix-tools/nix-tools-git-crypt.key`. Initialize the vault and
export the git-crypt key with the unified script:

```nu
bash scripts/vault.sh init                # 首次创建加密库
bash scripts/vault.sh nix-tools export    # 导出 git-crypt key 到 ~/.config/secrets/nix-tools/
```

The git-crypt key unlocks both `secrets/` (mihomo/Rime) and
`deploy/secrets/` (DUFS Plus runtime credentials), which are stored encrypted
in Git. See `deploy/secrets/README.md` for the workflow.

Other credentials, such as model API keys, should remain KeePassXC entries
(for example `ai/openai-api-key`) and only be exported to
`~/.config/secrets/` when a program explicitly needs a file or environment
variable. Override the paths with `NIX_TOOLS_SECRETS_DIR`, `NIX_TOOLS_SYNC_DIR`,
or `NIX_TOOLS_VAULT_FILE`.

See [the KeePassXC CLI vault guide](docs/secret-vault-cli.md) for commands to
add and retrieve API keys, and to import or export encrypted file attachments.

This post-install step is required because the mihomo configuration contains
subscription secrets and is intentionally not in the NixOS closure. Without it,
mihomo creates a tiny default configuration on first boot (`127.0.0.1:7890` and
no controller), so clashtui reports `connection refused`.

The NixOS service also declares the shared `clashtui/mihomo` directory with
setgid/group-write permissions and uses `UMask=0007`, so root-created provider
and cache files remain manageable by clashtui without a first-run “Fix now”.

See [nixos/reinstall-checklist.md](nixos/reinstall-checklist.md) for the
preflight, automatic post-install checks, and manual desktop checks. To run
the complete non-destructive reinstall preflight:

```bash
bash scripts/install-nixos-anywhere.sh --check
```
