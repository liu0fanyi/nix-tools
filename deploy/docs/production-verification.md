# 统一 just 流程生产发布验收（2026-09-05）

## 2026-09-07 录音联删精确路由

按用户单独授权，LAN 与 nas 公网仅新增 DELETE
`/device-api/v1/transcriptions/by-key/*`，继续由后端 transcriptions 令牌权限校验。
不修改设备密钥，不放开通配写入。30项 deploy 测试通过，相对生产 render.py 仅此两处路由。
通过 just manage backup/config/recreate caddy 激活；备份为
`20260907-161731-534597432`。Caddy 配置验证通过；Compose 停止超时后结束旧代理，
新代理及只读网关恢复。LAN 与公网匿名 DELETE 均401，根入口302、Authelia200。
未发送带权限的真实录音删除请求；后端发布和实机进度见 tag-all 录音联删文档。

## 2026-09-07 目录排序精确写路由

按用户授权在LAN与nas公网音乐POST matcher增加 `/device-api/v1/music/order`，
继续由后端music设备令牌权限校验；未开放通配写入，不修改密钥或音乐文件。
对比现网render.py仅两行路由变化，51项测试通过。通过既有just manage
backup/config/recreate caddy/smoke流程启用，未升级整套基础镜像。
配置备份 `20260907-151357-642249916`。Caddy停止超过10秒后Compose强制结束旧进程，
新Caddy及联动只读网关已正常恢复；根入口302、Authelia200；LAN及公网匿名POST均401。
后端与App发布进度以tag-all目录排序文档为准，路由启用不等于端到端排序验收。

## 2026-09-07 播放列表精确写路由

按用户授权在 LAN 与 nas 公网入口的音乐 POST matcher 中增加
`/device-api/v1/music/playlists`，沿用后端 music 设备令牌校验，未放开音乐通配写入。
51项发布工具测试通过。经既有 just manage backup/render/recreate caddy/smoke 管理流程
更新，仅同步 render.py；没有拉取升级整套基础镜像。配置备份：
`20260907-131003-907255742`。Caddy及联动只读网关恢复，根入口302登录、Authelia200；
LAN及真实公网域名匿名列表POST均为401，公网TLS校验开启。初次直连源站HTTPS curl因
本机CA链校验失败未取得状态，不能计为该直连测试通过。
后端播放列表版本的部署结果另见 tag-all 音乐文档。

本记录为本轮最新状态，取代此前“仅构建/预演、尚未生产发布”的阶段说明。

## 执行结果

在 PC `/home/liou/nix-tools` 的宿主 rootless Podman 环境分别执行：

```bash
devenv shell -- just deploy nuc all
devenv shell -- just deploy aliyun all
```

两端均成功完成本机构建、测试、备份、基础镜像传输、后端激活、基础设施应用、
前端上传及 smoke。NUC 与阿里云均不编译产品，没有执行 NixOS switch。

| 场景 | 验收 |
| --- | --- |
| NUC 5006，dufs-lan | 匿名 401；认证后读 API、静态资源正常；临时文件 PUT/GET/DELETE 成功；完整工具入口保留 |
| NUC 5008，dufs | 匿名 401；认证后只读；PUT 被拒绝，tag-api POST 返回 405；私有工具 URL 返回 404 |
| 阿里云源站及 www.wttliou.top | 匿名读取正常；源站拒绝文件与标签写入；公网 CDN 私有工具 URL 返回 404 |

每个源站检查了 8 个入口引用的 JS/WASM/CSS 文件，与服务器产物 SHA-256 一致；
发布器另用 rsync checksum 比对 PC 与远端产物，并核对阿里云 CDN 首页内容哈希。
三个场景均用真实 Chromium 浏览器加载：能力配置正确，游戏/画板/设备/转写/项目入口
只在可写站可见，只读站不加载画板 iframe，未出现 JavaScript pageerror。
只读测试上下文预设旧 board 本地偏好，仍不会加载画板。浏览器未保存认证信息或截图。

只读直达检查覆盖 devices、transcriptions、recorder-bean、bevy-sketch、bevy-game、
project-planner，包含 `/dist/` 和根路径别名；另检查 terminal。阿里云 CDN 的 12 个
应用 index 路径也均返回 404。NUC 临时读写测试文件已删除；只读写入尝试未创建文件。

## 发布产物与恢复依据

- 两端 index.html：`be8537e3f916d7162d55bb83c8be4c641ead12e894a5cb8cfbf23bb7f53c28ae`。
- NUC 后端：`localhost/tag-server:release-20260905T142532777137Z`，镜像
  `da887616503d21015614d03acbd51980318d1e0244383dfba4957b1607becdc8`，读写两个服务一致。
  rollback 标签为 `localhost/tag-server:rollback-20260905T142532777137Z`。
- 阿里云后端：`localhost/tag-server:release-20260905T143352295321Z`，配置摘要
  `a30186c532cd47271ff94e302fadb01ccc4c935a78b8d15117a23786ee98d980`；Docker 29 运行 ID
  `d418c3c11a149c9d4108abf602c494cfdcf2d3cc16a4b954c247d086034b7140`。
  rollback 标签为 `localhost/tag-server:rollback-20260905T143352295321Z`。
- NUC 数据/配置备份：`/home/liou/.local/state/dufs-plus/backups/dufs-plus/20260905-222547-136779725`；
  前端备份：`/home/liou/.local/state/dufs-plus/frontend-backups/frontend-c03y2IhN.tar`。
- 阿里云数据/配置备份：`/root/.local/state/dufs-plus/backups/nix-tools/20260905-223406-631034338`；
  前端备份：`/root/.local/state/dufs-plus/frontend-backups/frontend-g9g3etO4.tar`。

NUC 后端保留 Whisper，阿里云后端不包含 Whisper。公开前端构建不含三个私有管理应用；
旧静态文件和 Bevy 目录不通过删除清理，而由只读路由阻止访问。没有同步私有数据或密钥。
NUC Bevy 三目录发布前后整体文件摘要均为
`97fc4f1e456ded075b7c4a51aa3e994e5d58f1b8c01d9bbbfff207b0cf59f26e`。
阿里云 signature-server、stt-bridge、mosquitto、my-postgres 未重启或更新。

## 实际发布发现并修正的问题

1. DUFS 配置标签缺少 v：`sigoden/dufs:0.46.0` 拉取失败，改为官方存在的 `v0.46.0`。
   PC 拉取后镜像 ID 与 NUC 原运行镜像一致，未升级版本。首次失败发生在容器切换前。
2. Docker 29 containerd 存储返回 manifest ID，不能直接与 Podman 配置 ID 比较。
   不一致时导出 Docker 镜像，计算实际配置字节 SHA-256 并与 PC ID 比较；配置绑定层 diff IDs。
   校验通过后使用远端运行 ID 激活和验收。错误配置摘要仍拒绝，Podman 仍要求 ID 相等。
   首次校验失败时未切换阿里云服务，修正后完整重试成功。
3. 只读静态目录还可通过根路径别名访问，补齐与 `/dist/` 相同的拦截及回归测试。

最终 30 项 Python/just 回归测试通过。前端及后端 release 构建/测试通过；存在已有的
未使用变量/函数及 Browserslist 数据过期提示，不影响本次构建和浏览器验收。

## 边界

本轮验证发布流程和访问权限，不替代文件移动/元数据修复等专项业务回归。
NUC Compose 联动重建代理的行为仍存在，已验证切换后恢复；发布并非多组件原子事务。
镜像回滚有故障注入测试，但本轮未故意制造生产激活故障；数据库不会自动回退。
