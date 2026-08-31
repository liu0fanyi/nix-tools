# DUFS Plus deployment

The deployment has one shared Compose stack and one TOML file per machine:

| Instance | Engine | Published ports | Optional services |
| --- | --- | --- | --- |
| `instances/home.toml` | rootless Podman | `5006`, `5008`, `5009` | Authelia, read-only DUFS, DDNS-Go, host ttyd |
| `instances/aliyun.toml` | Docker | `80` | none |

`features.dufs_write` controls the primary DUFS permissions. It is enabled for
the authenticated home instance and disabled for the public Aliyun instance.
Read-only is the safe default in the shared Compose file.

When `features.readonly` is enabled, the additional home endpoint is a complete
read-only dufs-plus instance rather than the stock DUFS UI. It reuses the same
immutable frontend files and container image, but has its own
`dufs-readonly`/`tag-server-readonly` services, workspace, SQLite database, and
thumbnail metadata directory. Caddy advertises all write capabilities as
disabled and rejects non-read tag API methods. Internal tag-server database and
thumbnail-cache writes remain isolated under `paths.readonly_tag_data`; the
served source tree stays mounted read-only. Both home instances keep their
database and generated metadata in a per-root `.dufs_plus_state` directory.
Caddy authenticates the complete read-only site with the same Basic Auth account
as port 5006; the internal DUFS backend does not issue a second authentication
challenge.
Read-only instances also report `game_tools: false` and reject
`/dist/bevy-game/*` at Caddy, so the game tools are neither shown in the top bar
nor reachable through a copied direct URL.

Port 5008 accepts both protocols through the small `readonly-gateway` service:
plain HTTP is forwarded to Caddy's LAN listener, while a TLS ClientHello is
forwarded to its HTTPS listener. Consequently `http://nuc.local:5008/` behaves
like port 5006, while EdgeOne can continue HTTPS origin connections to the same
port without depending on a particular dynamic IPv6 address.

The Aliyun instance deliberately serves plain HTTP to EdgeOne. Caddy redirects
only requests carrying `X-Forwarded-Proto: http`; this preserves public HTTPS
without creating an EdgeOne-to-origin redirect loop. It does not publish 443.
Like the additional home read-only instance, it rejects Tag API mutations and
mounts the served workspace read-only. Its separate SQLite database and
thumbnail metadata directory remain writable for internal indexing and caches.

Runtime databases remain outside Git. Home secret sources are encrypted in Git
with git-crypt and decrypted in the deployment checkout. Each render securely
materializes them into `~/.config/dufs-plus/secrets` with directory mode `0700`
and file mode `0600`. Generated configuration, private Compose assets, and the
standalone Compose control script live under
`~/.local/share/dufs-plus/runtime/home`. Containers and the installed systemd
unit therefore do not depend on the Git checkout after deployment.
Private generated assets remain mode `0600`. The credential-free
`haproxy.readonly.cfg` is intentionally mode `0644`, because the official
HAProxy image runs as a non-root user and must read this bind-mounted file.

`manage.py preflight` removes group/world access from locally owned regular
runtime secret files before validating them; it rejects symlinks and paths owned
by a different user. The encrypted repository files remain the recoverable
source of truth. The home instance reuses the existing runtime directories. The
Aliyun instance reuses:

- `/root/nix-tools/dufs_data`
- `/root/nix-tools/tag-db/tag_all.db`
- `/root/nix-tools/dist`

## Management

Commands default to the home instance:

```bash
python3 deploy/scripts/manage.py config
python3 deploy/scripts/manage.py ps
python3 deploy/scripts/manage.py backup
python3 deploy/scripts/manage.py smoke \
  --base-url https://nas.wttliou.top:5009 --resolve-address 127.0.0.1
```

The default generated-output directory is
`~/.local/share/dufs-plus/runtime/home`. Passing `--output` remains supported for
isolated tests and remote profiles.

For Aliyun, pass its config and generated-output directory:

```bash
python3 deploy/scripts/manage.py \
  --config deploy/instances/aliyun.toml \
  --output deploy/.generated/aliyun config
```

`up` requires `--confirm`. `recreate tag-server` only replaces that
container and is intended for normal application releases.

Backups default to
`$XDG_STATE_HOME/dufs-plus/backups/<instance>` (normally
`~/.local/state/dufs-plus/backups/<instance>`) and retain the latest five
completed snapshots. Use `backup --keep-last 0` to disable pruning or
`backup --destination PATH` to choose another root.

## First installation

Render and install the generated user units on a new home host:

```bash
./scripts/install-dufs-media-mounts.sh --dry-run
sudo ./scripts/install-dufs-media-mounts.sh
bash deploy/bootstrap/install-user-service.sh
systemctl --user enable --now ttyd-compose.service dufs-plus-compose.service
```

`install-dufs-media-mounts.sh` validates the Art exFAT and project ext4
filesystem UUIDs, backs up `/etc/fstab`, and installs idempotent `nofail` mounts
at `/media/liou/Art` and `/media/liou/project`. The home deployment declares both
as required mounts and waits up to 30 seconds during preflight, preventing Podman
from binding and publishing empty mount-point directories during boot.

The VPS uses Docker and does not need the host terminal unit.

## Validation

The home and Aliyun profiles can be exercised without touching production:

```bash
python3 deploy/tests/integration/isolated-home.py
python3 deploy/tests/integration/isolated-aliyun.py
python3 -m unittest discover -s deploy/tests -p 'test_*.py'
```

The Aliyun test runs its HTTP origin temporarily on local port 15080.

## Releasing applications to both machines

After the initial VPS installation, this command builds both applications once,
updates the local instance, synchronizes the non-secret deployment control
plane, sends the same artifacts/image to Aliyun, applies both Compose stacks,
and smoke tests both:

```bash
python3 deploy/scripts/release-apps.py all
```

Individual releases are also supported:

```bash
python3 deploy/scripts/release-apps.py frontend --skip-bevy
python3 deploy/scripts/release-apps.py tag-server
python3 deploy/scripts/release-apps.py config
```

Frontend assets are uploaded with `index.html` last. Tag Server databases are
backed up on both machines before the image is transferred and the single
VPS service is recreated; the home release recreates both writable and
read-only tag-server instances. Container images are always transferred as individual
`podman save | zstd | ssh | docker load` streams; the VPS never needs to pull
them from Docker Hub. To seed or refresh all runtime images:

```bash
python3 deploy/scripts/release-apps.py runtime-images --skip-smoke
```

## Directory ownership

- `scripts/manage.py` and `scripts/render.py` are the production control plane.
- `scripts/release-apps.py` coordinates normal releases to home and Aliyun.
- `bootstrap/` contains one-time host installation helpers.
- `tests/integration/` contains temporary-stack validation only.
- `.generated/`, `__pycache__/`, runtime secrets, and backups are generated or
  private state and are ignored by Git.
