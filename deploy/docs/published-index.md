# nix-tools 发布文档

[NUC 重装准备、备份与业务恢复](docs/nuc-migration.md)：业务恢复及修复后整机重启验收通过，保留现有 Art 检查策略。

[设备结构与 NUC 重装适用性审查](docs/host-structure-review.md)

[最新：两端生产发布与三个访问场景验收](docs/production-verification.md)

同页补充2026-09-07音乐播放列表精确POST路由、配置备份与匿名拒绝验收。
另补目录内歌曲排序order精确POST路由、备份和LAN/公网匿名401验收。

[构建发布命令与工程约束（根部 AGENTS.md）](docs/build-agent-guide.md)

当前入口：just deploy nuc|aliyun infra|frontend|tag-server|all；config 发布组件已改名 infra。

[PC 发起的 NUC 管理和阿里云发布](docs/pc-release.md)

包含 NUC 密码只读站与阿里云匿名站的工具入口隔离说明。
两端现共用产品构建、传输和激活流程；产品部署命令仅保留为快捷入口。

配置与脚本权威来源：PC `/home/liou/nix-tools/deploy/`。
跨工程计划以 NUC `/home/liou/dufs-lan/todos/` 为准。
