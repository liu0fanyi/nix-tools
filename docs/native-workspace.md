# 原生组合试验：复验与切换边界

规格以 specs/012-native-core-gateway 与 tag-all specs/024-native-core-release 为准。当前可构建与合成预演，不能替换现用 PC 节点。

在 nix-tools devenv shell 中：

```bash
just check-native-install /data/project/tag-all /data/project/dufs-plus
just check-native-migration /data/project/tag-all
just plan-native-pc
```

前两个入口需要既有产品验收报告/不可变制品，不重编译或跳过产品 gate。第三个只核对当前固定 PC 项目，不输出凭证或读取数据库。原生文件网关完整复验另见 check-native-workspace，需 Playwright/Chromium。

组合模块入口为 `import ./home-manager/native-stack.nix { tagAllSource = /data/project/tag-all; }`；选项 services.tag-native-stack 默认停用。启用试验时显式传 tested package、frontendRoot、workspace、运行期 authFile、nodeId 与端口；浏览器和核心各自分包，组合模块不强制安装 Firefox。不要将生产认证文件复制进 Nix store。

安装验收仅构建生成物，未执行 activate 或 import 到当前 home.nix。实际宿主配置仍由用户普通终端执行 rerun.nu，必须明确 --host liu-bigpc；未完成拓扑/路径适配及宿主配置全部构建前，不提供切换指令。

现用 PC 仍是 5006 私人入口和配对同步节点；原生试验在 18006/18081 且关闭同步。需要保留 loc_pc、CA、发现和 /workspace/project 嵌套映射之后才有资格切换。

回退原则：停新服务、恢复旧入口/二进制，尽量保留新期间的数据；schema 若不兼容，保留新状态并报告。旧快照恢复是单独的显式操作，可能失去快照后写入，不能作为自动失败处理。合成测试没有修改生产工作区。

## 显式配对配置（尚非生产切换）

默认 syncMode=isolated。试验可显式设置 syncMode=configured、configurationFile（当前用户所有，600 的运行期 TOML）和 environmentFile（工作区外、600 的运行期 systemd 环境文件）。配置保留具体位置、身份、配对和私人 CA；认证环境由服务管理器读取，不在 Nix 中读取其内容。两个配置都只是路径，不包含入 store 的凭证。

产品包装入口现在还必须通过真实临时双节点的 TLS/双方批准/签名/撤销/重放/重启检查。该测试使用 Python TLS 代理，不代表 Caddy 配对入口或发现服务已经接通；不要据此切换生产。

## 嵌套目录与整套生命周期

组合可显式声明 `workspaceMounts = { project = "/data/project"; };`，将源目录呈现
为工作区的 `project` 子目录。两端目录必须已存在；这是可信安装配置，不能来自网页请求。
只在核心和 DUFS 的私有命名空间呈现，宿主目标目录内容不受挂载影响；不会改成 symlink。
支持空格、中文、% 和 $；相对目标不能含空组件、.、..，路径不能含冒号、换行、
单引号或反斜杠。该模式需要宿主支持用户命名空间，否则启动明确失败。

组合启用后由 `tag-native-stack.target` 统一管理 core/files/gateway：
`systemctl --user start tag-native-stack.target`、`stop`、`restart` 操作整套服务。
停止 target 返回后，子服务可能仍处于短暂退出中，须等三项均 inactive；
运行中的组合会自动恢复异常退出的组件。独立 core 不受组合 target 接管。

复验：`just check-native-stack-runtime /data/project/tag-all /data/project/dufs-plus`。
只运行随机名称的实际生成单元副本及合成数据，检查映射读写、逐项 SIGKILL 恢复、
整套停止/重启和精确清理。Caddy 数据/自动保存限定于组合私有状态，socket 路径
超过 Linux 107 字节限制会在构建前拒绝。实际开机和现网迁移仍未执行，不据此激活。

## 显式 HTTPS 配对入口

在组合配置的 `peer` 中显式设置 `enable`、`serverName`、`listenAddress`、`port`、
`allowedNetworks`、`certificateFile` 和 `privateKeyFile`；默认不开启，试验默认仅 loopback。
启用时须 `syncMode = "configured"` 并指定私有 `environmentFile`；TLS 两个文件必须
是当前用户所有的普通文件、权限 600、位于工作区外。文件内容不入 Nix store。

本机认证网页入口可以刷新候选、发起申请、同意和撤销；管理员令牌由已认证网关
在内部注入。HTTPS 节点入口只接受声明网段内的配对/同步/受控代理请求，其他路径 404。
节点入口删除管理员及设备权限头，后端仍验证签名/批准/私人 CA。

复验：`just check-native-peer-gateway /data/project/tag-all /data/project/dufs-plus`。
使用实际生成 Caddy 配置与两个临时原生核心；候选由临时文件提供，过滤过期候选
并跑申请/同意/签名同步。没有 mDNS 广播、现网认证文件读取或生产切换。
真实宿主地址/接口/CA 和目录配置尚未适配，不能直接照试验端口替换现用节点。

## 保留已有 Caddy CA

默认仍使用显式证书文件。已有 Caddy `tls internal` 的实例可设置 peer.tlsMode 为
`internal`，并用 peer.storageDirectory 指向私有 Caddy 存储根（直接含 pki/ 和
certificates/）。certificateFile/privateKeyFile 必须为空。
这保留 Caddy 的自动续期，不尝试安装系统信任。存储和 CA 文件必须通过私有权限守卫。
现用服务不得在线共享存储；停旧服务、备份并离线复制的实际步骤归 S2 切换方案，
本说明不代表已具备切换条件。合成回归入口：
`just check-native-peer-renewal /data/project/tag-all /data/project/dufs-plus`。
