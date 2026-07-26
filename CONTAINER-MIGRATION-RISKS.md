# dufs-lan 容器迁移风险说明

这份文档记录将对外访问的 `dufs-lan` 服务栈，从 Home Manager/Nix user services 迁移到统一容器/Compose 编排时的风险、目标形态、验证项和回滚步骤。

## 复核结论

早期的根目录 `docker-compose.yml` 和 `Caddyfile.prod` 最小原型已移除，避免误用；正式实现位于 `deploy/`。

当前实际服务全貌是：

- Caddy 提供局域网入口、受 Authelia 保护的公网入口，以及单独的只读 `work` 入口。
- `dufs-lan` 提供可写文件服务。
- 另一个 `dufs` 实例提供只读文件服务。
- `tag-server` 共享 `dufs-lan` 的 workspace，并维护 SQLite、sidecar 和阅读元数据。
- Authelia 提供公网入口的两步认证。
- `ddns-go` 更新当前动态 IPv6 地址。
- `ttyd` 提供受 Caddy/Authelia 保护的 Web 终端。

所以迁移目标不能只是“Caddy + Dufs + Tag Server”，而应覆盖现有入口、认证、数据路径和可选服务。

另外，当前部分口令会出现在进程启动参数中，通过服务状态即可看到。新方案不得把口令写进 Compose `command`、镜像、版本库或可公开读取的启动参数；迁移时应轮换已有口令。

## 支持的两种部署环境

本次迁移只支持手头实际存在的两类服务器：

| Profile | 网络条件 | 公网访问链路 | DDNS |
| --- | --- | --- | --- |
| `home-ipv6-cdn` | 家庭网络，有动态、可路由的公网 IPv6，没有可直接服务所有 IPv4 客户端的公网 IPv4 | IPv4/IPv6 客户端 → EdgeOne CDN → 动态 IPv6 原站 → Caddy 高位端口 | 必须启用 |
| `vps-direct` | VPS 有固定公网 IPv4；如需保证纯 IPv6 客户端直连，还需要固定公网 IPv6 | IPv4/IPv6 客户端 → DNS A/AAAA → Caddy `80/443` | 不启用 |

当前家庭机对应的链路是：

```text
nas.wttliou.top       -> EdgeOne -> home.wttliou.top:5009 -> Caddy -> Authelia -> dufs-lan/tag-server
workcdn.wttliou.top   -> EdgeOne -> work.wttliou.top:5008 -> Caddy -> dufs-readonly
                                     ^
                                     |
                         ddns-go 更新原站域名 AAAA
```

其中：

- `nas.wttliou.top`、`workcdn.wttliou.top` 是用户访问的 CDN 域名。
- `home.wttliou.top`、`work.wttliou.top` 是只供 CDN 找到家庭服务器的原站域名。
- DDNS-Go 只更新原站域名的 AAAA，不修改 CDN 对外域名。
- `5006` 是家庭局域网入口，不应暴露给公网。
- `5008` 是只读原站入口，`5009` 是受 Authelia 保护的主原站入口。

DDNS 只负责更新 DNS 记录，不能穿透 CGNAT。这里的“没有独立 IP”是指没有固定 IP、但仍有可路由的动态公网 IPv6；完全没有可路由公网地址的服务器不在本次迁移范围内。

两种 Profile 复用相同的核心容器、数据卷和应用路由，但使用不同的 Caddy 入口、DNS、防火墙和 Compose 叠加配置。

### `home-ipv6-cdn` 必需配置

服务器内：

- 为服务器取得稳定的局域网地址和可路由公网 IPv6。
- Podman 运行核心容器，并额外启用 `compose.ddns.yaml`。
- DDNS-Go 使用 host network 或其它能正确探测宿主机公网 IPv6 的方式运行。
- 持久化 DDNS-Go 配置；配置 DNS 服务商、token、IPv6 获取方式、更新周期以及原站域名。
- Caddy 监听局域网端口 `5006`、只读原站端口 `5008` 和主原站端口 `5009`。
- Caddy 只信任实际使用的 EdgeOne 回源地址段，正确读取真实客户端 IP。
- Authelia cookie、redirect URL、WebAuthn RP 信息全部使用用户访问的 CDN 主域名，不能使用原站域名。

路由器和主机防火墙：

