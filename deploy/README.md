# DUFS Plus deployment

The deployment has one shared Compose stack and one TOML file per machine:

| Instance | Engine | Published ports | Optional services |
| --- | --- | --- | --- |
| `instances/home.toml` | rootless Podman | `5006`, `5008`, `5009` | Authelia, read-only DUFS, DDNS-Go, host ttyd |
| `instances/aliyun.toml` | Docker | `80` | none |

The Aliyun instance deliberately serves plain HTTP to EdgeOne. Caddy redirects
only requests carrying `X-Forwarded-Proto: http`; this preserves public HTTPS
without creating an EdgeOne-to-origin redirect loop. It does not publish 443.

Runtime secrets and databases remain outside Git. The home instance reuses the
existing directories. The Aliyun instance reuses:

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

For Aliyun, pass its config and generated-output directory:

```bash
python3 deploy/scripts/manage.py \
  --config deploy/instances/aliyun.toml \
  --output deploy/.generated/aliyun config
```

`up` requires `--confirm-cutover`. `recreate tag-server` only replaces that
container and is intended for normal application releases.

## Validation

The home and Aliyun profiles can be exercised without touching production:

```bash
python3 deploy/scripts/isolated-test.py
python3 deploy/scripts/isolated-aliyun-test.py
```

The Aliyun test runs its HTTP origin temporarily on local port 15080.

## Releasing applications to both machines

After the initial VPS installation, this command builds both applications once,
updates the local instance, sends the same artifacts/image to Aliyun, and smoke
tests both:

```bash
python3 deploy/scripts/release-apps.py all
```

Individual releases are also supported:

```bash
python3 deploy/scripts/release-apps.py frontend --skip-bevy
python3 deploy/scripts/release-apps.py tag-server
```

Frontend assets are uploaded with `index.html` last. Tag Server databases are
backed up on both machines before the image is transferred and the single
service is recreated. Container images are always transferred as individual
`podman save | zstd | ssh | docker load` streams; the VPS never needs to pull
them from Docker Hub. To seed or refresh all runtime images:

```bash
python3 deploy/scripts/release-apps.py runtime-images --skip-smoke
```
