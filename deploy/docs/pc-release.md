# PC 发起发布：NUC 与阿里云

最新状态：2026-09-05 两端已实际发布并通过 HTTP、浏览器和产物验收。
见 [生产验收记录](production-verification.md)；下文未发布说明为此前阶段历史。

## 当前统一入口（2026-09-05）

在 PC /home/liou/nix-tools 执行：

```bash
devenv shell -- just deploy nuc infra
devenv shell -- just deploy nuc frontend
devenv shell -- just deploy nuc tag-server
devenv shell -- just deploy aliyun all
devenv shell -- just -- deploy nuc all --dry-run
```

两端均显式指定目标，省略组件一律为 infra。原 config 组件已改名 infra；
管理器内部的 config 子命令仍表示渲染配置，不是发布组件。
旧 devenv release/release-nuc/release-aliyun/manage 包装已删除，运维使用 just manage。
产品构建统一调用 just build private/public；复杂 Python 配置、备份和回滚实现保留。
`just --dry-run` 只显示 recipe；上面的 `just -- ... --dry-run` 才会预演整个发布流程。

迁移验证：28 项 Python/just 入口测试通过，两个目标 all 与 nuc infra 预演、产品前端/后端
及单应用快捷命令转发通过；前端 public/private 实际构建通过。未执行生产部署。
tag-all 的两种 just 构建也完成完整 release 测试，public 镜像 `a30186c532cd`、
private 镜像 `da887616503d`，均在 PC 构建。

源码维护在 `/home/liou/nix-tools`。`just deploy nuc infra` 管理 NUC 基础设施；
`just deploy nuc frontend|tag-server|all` 调用 PC 产品仓库构建脚本，然后统一部署；
`just deploy aliyun all` 在 PC 构建产品产物，发送到阿里云 Docker，应用公开只读配置。
完整操作命令见仓库 deploy/README.md。

NUC 的音乐 manifest、文件下载、上传路由和回归测试已同步回 PC。
两端均由 PC 拉取配置指定的官方基础镜像并传到目标引擎，不从源码编译 Caddy。
阿里云产品脚本使用 public 参数：前端不包含 devices/transcriptions/recorder-bean，
后端 public-runtime 不包含 Whisper CLI，也不依赖 Whisper 构建阶段。
后端 Rust 二进制仍共用，不是 Cargo feature 级裁剪；权限和路由继续限制只读访问。
只读入口还会拒绝旧私有页面 URL，避免历史遗留静态文件继续被访问。
没有把私有数据、设备令牌或模型复制到阿里云。

2026-09-05：19 项 Python 单元测试通过，包括两种目标隔离、NUC 产品委托、
dry-run 不执行命令、强制显式目标、镜像 ID 不匹配中止，以及已有渲染/管理测试。
两条完整发布命令已做 dry-run；本次没有执行生产配置切换或阿里云发布。
阿里云 SSH 预检返回 Host key verification failed，真实发布前须核对并建立可信
主机密钥记录，不使用关闭主机密钥校验的方式绕过。

产品 profile 已实际验证：dufs-plus public/private 两次 release 构建成功，
确认公开版不含三个私有应用、私有版仍完整。tag-all 完整 Alpine release 测试通过，
公开镜像 `76ac92b57500`、私有镜像 `f83cb74a1b0e` 构建成功；无网络临时容器
验证公开版无 Whisper、私有版 Whisper 可执行，两者 tag-server 均可启动帮助命令。

NUC Compose 可能联动重建代理与相关服务，发布期间入口有短暂中断。
两端后端激活失败会尝试恢复旧运行镜像，但不会自动回滚整个站点或数据库。

## 统一调度实现（2026-09-05）

NUC 和阿里云现在共用 release_pc.py 流程，仅构建 profile、远端引擎和服务集合不同。
产品只维护 just build，nix-tools 负责静态备份、传输、校验、
容器激活和验收。两个产品的 just deploy 及前端 just deploy-prod 均是反向调用
nix-tools 的快捷入口；不得从 nix-tools 调用这些入口，避免递归。

NUC 单个静态应用可用 `just deploy nuc frontend --frontend-app devices`（或
transcriptions、recorder-bean）；无需重建 WASM，仍备份并校验。阿里云不允许该选项。
两端前端发布均保护 Bevy 三目录并保留旧哈希资源。NUC 用 rsync 内容校验和源站 smoke，
阿里云另外校验 CDN index 哈希。后端共用 activate_tag.py，NUC 检查并切换两个服务，
阿里云一个；重建或激活 smoke 失败时恢复旧镜像，不自动恢复数据库。

26 项测试覆盖两端流程、备份失败、镜像/架构不匹配和激活回滚。真实只读检查发现 NUC
podman-compose 不支持带服务参数的 ps，已改为两端均支持的标准 Compose 标签查询，
并验证准确返回 NUC 两个、阿里云一个目标容器。本轮尚未执行真实生产切换。

## 只读工具入口补齐（2026-09-05）

NUC 密码只读站和阿里云匿名站共用只读工具限制；NUC dufs-lan 保持完整功能。
除原有 Bevy 游戏限制外，只读路由拒绝 devices、transcriptions、recorder-bean、
bevy-sketch、project-planner 的 `/dist/` 入口及子路径，以及 `/terminal`。
dufs-plus 同时隐藏画板按钮，并将旧 Board 偏好回退为网格，避免加载不可用 iframe。
三种场景由认证和运行能力组合区分，不需要第三份前端构建。

本轮配置回归 20 项通过；未执行生产配置切换，新增路径拦截须发布配置后生效。
Bevy 独立产物不复制、不删除。

同日 SSH 状态更新：用户处理连接后，PC 已用 BatchMode 成功免密连接
`root@47.93.153.102`，确认 `/usr/bin/docker` 和 `/root/nix-tools/deploy` 存在。
此前主机密钥校验阻塞已解除；本次仅做只读检查，未执行生产发布或 HTTP 验收。