- 允许 EdgeOne 回源访问服务器 IPv6 的 `5008/5009`。
- 不向公网开放 `5006`。
- 最好把 `5008/5009` 的来源限制为 EdgeOne 回源网段；如果路由器做不到，再由主机防火墙和 Caddy 双重限制。
- IPv6 通常不是端口映射问题，而是入站防火墙放行问题；部署前必须从外网实际验证。

DNS/DDNS：

- 原站域名配置 AAAA，并交给 DDNS-Go持续更新。
- CDN 对外域名按 EdgeOne 要求设置 CNAME/接入记录，不由 DDNS-Go更新。
- 原站域名和对外域名分离，避免 CDN 配置递归回源到自己。

EdgeOne：

- 分别配置主站和可选只读站的回源域名、IPv6 原站端口、Host header 和 SNI。
- 主站回源到 `5009`，只读站回源到 `5008`。
- 允许当前应用需要的 HTTP 方法，包括 `GET`、`HEAD`、`OPTIONS`、`PUT`、`DELETE`、`MOVE` 等文件操作方法。
- 放行 `/tag-api/*`、大文件上传下载、Range 请求以及可选 `/terminal` 的 WebSocket。
- 明确源站证书校验方式。当前 `tls internal` 不具备通用可移植性；目标方案应改用 EdgeOne 可验证的源站证书，或者明确配置受控的回源 TLS 策略。
- 对动态 API、认证页面和文件写操作关闭不合适的缓存；静态前端资源可以缓存。

### `vps-direct` 必需配置

服务器内：

- Podman 只启动核心 Compose；不加载 `compose.ddns.yaml`。
- Caddy 直接监听 `80/443`，使用公开域名自动申请和续期受信任证书。
- 不使用家庭环境的 `5006/5008/5009` 原站入口，也不信任 EdgeOne 专用代理网段。
- 如果使用 rootless Podman，需要提前解决低位端口绑定；或者由宿主机防火墙/systemd 把 `80/443` 转发到容器高位端口。
- 只开放 SSH、HTTP 和 HTTPS 等明确需要的端口，DUFS、Tag Server、Authelia 的内部端口不发布到公网。

DNS：

- 公共域名的 A 记录指向 VPS 固定 IPv4。
- VPS 有固定 IPv6 时再添加 AAAA。只有 A 记录时可服务 IPv4 和双栈客户端，但不能保证没有 NAT64 的纯 IPv6-only 客户端访问。
- 如果 VPS 只有 IPv4、又必须保证纯 IPv6-only 客户端也能访问，需要为 VPS 增加 IPv6，或者给 VPS 入口也接入 CDN；这不改变 DDNS-Go 仍然不需要的结论。
- DNS 直接指向 VPS，不需要原站域名，也不需要 DDNS-Go。

认证和路由：

- Authelia cookie、redirect URL、WebAuthn RP 信息使用 VPS 的公开访问域名。
- 主站继续由 Authelia 保护。
- 是否启用独立只读域名由 `ENABLE_READONLY` 决定；启用时增加对应 DNS 和 Caddy 站点。
- VPS 默认不提供局域网专用的 `5006` 入口。

## 迁移范围

核心容器栈：

- `caddy`
- `dufs-lan`
- `tag-server`
- `authelia`

按需启用的容器或服务：

- `dufs-readonly`：需要保留当前独立只读 `work` 入口时启用。
- `ddns-go`：仅 `home-ipv6-cdn` Profile 启用。
- `ttyd`：需要重现宿主机开发环境时保留为宿主机服务，通过 Unix socket 交给容器 Caddy 反代。

建议继续留在宿主机/Nix 侧的内容：

- shell/editor/terminal 配置
- 桌面和输入法相关服务
- 开发工具链

明确不迁移：

- `rclone-mount`：原 S3/R2 FUSE 挂载已经停用，容器栈不依赖它。
- tunnel：当前机器没有运行或配置隧道服务，本次迁移不引入。

目标分工：

- Nix/Home Manager 管理宿主机用户环境。
- Compose/容器管理对外访问的服务。

## 本机原地切换

当前第一阶段目标是在同一台家庭服务器上，把应用服务编排从 Home Manager/Nix user services 切换为 Podman Compose；开发终端仍由宿主机管理，不更换机器、域名、端口和数据目录。

这种情况下不需要复制大部分数据，也不需要重新配置外部平台。新容器直接 bind mount 当前路径：

