# nix-tools 发布文档

[最新：两端生产发布与三个访问场景验收](docs/production-verification.md)

[构建发布命令与工程约束（根部 AGENTS.md）](docs/build-agent-guide.md)

当前入口：just deploy nuc|aliyun infra|frontend|tag-server|all；config 发布组件已改名 infra。

[PC 发起的 NUC 管理和阿里云发布](docs/pc-release.md)

包含 NUC 密码只读站与阿里云匿名站的工具入口隔离说明。
两端现共用产品构建、传输和激活流程；产品部署命令仅保留为快捷入口。

配置与脚本权威来源：PC `/home/liou/nix-tools/deploy/`。
跨工程计划以 NUC `/home/liou/dufs-lan/todos/` 为准。
