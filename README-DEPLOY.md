# dufs-plus Podman 应用部署

这套部署将应用服务从 Home Manager user services 切换到 Podman Compose。当前默认配置是本机原地切换：继续使用现有数据、域名、EdgeOne、DDNS-Go 和认证状态，不搬动正式数据。

## 当前状态

- `deploy/instance.toml` 是唯一的非敏感实例配置。
- `deploy/secrets/` 保存当前实例 secrets，真实内容被 Git 忽略。
- `deploy/.generated/` 保存自动生成的 Compose override、Caddyfile 和 Authelia 配置，整个目录被 Git 忽略。
- 当前正式 Nix/Home Manager 服务仍在运行。
- 隔离测试使用临时数据和 `15006/15008/15009` 端口，不接触正式数据库。

旧版根目录 Compose/Caddy 原型已经移除，正式入口是 `deploy/scripts/manage.py`。

## 配置

编辑：

```text
deploy/instance.toml
```

支持的 Profile：

- `home-ipv6-cdn`：家庭动态公网 IPv6、DDNS-Go、EdgeOne 回源。
- `vps-direct`：固定公网 IP，Caddy 直接监听 `80/443`，不启动 DDNS-Go。

本机默认使用：

```toml
[deployment]
profile = "home-ipv6-cdn"

[features]
readonly = true
terminal = true
ddns = true
```

本机配置实际设置 `terminal = true`：ttyd 继续运行在宿主机中，保留 Nix
工具链、PATH 和现有 zellij 会话；Caddy 容器只通过
`/run/user/1000/ttyd/ttyd.sock` Unix socket 访问它。新服务器没有对应的
宿主机开发环境时设置为 `false`。

## Secrets

本机首次准备：

```bash
cd nix-tools/deploy
python3 scripts/import-current-secrets.py
```

导入来源：

- git-crypt 解锁后的 `secrets.json`
- 当前 Authelia 用户文件
- 当前 Caddy LAN basic-auth hash
- 当前 Tag Server env

脚本不会打印 secret 内容。生成目录权限为 `0700`，文件为 `0600`。

新服务器不运行导入脚本，应根据 `deploy/secrets/README.md` 自行提供 secret 文件。

## 日常命令

所有命令在 `nix-tools` 目录执行。

生成配置：

```bash
python3 deploy/scripts/manage.py render
```

检查路径、secret、SQLite 和依赖：

```bash
python3 deploy/scripts/manage.py preflight
```

让 Podman Compose 解析最终合并配置：

```bash
python3 deploy/scripts/manage.py config
```

创建一致性备份：

```bash
python3 deploy/scripts/manage.py backup
```

备份保存在被 Git 忽略的 `deploy/backups/`，包含：

- Tag SQLite 在线一致性备份
- Authelia SQLite 在线一致性备份
- 所有 `.tag` sidecar
- DDNS-Go 配置
- instance 配置和 runtime secrets
- SHA-256 manifest

运行隔离测试：

```bash
python3 deploy/scripts/isolated-test.py
```

隔离测试会：

1. 在线备份当前两个 SQLite 到临时目录。
2. 创建临时 workspace、Caddy data 和容器网络。
3. 启动 Caddy、两个 DUFS、Tag Server 和 Authelia。
4. 使用 `15006/15008/15009` 测试入口和认证跳转。
5. 自动停止并删除测试容器和网络。

它不会启动 DDNS-Go，不会修改 DNS，也不会写正式数据。

## 本机正式切换

切换脚本默认拒绝执行，必须显式确认：

```bash
python3 deploy/scripts/cutover.py --confirm
```

切换步骤：

1. 创建切换前一致性备份。
2. 启动 socket 版宿主机 ttyd，并确认 socket 已建立。
3. 停止旧 Caddy、TCP 版 ttyd、DDNS-Go、Authelia、Tag Server 和两个 DUFS。
4. 对 Tag SQLite 执行 WAL checkpoint。
5. 再创建一份停止写入后的备份。
6. 使用原路径启动 Compose。
7. 直连本机源站端口并携带公开 Host，检查 Caddy 和 Authelia；这不会受
   本机 DNS 分流或 CDN 回流能力影响。
8. 安装并启用 `dufs-plus-compose.service`。
9. 禁用旧 user services。

任何一步失败都会执行 `podman compose down`，并尝试重新启动切换前处于 active 状态的旧服务。

切换前仍建议另开一个 SSH 会话，避免当前终端断开后无法处理异常。

## 自动启动

只安装但不启用 systemd user unit：

```bash
bash deploy/scripts/install-user-service.sh
```

正式切换成功后启用：

```bash
systemctl --user enable dufs-plus-compose.service
```

目标用户还需要启用 linger，确保退出登录后 user services 继续运行：

```bash
loginctl enable-linger "$USER"
```

`cutover.py` 会安装并启用 Compose unit，但不会修改系统级 linger。

切换成功并确认回滚不再需要后，应用专用的 Home Manager profile，避免以后
`home-manager switch` 又生成旧的 Caddy、Authelia、DUFS 和 TCP ttyd unit：

```bash
home-manager switch --flake .#liou-compose
```

这个 profile 仍保留 Podman、Podman Compose、socket、日常容器工具，以及通过
Unix socket 提供完整宿主机开发环境的 `ttyd-compose.service`；其余应用服务
交给 `dufs-plus-compose.service` 管理。不要在切换验证完成前应用它，否则会
提前移除旧服务定义，降低回滚便利性。

## 家庭 Profile

保持当前链路：

```text
nas.wttliou.top
  -> EdgeOne
  -> home.wttliou.top:5009
  -> Caddy
  -> Authelia
  -> dufs-lan / tag-server

workcdn.wttliou.top
  -> EdgeOne
  -> work.wttliou.top:5008
  -> Caddy
  -> dufs-readonly
```

Compose 继续挂载当前 DDNS-Go 配置目录，因此本机原地切换不需要重新填写 Web UI。

## VPS Profile

至少修改：

```toml
[deployment]
profile = "vps-direct"

[features]
ddns = false

[domains]
public = "实际主域名"
readonly_public = "实际只读域名"
```

VPS 需要：

- DNS A 指向固定公网 IPv4。
- 有固定 IPv6 时配置 AAAA。
- 防火墙开放 `80/443`。
- Rootless Podman 能绑定低位端口，或者在宿主机做高位端口转发。
- Authelia cookie/session domain 与公开域名一致。

## 手工回滚

如果 Compose 已启动：

```bash
python3 deploy/scripts/manage.py down
systemctl --user disable --now ttyd-compose
```

然后启动旧服务：

```bash
systemctl --user start podman-dufs
systemctl --user start podman-dufs-lan
systemctl --user start podman-tag-server
systemctl --user start podman-authelia
systemctl --user start podman-ddns-go
systemctl --user start ttyd
systemctl --user start caddy
```

如果旧服务已被禁用，需要先重新 `enable`。

## 不包含的服务

- rclone-mount：已经停用，不迁移。
- tunnel：当前没有运行或配置，不引入。