| 服务 | 可直接复用的当前路径 | 处理方式 |
| --- | --- | --- |
| `dufs-lan` | `~/dufs-lan/`、`/media/liou/` | 保持原挂载路径和读写权限 |
| `dufs-readonly` | `~/dufs/` | 保持原挂载路径和认证规则 |
| `tag-server` | `~/dufs-lan/`、`~/tag_secrets.env` | 直接使用原 workspace、`tag_all.db` 和 `.tag`；secret 文件权限改为 `0600` |
| Authelia | `~/.config/authelia/`、`~/.local/share/authelia/` | 直接复用用户文件、配置和活跃数据库 |
| DDNS-Go | `~/.config/ddns-go/` | 直接挂载为容器 `/root`，保留现有 Web UI 配置和 token |
| dufs-plus | `~/dufs-lan/dist/` | 直接挂载给 Caddy，不复制 |
| Caddy data | `~/.local/share/caddy/` | 映射为 `/data/caddy`，保持当前目录布局并保留内部 CA 和源站证书 |

仍需改写但不需要人工重新填写的部分：

- Caddyfile：宿主机的 `127.0.0.1:5005/5007/8081/9091` 要改成 Compose 服务名，静态目录改成容器内路径。
- Compose：把当前端口、挂载和启动参数转换为服务定义。
- 可信代理：由 Caddy 校验 EdgeOne 和转发头；Authelia 4.39 没有当前 Nix 配置所写的 `AUTHELIA_SERVER_TRUSTED_PROXIES` 变量，新方案不再传入这个无效变量。
- secret 注入：复用现有值，但不再把密码放进进程参数；由 secret 文件只读挂载。
- ttyd：继续使用宿主机 Nix 的 bash、zellij 和 PATH，监听 `%t/ttyd/ttyd.sock`；Caddy 只读挂载 socket 目录，不开放宿主机 `7681` 端口，现有 zellij 会话可继续复用。

原地切换且保持域名和端口不变时，以下配置不需要重做：

- EdgeOne 加速域名、回源域名、回源端口和缓存规则。
- DNS 和 DDNS 服务商记录。
- 家庭路由器 IPv6 防火墙与端口放行。
- 浏览器 localStorage、Authelia cookie、TOTP 和 WebAuthn 注册。

不过仍应把这些外部配置记录进 `instance.toml`，用于验证现有配置与目标模板一致，而不是在切换时修改它们。

### 原地切换约束

相同路径、端口和数据库不能同时由旧、新两套服务写入：

1. 先使用临时目录和临时端口验证新 Compose 模板。
2. 正式切换前停止旧 Caddy、Tag Server、Authelia、DDNS-Go 和两个 DUFS。
3. 对 Tag SQLite 执行 checkpoint/一致性备份。
4. 新 Compose 使用原路径启动。
5. 验证成功后禁用旧 Home Manager 服务，防止下次登录或 Home Manager switch 后抢占端口。

DDNS-Go、Authelia、Tag SQLite 和 Caddy data 尤其不能由旧、新容器同时使用。

## 服务风险等级

| 服务 | 风险 | 说明 |
| --- | --- | --- |
| `ddns-go` | 低 | 当前已经是 Home Manager 管理的容器。主要风险是丢失或覆盖现有 DDNS 配置/token。 |
| `authelia` | 低到中 | 当前已经是容器。主要风险是 secret/config 路径变化，以及 Caddy forward-auth 登录循环。 |
| `dufs-lan` | 低到中 | 当前已经是容器。主要风险是数据卷路径、UID/GID 权限、认证参数。 |
| `tag-server` | 中 | 当前已经是容器。主要风险是 ARM64 镜像构建、数据库路径、workspace 路径、外部命令依赖。 |
| `caddy` | 中到高 | 当前是宿主机 Nix 包 + systemd user service。它是公网入口，路由配置错误会导致整套服务不可访问。 |
| `ttyd` | 中 | 可选且敏感。涉及 shell/zellij/session 行为和权限控制。 |
| `dufs-readonly` | 低到中 | 当前有独立目录、认证和公网入口，不能和可写实例误用同一权限配置。 |

整体风险判断：

- 临时端口并行测试：低风险。
- 切换正式 `80/443` 入口：中风险。
- 正式入口、数据路径、认证、DNS 同时切换：中高风险。

## 主要风险点

### 1. 端口冲突

