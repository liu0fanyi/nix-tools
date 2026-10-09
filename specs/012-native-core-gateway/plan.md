# Plan

## Constitution Check

核对工作区 AGENTS 与本仓库 constitution，PC 本机实施，规格归各产品；基础设施在独立 worktree，不混入主树未提交改动。
外部参考/ref、说明/docs、需求/specs 分层及固定 gitlink/shallow 约束不变；使用已锁定 Nix 包和已验收产品制品，不复制上游参考或移动嵌入文件。
不执行 switch、现网迁移、产品生产部署、默认 Podman 清理；新构建仍从各产品 just 入口，已有同一字节制品复用明确记录。

## 实施

实现固定上游/Basic Auth 网关与默认停用模块；对匿名/错误凭证、标签/文本、真实文件上传/读取和静态入口实测；验证消费者，不迁移生产。

运行代码若无需改变，也须给出实际组合验收依据，不能以理论兼容直接勾选。

## T005：固定结束位置

按 tag-all 024 FR-006，先只构建组合 generation 与合成离线迁移回退，不激活宿主。
新组合入口是模块工厂 native-stack.nix，由消费者明确指定 tag-all 权威模块源，统一包/工作区/端口；不另复制产品模块。
基础设施主树有其他未提交改动，继续在原独立 worktree 编写，合并仅本次白名单。
运行完整版使用 023 固定已验收归档中校验过 SHA 的静态二进制，只导出 app/tag-server 字节，无 tar 解包或容器运行；合成后台任务仅 opaque fixture，不声称真正任务执行/签名配对通过。
SQLite backup 仅在自有进程退出后进行，元数据同样离线，源/备份保持不变。默认二进制回退继续用新数据；只有明确恢复演示才把旧备份恢复到全新目录，不能覆盖新写入。

实际 PC 为 dufs-plus-pc 项目，后端镜像 9deedf60…；认证入口 5006，节点配对入口与发现服务独立。配置含 loc_pc、配对/NUC 同步与容器 /workspace/project 嵌套挂载；当前原生 --disable-sync 试验与无 symlink DUFS 不等价。
只读预检须输出 cutover_ready=false，保留现网；不把源 writer 正在运行当作让用户此刻停止的要求。

剩余固定关卡：T005d 保持拓扑/路径/身份语义并实际组合运行与配置预演；T005e 由用户执行当前主机配置切换后核验入口/登录启动/回退；T006 以既定五关收敛。
不扩大为其他平台、全工具迁移、NUC 切换或原生 Rust 重编译。

T005d.1 组合模块传递 configurationFile、syncMode、environmentFile，环境文件只引用运行期路径；
默认 isolated 和独立状态保持。configured 从私有 TOML 保存现用身份/位置/CA/同步配置，
当前双节点 gate 在 tag-all 用独立随机身份验证，未读取/复制生产配置密钥。
Caddy 配对入口、候选握手、嵌套工作区和临时生命周期已通过；剩余以 tasks.md 的 S1–S3 为准。

## T005d 目录映射与生命周期

组合模块调用 tag-all 权威 workspace-mounts.nix；可信 workspaceMounts 显式声明
工作区相对目录与宿主源目录。只为 core/DUFS 开启私有用户和挂载命名空间，现有
目录保持原样；ConditionPathIsDirectory 在启动前要求两端目录存在。
一个默认停用的组合 target 负责三个服务的启动/停止/恢复，凭证仍只在私有运行期文件。
Caddy 的 autosave 和数据目录限定到本组合私有状态；Unix socket 长度超限提前拒绝。
实际生成单元仅替换测试名称，以临时合成数据验证读写、崩溃恢复、停止再启动和清理。
Constitution Check：本机构建、产品模块单源、依赖锁定；无外部参考新增，无宿主
switch、现网目录挂载或生产数据库操作。真实 Caddy 配对入口/发现及宿主完整构建仍待完成。

## T005d 实际配对入口与发现边界

由 nix-tools 原生网关统一生成私人 TLS 站点，与认证网页入口分开；遵循现有
/tag-api → 根 API 转换，允许网段及节点端点白名单，禁止管理员/设备权限头透传。
本机网页认证通过后可访问管理接口，由 Caddy 从私有 EnvironmentFile 注入管理员头。
产品真实双节点测试提供可选代理工厂，默认 Python TLS gate 不变；基础设施复用
相同真实身份/签名/批准/重启负例，增加真实 Caddy、来源网段拒绝和网页认证检查。
发现仅用 external_agent 的自有候选文件验证读取、过期过滤与申请/同意握手。
下一步核对原生宿主可直接运行核心内置发现；转换现用 external_agent 配置须
保留身份/地址/接口且先预演。真实广播仍需遵守禁广播的临时验收边界，不默默开启。
Constitution Check：本机固定二进制/Nix 依赖，无 Rust 重编译、外部参考新增、
生产数据/密钥读取或系统激活；仅 loopback HTTPS、自有密钥与临时进程，精确清理。

