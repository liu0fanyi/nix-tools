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

## EdgeOne and Authelia

The private `nas.wttliou.top` CDN path must authorize at the edge before reading
shared cache objects. The deployed Edge Function source, console setup, cache
purge procedure, validation commands, quota caveat, and safe rollback order are
documented in
[`docs/edgeone-authelia-edge-auth.md`](docs/edgeone-authelia-edge-auth.md).

## PC 发起的两个发布流程

在 PC 的 `/home/liou/nix-tools` 执行：

```bash
devenv shell -- just deploy nuc infra
devenv shell -- just deploy aliyun all
```

省略组件时默认只应用基础设施配置；所有 manage 命令通过 SSH 在 NUC 执行。
保留 NUC 上的 secrets、运行数据与模型，不将 PC 当作生产主机。
配置更新前使用远端已安装的 manage.py 备份，再同步非密钥 deploy 文件、preflight、
应用 Compose 并重建 Caddy，最后 smoke。Compose 可能联动重建关联容器，有短暂中断。

NUC 产品发布可单独执行，也可通过 all 统一执行：

```bash
devenv shell -- just deploy nuc frontend
devenv shell -- just deploy nuc tag-server
devenv shell -- just deploy nuc all
```

两端都只调用产品的 just build；NUC 参数为 private，阿里云为 public。
传输、静态备份、容器激活、镜像回滚和验收统一维护在 nix-tools。
all 先完成本机构建，再备份、同步基础配置与镜像、激活后端、应用配置、上传前端并验收。
两个产品的 just deploy 都调用本入口，不再自带发布实现。
可用 NIX_TOOLS_DIR 指定 PC nix-tools 路径（默认 /home/liou/nix-tools）。

阿里云 all 在 PC 调用 dufs-plus 的 just build 和 tag-all 的 Containerfile
（通过 just build public 先 tester 再 public-runtime），只向阿里云发送前端与镜像，再应用 aliyun 配置。
不调用固定部署 NUC 的产品 redeploy 入口。镜像通过 Podman save/zstd/SSH/Docker load
传输，核对镜像 ID；保留旧镜像 rollback 标签和远端备份。
也支持 frontend、tag-server、infra 单独发布。

产品构建入口接受 private/public：公开前端不打包设备、转写管理和录音豆页面；
公开镜像不包含 Whisper CLI，也不构建 Whisper 阶段。Rust 业务二进制仍共用。
另外沿用 aliyun.toml 的只读、无终端、无 DDNS/Authelia、禁用游戏工具等权限和路由配置。
前端上传保护 Bevy 三个独立目录，并保留旧哈希资源，上传所有依赖后才更新入口。
远端 checksum 与阿里云公网 CDN 入口哈希不一致会报错。两端后端激活或其 smoke 失败
都会尝试恢复旧运行镜像；NUC 同时恢复读写两个服务。不会自动回滚数据库或前端，
需根据保留的镜像标签和状态备份处理；多个组件的发布不是原子事务。

runtime-images 仅发送对应目标的基础设施镜像；NUC 不包含 tag-server，
阿里云发送 Caddy 和 DUFS。infra/all 同样先在 PC 拉取这些官方镜像并传到目标引擎，
然后应用配置；不从源码编译 Caddy。

检查实际命令而不构建或发布：

```bash
devenv shell -- just deploy nuc all --dry-run
devenv shell -- just deploy aliyun all --dry-run
```

底层 `python3 deploy/scripts/release-apps.py` 必须显式提供 `--target nuc|aliyun`。
旧的无目标 `release all` 和 `--skip-bevy` 参数已取消。
普通 `manage` 简写也已改为通过 SSH 管理 NUC；
直接运行 manage.py 仅供目标服务器本地维护。

验证记录及限制见 [PC 发布流程](docs/pc-release.md)。

## Directory ownership

- `scripts/manage.py` and `scripts/render.py` are the production control plane.
- `scripts/release-apps.py` / `release_pc.py` provide explicit PC-to-NUC and PC-to-Aliyun entry points.
- `bootstrap/` contains one-time host installation helpers.
- `tests/integration/` contains temporary-stack validation only.
- `.generated/`, `__pycache__/`, runtime secrets, and backups are generated or
  private state and are ignored by Git.
