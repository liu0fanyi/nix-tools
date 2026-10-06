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
