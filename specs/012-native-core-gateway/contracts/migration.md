# 安装与迁移预演契约

- `just check-native-install <tag-all> <dufs-plus>`：只构建/检查隔离 Home Manager generation；默认无服务，启用组合生成 core/files/gateway、统一工作区/端口，凭证仍为运行期路径。无 activate/switch。
- `just check-native-migration <tag-all>`：仅随机 .devenv/native-migration-* 下的合成数据。核对 023 完整归档及 app/tag-server SHA 和 024 core SHA，不从未验证制品抽取二进制。无生产源/服务参数。
- 迁移演示在自有完整版进程退出后对 SQLite 使用 backup API、核验 integrity_check，元数据同样离线复制；拒绝 symlink/特殊文件与已有目标；mode 700/600。
- 二进制回退保留新写入。旧备份恢复必须显式选择，并且只写全新目录；真实部署不得自动回写旧 DB，失败时保留新状态和备份。
- `just plan-native-pc`：仅固定 dufs-plus-pc 项目只读 container inspect 与部署 TOML。无 --apply、无 DB/密钥内容、无环境/凭证输出、无 stop/copy/activate。实例范围不匹配则拒绝。
- 当前 cutover_ready=false 是实际预检结果；不因合成数据通过而停旧节点。状态文件含真实 PC 路径和摘要，不含业务数据或凭证。
- 当前配置使用身份 pc / 位置 loc_pc / 配对发现 / 远端 CA / 嵌套工作区挂载；迁移前必须逐项保持语义，并在临时节点复验。真实合成双节点签名同步已通过 peer-gateway-results.json；生产任务执行尚未覆盖。

- 配置转换仅内存深拷贝，明确路径字段按最长 bind 目录边界改写；身份、位置 ID、同步配置和未知字段保持。禁止读取 DB/密钥或输出完整配置。
- `TAG_PODMAN_URL` 仅接受当前用户的 `/run/user/<uid>/podman/podman.sock` Unix 服务，不允许任意远端 Podman。
- proposed_native_sync_enabled 只是候选配置意图，不代表原生服务已启用。cutover_ready 仍为 false。
- 现用 internal CA 必须同时保持信任根与自动续期；只引用旧叶证书不足以满足迁移契约。