## T005d 现用配置转换

`native_pc_config.py` 为纯转换函数：只转换 locations.path 和 pairing.trusted_ca_files，
按容器 bind 的最长目录边界匹配；拒绝无映射、相对路径与遍历。原字典、节点/位置 ID、
同步对象和未知字段不变。工作区嵌套映射另返回，不把普通 URL/文本当作路径改写。
发现容器的身份/广告地址须与核心 TOML 一致；完整显式 CLI 提供 RFC1918 IPv4 和接口，
将 external_agent 转为内置发现。此步骤仅内存转换，不生成/激活生产 TOML。
六组回归包括中文路径、最长映射、源不变、身份/参数不匹配和非法地址拒绝；真实 PC
只读转换摘要写入 pc-preflight.json。未验证真实 LAN 广播或宿主完整构建。

现用 peer-gateway 使用 Caddy tls internal；只读文件元数据确认已有叶证书、根与中间
CA 均为当前用户所有、600。不能只把现有叶证书路径交给静态 TLS：还须保留同一 CA
下的自动续期。既有 CA 存储接管/续期已通过 S1 合成验收，下一步构建当前主机完整候选配置；
切换方案必须停用旧 pc-private-node-restore 自动恢复，防止旧容器抢占端口。
不读取私钥字节，不迁移在线 DB，不提前停止旧服务。

## 当前执行顺序与停止汇报

S1 已验收，按 tasks.md 的 S2 → S3 收敛，三步完成后交付用户切换；不得新增优化前置。
每次结束工作时说明阶段名称、剩余步骤数、未完成编号和下一步；
计数按 S1–S3 验收状态，不按测试数量或历史任务累计。切换后改按 T005e 的验收清单计数。
Constitution Check：本次只收敛既有范围和新增用户明确要求的汇报约束，
不引入外部参考、不修改构建/迁移授权、不执行系统激活或读取生产密钥。

## S1 证书续期接管完成