旧 Home Manager 服务和新容器不能同时绑定同一端口。

需要重点关注的端口：

- `80`
- `443`
- `5006`
- `5007`
- `8081`
- `9091`
- `7681`

建议先让新容器栈跑在临时端口，完整验证后再切换正式端口。

### 2. Caddy 路由顺序

Caddy 路由顺序非常关键。

期望行为：

- 带 `?json` 的请求转发给 `dufs`。
- `/tag-api/*` 转发给 `tag-server`。
- `dist/` 里存在的静态文件由 Caddy 直接服务。
- 其它请求回落到 `dufs`。

常见错误：

- 文件列表失败，因为 `?json` 被前端静态入口处理了。
- 标签功能失败，因为 `/tag-api` 被转发到 `dufs`。
- 上传/下载失败，因为 fallback 路由错误。
- 首页正常，但嵌套路径、文件 API 或下载异常。

### 3. Authelia forward-auth

Authelia 应该保护 `dufs`、`dufs-plus`、`/tag-api`，以及可选的 `ttyd`。

但不能让 Authelia 自己的认证接口也被错误保护，否则会产生登录循环。

常见错误：

- `/authelia/*` 被 Authelia 自己保护。
- 浏览器登录后反复跳转。
- `OPTIONS` 预检请求被拦截。
- 认证后 `PUT` 上传失败。
- `ttyd` WebSocket 缺少 upgrade header，导致终端无法连接。

### 4. 数据卷路径一致性

`dufs` 和 `tag-server` 必须看到同一份 workspace 数据。

容器内路径可以不同，例如：

- `dufs` 使用 `/data`
- `tag-server` 使用 `/workspace`

但它们应该映射到宿主机同一个目录，例如：

- `/mnt/ssd/dufs-lan/data`

如果两者看到的不是同一份文件，标签、阅读进度、PDF 渲染、文件操作都会出现不一致。

### 5. SQLite 和 sidecar 写入

正式环境里只能有一个 `tag-server` 写同一个数据库。

重要状态包括：

- `tag_all.db`
- `tag_all.db-wal`
- `tag_all.db-shm`
- `.tag` sidecar 文件
- `.dufs_plus_metadata/`

正式切换时，不要让旧 `tag-server` 和新 `tag-server` 同时写同一个 `tag_all.db`。

### 6. 文件所有权和权限

容器化后，`dufs` 上传文件、`tag-server` 写 `.tag` 文件时，写入 UID/GID 可能和旧服务不同。

可能症状：

- 上传后的文件宿主机用户无法修改。
- `.tag` 文件写入失败。
- SQLite 数据库无法打开或写入。
- Caddy 无法写证书或配置状态。

切换前需要验证这些目录的写权限：

- 数据 workspace
- tag 数据库目录
- Caddy data/config 目录
- Authelia config/data 目录
- DDNS 配置目录

### 7. 外部命令依赖

`tag-server` 的部分功能依赖外部命令。

当前 `tag-all/Containerfile` 已安装：

- `git`
- `ffmpeg`
- `poppler-utils`
- `mupdf-tools`

这些依赖用于 git 文件读取、缩略图、视频时长分析、PDF 页面渲染等功能。

如果以后重做 runtime 镜像，必须保留这些工具。

### 8. 树莓派性能

普通文件列表和标签 CRUD 在 Pi 4/5 + SSD 上应该问题不大。

风险较高的是：

- PDF 渲染
- 视频缩略图/时长分析
- 大目录扫描
- 大量 `.tag` sidecar 读取

常规运行中不建议在树莓派上编译 `dufs-plus`、`bevy-sketch` 或 `tag-server`。应在其它机器构建产物/镜像后部署到树莓派。

### 9. DDNS 切换

`ddns-go` 本身资源占用很低，但配置错误会直接导致外网域名不可用。

它只在 `home-ipv6-cdn` Profile 中启动。`vps-direct` 不创建该容器，也不要求存在 DDNS 配置。

迁移前备份现有配置：

- `.ddns_go_config.yaml`

保留旧配置，方便回滚。

### 10. TLS 和证书状态

Caddy 容器化后，证书存储位置会改变。

需要持久化：

- Caddy `/data`
- Caddy `/config`

迁移后首次启动时，Caddy 可能会重新签发证书。此时 DNS 和端口转发必须已经指向新服务，否则证书签发可能失败。

不同入口模式的 TLS 终止点必须明确：

