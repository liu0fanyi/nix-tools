# tag-server 打包选择契约

产品需求权威源：PC `/data/project/tag-all/specs/023-nix-full-rollout/`；本文件只管理发布器。

- CLI `--tag-packaging alpine|nix` 默认 alpine；nix 只接受 `--target nuc` + tag-server/all。
- Alpine 原构建/传输和 Aliyun 摘要校验不变；Nix 只调用 PC build-nix private，不能调用产品 deploy。
- 每次生成唯一 release 标签；成功报告必须绑定该标签、Nix store 归档 SHA256、单镜像
  manifest RepoTags 和实际配置字节摘要。完整 private/worker 探针通过且模型未打包。
- 传输前重新核对归档，备份失败不激活；直接 gzip 解包→zstd→SSH→Podman load，
  再核对 NUC 配置摘要。无默认 PC Podman 导入/reset/migrate/prune。预演不执行或读取旧报告。
- 目标为主后端、启用的 readonly、启用的 peer discovery。所有旧目标必须同镜像，
  否则在标签/服务变更前拒绝；保留旧 image ID 及 rollback 标签。
- 全部目标镜像摘要 + 后端 /tags + discovery 运行容器/CLI + 代理 smoke 成功才算激活。
- 失败恢复旧生产标签，逐个尝试全部服务，即使单项失败也继续；复核旧摘要和代理。
  未完整恢复明确失败并保留原异常与未恢复项；不自动恢复数据库/身份/前端/模型。
- 原用户、挂载、只读拒写、签名/CA/SSH 主机校验不变，不向 Aliyun 发送私有归档。

## 验证

发布器单测覆盖默认/非法目标与组件/零执行预演/新鲜标签/SHA与配置摘要/备份失败阻断、
第三服务失败/部分重建失败/旧镜像分裂拒绝/所有服务回滚和回滚中单项失败仍继续。
真实 NUC 结果单独记录在产品 023，单测通过不代表已部署。
