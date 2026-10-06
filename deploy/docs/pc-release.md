# PC 发起发布

在 PC nix-tools 开发环境执行 `just deploy nuc|aliyun infra|frontend|tag-server|all`，必须明确目标，默认组件 infra。完整预演使用 `just -- deploy nuc all --dry-run`，而非 just 自身的 --dry-run。

NUC 单应用可用 `just deploy nuc frontend --frontend-app devices`（或 transcriptions、recorder-bean）；阿里云不接受此参数。

产品只维护 build，部署快捷入口反调 nix-tools；不得在父调度中再次调用产品 deploy。前端保护 Bevy 三目录并保留旧哈希资源，后端摘要不匹配停止，激活失败只尝试旧镜像恢复，不自动回滚数据库或整站。

命令详见 [部署手册](../README.md)，规格见 [基础设施](../../specs/009-infrastructure/spec.md)。

## tag-all Nix 镜像试验边界

用户继续能力分层之后的 Nix dockerTools 试验：产品本机 `just check-nix-core` 先完成
既有 Containerfile 全 tester/core，再组装同一二进制并用 Podman 验收。仅有本机
`nix-trial-baseline` / `nix-core-trial` 标签；规格在 tag-all `specs/020-nix-image-trial/`。
020–022 发布边界仍只接受原 private/public，不接受这些检查镜像或增加新 profile。
该约定不允许服务器构建、生产迁移或挂载数据库/socket，也不改变回滚流程。

## 完整 Nix 私有镜像

产品 023 的完整 private 已通过本机构建/持久化/回退/TLS/Git 验收；已通过原入口部署 NUC；
真实部署与备份/回滚摘要见产品 023 production-results.json，人工 R01–R05 仍待复验。`just -- deploy nuc tag-server --tag-packaging nix --dry-run` 可预演，去掉
`--dry-run` 才发布。默认 `--tag-packaging alpine` 保留；Nix 不用于 Aliyun。

具体发布契约见 [Nix 打包选择](../../specs/009-infrastructure/contracts/tag-packaging.md)。
服务端只加载运行，原数据/SSH/模型挂载及用户不变。发现服务一并切换，旧镜像不同则拒绝；
失败恢复全部目标并检查代理，数据库不自动恢复。