- `home-ipv6-cdn`：EdgeOne 提供客户端侧证书；EdgeOne 到原站的 TLS 和证书校验方式需要单独配置。
- `vps-direct`：由本机 Caddy 申请和续期公网证书。
- CDN/代理回源：必须配置可信代理网段，并验证真实客户端 IP，不能无条件信任任意 `X-Forwarded-*` 请求头。

### 11. 可移植路径和额外挂载

当前配置包含 `/home/liou`、`/media/liou`、固定域名和固定远端地址，不能原样部署到另一台服务器。

至少要参数化：

- `DUFS_DATA_DIR`
- `READONLY_DATA_DIR`
- `MEDIA_DIR`，可为空
- `TAG_DB_DIR`
- `DIST_DIR`
- `AUTHELIA_CONFIG_DIR`
- `AUTHELIA_DATA_DIR`
- `CADDY_DATA_DIR`
- `CADDY_CONFIG_DIR`
- 主域名、只读域名、Authelia 外部 URL
- 容器运行 UID/GID

`dufs-lan` 和 `tag-server` 必须用同一个宿主机路径映射到各自 workspace。额外的 `/media` 挂载应是可选项，不能假设每台服务器都存在。

### 每台新服务器需要填写的实例配置

通用非敏感配置写入实例自己的 `.env`：

| 配置 | 说明 |
| --- | --- |
| `DEPLOY_PROFILE` | `home-ipv6-cdn` 或 `vps-direct` |
| `PUBLIC_HOST` | 用户访问的主域名 |
| `READONLY_PUBLIC_HOST` | 可选的只读域名 |
| `ORIGIN_HOST` | 仅家庭 Profile 使用的主原站域名 |
| `READONLY_ORIGIN_HOST` | 仅家庭 Profile 使用的只读原站域名 |
| `DUFS_DATA_DIR` | 可写文件根目录 |
| `READONLY_DATA_DIR` | 可选只读文件根目录 |
| `MEDIA_DIR` | 可选的额外媒体目录 |
| `TAG_DB_DIR` | Tag Server SQLite 目录 |
| `DIST_DIR` | 已构建的 dufs-plus 前端目录 |
| `AUTHELIA_CONFIG_DIR` / `AUTHELIA_DATA_DIR` | Authelia 配置和状态目录 |
| `CADDY_DATA_DIR` / `CADDY_CONFIG_DIR` | Caddy 证书和状态目录 |
| `PUID` / `PGID` | 容器写文件使用的宿主机 UID/GID |
| `ENABLE_READONLY` | 是否启用独立只读 DUFS |
| `ENABLE_TERMINAL` | 是否接入宿主机 ttyd Unix socket；目标机没有对应开发环境时关闭 |

每台服务器单独生成、权限设为 `0600` 的 secret：

- Authelia JWT、session、storage encryption key。
- Authelia 用户密码 hash。
- Tag Server 所需的环境变量。
- 独立只读 DUFS 的认证信息。
- 家庭 Profile 额外需要 DNS 服务商 token 和 DDNS-Go 管理密码。

部署前还需要准备：

- 与目标架构匹配的固定版本容器镜像。
- dufs-plus 的 `dist/`，包括其引用的其它前端产物。
- workspace 数据、Tag Server SQLite 和元数据的一致性备份。
- Authelia 用户、TOTP/WebAuthn 状态的迁移或重新注册方案。
- DNS 控制权；家庭 Profile 还需要 EdgeOne 站点的配置权限。

### 当前运行时状态迁移清单

以下内容不是只靠 Compose 和 Nix 声明就能重建的：