显式 peer.tlsMode=internal 使用 peer.storageDirectory 指向离线复制后的 Caddy
存储根（含 pki/、certificates/），继续 tls internal，自动 HTTPS 只禁重定向；
skip_install_trust 保证不自动改宿主信任库。files 模式和默认关闭保持。
启动前要求现有 CA 根/中间证书及密钥，当前用户所有、600，pki 目录700且无
symlink；缺文件直接拒绝，避免静默生成不同根 CA。S2 须在旧网关停止后复制到
新私有状态，禁止新旧服务共享在线可写 CA 存储。生产私钥不进入 Nix store。
续期验收见 peer-renewal-results.json；不把临时 CA 结果当成已完成生产迁移。
官方依据：[Caddy 自动 HTTPS 配置](https://caddyserver.com/docs/caddyfile/options)、
[内部证书签发](https://caddyserver.com/docs/caddyfile/directives/tls)。

## S2 激活与回退预演完成

最终候选的三个原生服务各用 ExecCondition 检查固定源容器均已停止；通过本机
Podman socket 只读获取状态，私有用户/挂载命名空间实测可访问该 socket。
容器恢复单元要求 ready + container-mode，检查四个原生单元停止、五个容器身份/
固定镜像及新 DB/CA/证书/工作区挂载后只启动固定五个名称。默认主机不启用候选。
离线 overlay 固定全部源镜像，并引用新认证环境与信任证书；实际 Compose 合并
和原生期间新写入可见已验证。源 DB/CA 保留，不能用直接启动旧容器代替回退。

最终系统/HM 均构建并添加自有 GC 根；六项真实 ExecCondition 放行/拒绝及20项
回归通过。用户操作链路固定为停止源→离线准备→守卫→固定候选激活；回退为
停止原生→标记回退→只创建五容器→实际守卫→受保护恢复。返回原生先停全部容器。
具体命令权威源在 nix-tools docs/native-pc-cutover.md；切换非原子，实际用户操作
仍未执行。当前仅剩 S3，cutover_ready=false。

候选是明确固定产物的试用配置，普通 rerun 使用默认主机配置会撤掉候选；试用期
系统升级须重新构建同一候选入口、核对完整系统/HM再由用户激活，不能隐式混用。
Constitution Check：仅本机候选构建/合成临时单元/只读 inspect，无生产凭证或数据库
读取、真实广播、停止容器、离线生产复制或宿主 switch；不扩大阶段完成条件。

## S3 PC 处理兼容实施

用户已选择补齐 PC 处理服务，保持完整功能。文件基线与实际缺失见
[file-media-results.json](file-media-results.json)；S3 仍未完成，阶段剩余 1 步。

- 保留轻量 core 包；可选工作区装配复用已验收完整版静态服务，接入处理接口，
  替代 core 进程并复用同一状态锁；不另建共写数据库的媒体服务。
- 重工具通过明确操作的受控容器执行，先复用 PDF 执行器，再补此次 PC 兼容清单。
  worker 不接触 DB/身份/全部 metadata/socket，不用任意 shell 代理替代执行契约。
- 对照现用 PC 能力，逐项验证真实处理结果、原件保留、失败/取消/重启；
  新装配须重建实际宿主候选并复验互斥与回退。
- 当前只完成兼容调查和自动基线，未接入处理服务、未更换原生候选、未发布。

Constitution Check：本机固定制品与原 tester 规则保持；纯核心依赖不扩大。
本次无外部参考/目录迁移，未写生产数据；新增工作归已授权 S3，不追加其他平台或优化。

产品详细契约：`tag-all/specs/024-native-core-release/contracts/pc-processing-compatibility.md`（产品仓库权威源）。

## S3：可选原生工作区 PDF 接入已通过

- [workspace-pdf-results.json](workspace-pdf-results.json)：复用 023 相同已验收 image ID 的
  完整静态 API 制品，原核心启动器继续持有同一 DB/身份/任务锁；纯核心包与其制品未改。
  页数、页面 JPEG 渲染和切边实际 HTTP 通过，两次启停保留标签、文本与 PDF owner。
  实际观察 4 个 worker：只读单文件输入、只读根、无网络和资源限额；源 PDF 未改。
  非法位置、越界、缺文件、重复 DB writer、浮动镜像/网络运行时/工作区内状态均拒绝。
  工具镜像仅加载到自有 rootless VFS 运行时，结束清理；默认 Podman 存储未导入镜像。
- [workspace-pdf-module-results.json](workspace-pdf-module-results.json)：产品共享 PDF 配置类型、
  实际 HM 合法配置及纯核心通过；五种错误选择被拒绝，Environment 中 %/$/中文/空格处理通过。
  默认停用既有门槛复验通过；不新增第二个媒体 tag-server 或第二个 DB writer。
- [workspace-pdf-host-results.json](workspace-pdf-host-results.json)：基于同一实际 liu-bigpc
  源码快照的可选 PDF 系统/HM 均构建，生成单元的镜像/状态/socket 参数核对通过；未激活。
  组合预检仅显式 processing=true 使用该包，默认候选仍为原核心；真实生成单元运行尚未验。
- 可选包静态服务为 34,378,480 字节；包含 Podman 的 NAR 运行闭包 704,862,720 字节、
  144 路径。这不是下载压缩量，也未包含工具镜像体积；不宣称本次包装更小。

当前仍剩 **1 步 S3**，cutover_ready=false。这次只完成 PDF 装配及合成门槛，
封面/缩略图、EPUB 服务端/前端阅读、漫画转换、解压、音视频及现用扩展能力对照仍须接续。
归档/音视频/漫画/Git/音乐/转写等缺工具的能力当前为 dependency_unavailable，不能说全部媒体已恢复。
下一步接归档/音视频受控执行，逐项补结果与取消/恢复；完整工具就绪后再复验最终候选
实际单元、互斥、回退与镜像生命周期。真实 PC/NUC 服务保持，现阶段不要求用户停机。

## S3.6 完整安装候选已完成，下一项 S3.7

本轮实际入口继续由 native-pc-host 扩展当前主机，不 import 到默认主机配置。
完整包和四类执行器来自 tag-all 同一冻结 CLI/工具归档；native-stack 转发产品权威选项，
工具单元与后端一起受 ready/旧容器停止守卫及 target 维护。回退守卫包含工具单元，
旧纯核心无该单元时兼容 unknown，其余单元继续要求 inactive/failed。

实际 toplevel/HM 从同一不可变主机源码快照构建。用户已有 staged/未提交配置保留，
只提交本阶段候选/守卫/合成测试与规格，不执行激活或迁移。产品/运行时7项与生成
守卫8项通过；证据见 [native-full-install-results.json](native-full-install-results.json)。

Constitution Check：规格仍以 tag-all 024 为权威，不在基础设施建立另一套范围；
无外部参考/gitlink、无生产 DB/私钥读取，专用工具存储与资料镜像均按白名单核验。
下一项 S3.7 固定 A/B/C；只有全部通过才交付用户切换，当前 cutover_ready=false。
