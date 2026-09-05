# 统一 just 流程生产发布验收（2026-09-05）

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