| 内容 | 当前来源 | 重要性 | 迁移方式 |
| --- | --- | --- | --- |
| DDNS-Go 网页配置 | `~/.config/ddns-go/.ddns_go_config.yaml` | 家庭 Profile 必需 | 复制到新持久化目录，然后检查新服务器网卡名、IPv6 获取方式、域名和 token |
| Authelia 用户配置 | `~/.config/authelia/users_database.yml` | 必需 | 转为 secret 文件或从单一实例配置生成 |
| Authelia TOTP/WebAuthn 状态 | `~/.local/share/authelia/db.sqlite3` | 必需，否则重新绑定二次认证 | 连同原 storage encryption key 一起迁移 |
| Authelia 主配置 | `~/.config/authelia/configuration.yml` | 可重建 | 从实例配置生成；不要误用 `~/.config/authelia/db.sqlite3` 这份旧数据库 |
| Tag Server 索引 | workspace 根目录的 `tag_all.db` | 必需 | 停止旧 Tag Server 后做 SQLite 一致性备份；不能只在 WAL 活跃时复制主 DB |
| 标签、阅读进度、缩略图和媒体时长 | workspace 中隐藏的 `.*.tag` sidecar | 必需 | 连同整个 workspace 复制，不能使用忽略隐藏文件的同步参数 |
| PDF 服务端渲染缓存 | `.dufs_plus_metadata/pdf_cache/` | 可选，当前约 503 MiB | 可复制以避免重新渲染，也可以删除后自动重建 |
| Tag Server 外部 API key | `~/tag_secrets.env` | 对应功能需要 | 迁入 secret；当前只有 `DEEPSEEK_API_KEY` 键 |
| Caddy 内部 CA 和源站证书 | `~/.local/share/caddy/pki/`、`certificates/` | 家庭 Profile 需要明确处理 | 推荐重新设计为 EdgeOne 可验证的源站 TLS；若要保持现状则必须迁移 Caddy data |
| Caddy 路由 | Nix 生成的 Caddyfile | 可重建 | 从实例配置和 Profile 模板生成 |
| 只读 DUFS 数据 | `~/dufs/` | 启用只读站时必需 | 复制目录并重新注入认证 secret |
| dufs-plus 前端 | `~/dufs-lan/dist/` | 必需 | 重新构建或复制完整目录，包含 Bevy/WASM 产物 |

当前状态规模可用于迁移后核对：

- Tag 数据库约有 2337 个 item、30 个 tag、544 条 item-tag 关系和 21 条 tag 层级关系。
- workspace 内约有 83 个 `.tag` sidecar。
- Authelia 当前有 1 个 TOTP 配置、2 个 WebAuthn 凭据和 1 份用户二次认证偏好。
- Tag SQLite 当前使用 WAL，主库约 652 KiB，WAL 约 4 MiB。

迁移 Authelia 时必须保留原 `authelia_storage_key` 才能读取已有加密状态。可以轮换 session secret 并让所有会话重新登录，但 storage encryption key 不能直接当普通密码替换。WebAuthn 还绑定公开域名：保持相同 `PUBLIC_HOST` 可以继续使用；更换域名通常需要重新注册凭据。

### 浏览器端状态

dufs-plus 使用浏览器 `localStorage` 保存：

- `dufs-plus-recent-move-directories`：最近使用的 5 个移动目标目录。
- `pdf_crop_cache_v2::<path>`：PDF 自动裁边结果缓存。
- `pdf_position::<path>`：PDF 旧位置缓存。

正式阅读进度通过 Tag Server 写入文件旁的 `.tag` sidecar，不依赖浏览器缓存。

如果迁移后继续使用相同公开域名，原浏览器的这些 localStorage 数据仍在；如果更换域名，它们不会自动跟随。丢失它们只会导致最近目录消失、PDF 重新计算裁边或重新取得服务端进度，不会丢失标签数据库和正式阅读进度。

Authelia 登录 cookie 也是按域名保存的。迁移或轮换 session secret 后，已有浏览器通常需要重新登录；只要 Authelia 数据库、storage key 和公开域名保持一致，就不需要重新绑定 TOTP/WebAuthn。

### 本机无法自动读取的外部配置

这些设置存在服务商或路由器控制台中，当前仓库和容器无法完整导出，切换前需要人工记录：

- DNS 服务商：原站 AAAA、CDN 接入记录/CNAME、TTL、解析线路和代理状态。
- DDNS-Go：虽然本机配置可复制，但新服务器的接口名和 IPv6 匹配规则可能不同，必须在其 Web UI 中复核。
- EdgeOne：加速域名、回源域名与端口、Host header、SNI、源站证书校验、缓存规则、允许的 HTTP 方法、Range、大文件限制和 WebSocket。
- 家庭路由器：新服务器的 DHCP/静态租约、IPv6 入站防火墙、`5008/5009` 放行规则和来源限制。更换机器后 MAC/IPv6 地址变化，旧规则不会自动迁移。
- VPS 提供商：安全组、防火墙、固定 IPv4/IPv6 和反向代理之外的端口限制。

