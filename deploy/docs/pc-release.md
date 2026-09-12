# PC 发起发布

在 PC nix-tools 开发环境执行 `just deploy nuc|aliyun infra|frontend|tag-server|all`，必须明确目标，默认组件 infra。完整预演使用 `just -- deploy nuc all --dry-run`，而非 just 自身的 --dry-run。

NUC 单应用可用 `just deploy nuc frontend --frontend-app devices`（或 transcriptions、recorder-bean）；阿里云不接受此参数。

产品只维护 build，部署快捷入口反调 nix-tools；不得在父调度中再次调用产品 deploy。前端保护 Bevy 三目录并保留旧哈希资源，后端摘要不匹配停止，激活失败只尝试旧镜像恢复，不自动回滚数据库或整站。

命令详见 [部署手册](../README.md)，规格见 [基础设施](../../specs/009-infrastructure/spec.md)。
