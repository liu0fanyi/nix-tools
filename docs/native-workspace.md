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