部署清单应要求为这些控制面保存截图或导出文件，并把预期值写入 `instance.toml` 供 preflight/smoke test 验证。

### 当前 secret 需要整改

现有 secrets 由 git-crypt 工作区、Nix 插值和独立 env 文件共同管理；其中部分值会出现在进程参数里，而且若干敏感文件当前权限不是 `0600`。

切换到 Podman 应用栈时：

- 不直接复制当前启动参数。
- 将 DDNS token、DUFS 认证、Authelia secrets 和 Tag Server API key 写入独立 `0600` secret 文件。
- 迁移完成后轮换已经可能暴露的 DDNS 管理密码、DUFS 密码和 session/JWT secret。
- Authelia storage encryption key 先保持不变以迁移数据库；如需轮换，必须按 Authelia 支持的迁移方式单独执行。

### 12. 镜像、架构和版本

目标服务器可能是 x86_64 或 ARM64。`tag-server` 必须提供对应架构镜像，或者构建多架构镜像；不能把本机镜像直接当成通用产物。

正式配置不应长期使用 `latest`。应记录并固定：

- Caddy
- Dufs
- Authelia
- ddns-go
- tag-server

部署流程同时支持从镜像仓库拉取和离线 `podman load`，并在部署前检查目标架构。

### 13. Rootless Podman 和启动管理

目标以 Podman 为主，Compose 文件保持 OCI/Docker Compose 兼容。需要明确：

- rootless 容器如何绑定 `80/443`，或改由宿主机端口转发到高位端口。
- 用户退出后服务仍可运行所需的 linger 配置。
- 使用一个 systemd user unit 调用 `podman compose up/down`，或生成 Quadlet；不能只依赖人工执行。
- 内部服务只加入容器网络，不发布到公网；管理端口最多绑定到 `127.0.0.1`。

### 14. Secret 管理

仓库只提交 secret 模板和变量名，不提交真实值。

敏感信息通过权限为 `0600` 的宿主机文件、Podman secrets 或只读挂载注入，包括：

- Dufs 认证信息
- Tag Server 环境变量
- Authelia session/storage/JWT secret 和用户数据库
- DDNS DNS 服务商 token

启动脚本需要先检查 secret 是否齐全，日志和状态检查不能打印真实值。

### 15. 健康检查、备份和恢复

Compose `depends_on` 只能表达启动顺序，不能证明依赖已经可用。核心服务需要健康检查，Caddy 应在 upstream 可用后再接受正式流量。

备份至少覆盖：

- `tag_all.db` 及一致性快照
- `.tag` sidecar
- `.dufs_plus_metadata/`
- Authelia 数据和用户配置
- Caddy 状态
- DDNS 配置

除了备份命令，还必须有一次在空目录中的恢复演练。

## 目标配置结构

建议最终交付以下文件：

```text
compose.yaml                 # 核心：caddy、dufs-lan、tag-server、authelia
compose.readonly.yaml        # 可选：只读 dufs 和只读域名路由
compose.ddns.yaml            # 可选：ddns-go
宿主机 ttyd user unit        # 可选：完整宿主机开发环境，经 Unix socket 接入
.env.example                 # 非敏感路径、域名、UID/GID
.env.home-ipv6-cdn.example   # 家庭 IPv6 + EdgeOne 模板
.env.vps-direct.example      # 公网 VPS 模板
secrets/README.md            # secret 文件名、权限和生成方式
caddy/common.Caddyfile       # 两种 Profile 共用的应用路由
caddy/home-ipv6-cdn.Caddyfile
caddy/vps-direct.Caddyfile
authelia/                    # 可参数化模板，不包含真实 secret
scripts/preflight.sh         # 路径、端口、架构、权限、secret 检查
scripts/up.sh                # 根据 DEPLOY_PROFILE 组合 compose 文件
scripts/backup.sh
scripts/restore.sh
scripts/smoke-test.sh
```

示例选择逻辑：

```text
DEPLOY_PROFILE=home-ipv6-cdn -> core + home Caddy + ddns
DEPLOY_PROFILE=vps-direct    -> core + VPS Caddy
ENABLE_READONLY=1            -> 再叠加 readonly
ENABLE_TERMINAL=1            -> 挂载并反代宿主机 ttyd Unix socket
```

`ddns-go` 的 provider、域名和 token 保存在服务器自己的持久化配置中。复制核心容器栈到有固定公网 IP 的服务器时，不需要创建或启动它。

## 推荐迁移步骤

1. 把现有域名、端口、数据目录、额外挂载、secret 和服务开关整理到实例配置。
2. 选择 `home-ipv6-cdn` 或 `vps-direct`，先完成 IPv6/CDN 或公网 `80/443` 连通性预检。
3. 构建与目标 CPU 架构匹配、固定版本的镜像。
4. 使用临时端口和复制出来的数据启动核心栈，不直接操作正式数据。
5. 根据实例需要叠加只读 DUFS、DDNS，并决定是否接入宿主机 ttyd。
6. 验证完整路由、认证、写入、阅读元数据、媒体处理和备份恢复。
7. 暂停旧 Tag Server，做 SQLite 一致性备份并完成最终数据同步。
8. 停止旧入口，切换 DNS 或端口映射，再启动正式容器栈。
9. 完成外网和局域网 smoke test；观察日志、健康状态和资源占用。
10. 保留旧服务但禁止自动启动，经过稳定观察期后再清理。

## 切换前检查清单

切换前验证这些路径：

- `/`
- `/?json`
- `/tag-api/tags`
- `/tag-api/items?path=/`
- `/tag-api/items/progress`
- 文件上传 `PUT`
- 文件重命名/删除
- PDF 页面渲染
- 视频播放
- Authelia 登录/登出
- 受保护的 `/tag-api` 访问
- 可选：`ttyd` WebSocket 路由

切换前验证这些运行项：

- Caddy 日志显示请求进入预期 upstream。
- `tag-server` 日志显示正确 workspace 路径。
- `dufs` 可以写入上传文件。
- `tag-server` 可以写入 `.tag` 文件。
- SQLite 数据库可以打开并 checkpoint。
- `vps-direct` 确认没有创建或启动 DDNS-Go。
- `vps-direct` 从 IPv4 网络可访问公开域名；配置了 AAAA 时再从独立 IPv6 网络验证。
- `home-ipv6-cdn` 确认 DDNS-Go 只更新正确的原站 AAAA。
- `home-ipv6-cdn` 在公网 IPv6 变化后，原站域名和 EdgeOne 回源能自动恢复。
- `home-ipv6-cdn` 从仅 IPv4 和仅 IPv6 的客户端都能通过 CDN 域名访问。
- `home-ipv6-cdn` 确认公网无法访问局域网端口 `5006`。
- CDN 没有缓存 Authelia、Tag API、目录 JSON 和文件写操作响应。
- 大文件 Range 下载、上传、重命名、删除和可选 WebSocket 均能穿过 CDN。
- 备份脚本覆盖数据库、sidecar 和认证配置。
- 在空目录完成过一次恢复。
- 重启宿主机后容器栈能自动恢复。
- 日志、`podman inspect` 和 systemd 状态中没有出现明文 secret。

## 回滚计划

切换前记录旧服务状态：

```bash
systemctl --user status caddy
systemctl --user status podman-dufs-lan
systemctl --user status podman-tag-server
systemctl --user status podman-authelia
systemctl --user status podman-ddns-go
```

切换时停止旧服务：

```bash
systemctl --user stop caddy
systemctl --user stop podman-dufs-lan
systemctl --user stop podman-tag-server
systemctl --user stop podman-authelia
systemctl --user stop podman-ddns-go
```

回滚时：

```bash
python3 deploy/scripts/manage.py down
systemctl --user start podman-ddns-go
systemctl --user start podman-authelia
systemctl --user start podman-tag-server
systemctl --user start podman-dufs-lan
systemctl --user start caddy
```

`manage.py` 会使用本实例生成的完整 Compose 文件列表，避免手工遗漏 profile override。

## 推荐最终拓扑

只有 Caddy 应该直接暴露到公网。

```text
Internet / CDN
  -> Caddy
    -> Authelia forward_auth
      -> dufs-lan
      -> /tag-api -> tag-server
      -> 可选只读域名 -> dufs-readonly
      -> 可选 /terminal -> Unix socket -> 宿主机 ttyd/Nix/zellij
```

内部服务不应该直接暴露公网端口。

推荐 compose 服务列表：

- `caddy`
- `authelia`
- `dufs-lan`
- `tag-server`
- 可选：`dufs-readonly`
- `home-ipv6-cdn` Profile：`ddns-go`
- 可选宿主机服务：`ttyd-compose`
