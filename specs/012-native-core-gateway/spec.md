# 012 — 原生核心的同源认证文件入口

## 范围

在两个独立 loopback TCP 端口和私有 Unix 文件 socket组合 Caddy、原生 core 与 DUFS；保持 /tag-api 和静态/文件入口。Home Manager 默认停用，不 import 到当前配置，不激活 PC/NUC。

## 固定验收边界

1. 同源根入口与 /tag-api 通过真实原生服务。
2. 匿名与错误凭证拒绝；已登录可以受控操作自己的临时文件/标签；不给页面任意指定 API 的能力。
3. 核心缺媒体能力反馈准确，原文件仍能读取；已通过的窗口/节点隔离保留。
4. 实际结果、限制、提交推送与所属固定 todos 镜像收尾。

本规格属于 tag-all 024 T004 的配套关卡；真实 PC 迁移、生产同步/配对、全部工具容器与其他平台不在本步。

## 结果与复验

实际原生核心 + Caddy + DUFS Unix socket 通过：匿名/错误凭证及匿名写入拒绝、认证标签/文本/上传/列表/原文件/流读取、私有应用入口拒绝，合成 PDF 未改变，自有进程/目录已清理。Home Manager 启用/停用求值、全部断言、依赖关系与特殊字符参数转义通过；模块未激活。

在 nix-tools 的 devenv shell 中执行 `just check-native-workspace /data/project/tag-all /data/project/dufs-plus /data/project/tag-browser`。需既有 core 原生 gate 报告、dufs-plus dist、Playwright 的 NODE_PATH 和实际 CHROMIUM_PATH；无 API/静态 HTTP mock。模块复验见 nix-tools 的 tests/native-workspace-module.nix。生产安装、实际开机和迁移/回退属于 tag-all 024 T005。

## 组合安装与迁移状态

安装 generation 已实际构建；自有合成数据完成完整版 → SQLite/元数据离线快照 → 原生核心 → 完整版二进制回退，回退后保留原生新增标签；单独演示旧备份恢复到新目录。凭证/身份仅不透明夹具，真实签名与任务执行未测试。
真实 PC 预检仍拒绝切换：配置转换和临时配对/映射已通过，证书续期合成验收已完成；宿主完整构建及合成激活/回退预演已通过，S2完成；S3文件/媒体兼容未完成，生产离线迁移与实际切换未执行。现用容器、数据和配置未改变。剩余关卡见 tasks T005d/e；结果文件记录 activated=false 与 cutover_ready=false。

合成迁移另验证明确位置 ID、网页收藏与文件标签均保留；该结果不替代现网同步/容器路径转换的验收。

显式 configured 配置透传与运行期认证文件路径已实现；默认 isolated 保持。两种安装产物
构建通过，产品真实双节点配对/CA/签名/重启证据见 [peer-results.json](peer-results.json)。
该证据使用 Python TLS 夹具；实际 Caddy 与目录映射的后续结果见下方。真实发现/现用配置适配仍未完成，不能切换现网。

目录映射/生命周期验收见 [stack-runtime-results.json](stack-runtime-results.json)：
使用实际生成单元，在自有临时状态验证映射读写、三项崩溃恢复、整套停止再启动和清理。
不改变宿主工作区目录；未触碰生产服务。配置入口仍默认停用，实际开机/切换未验。

## 私人节点通信入口

HTTPS 入口默认停用，显式指定 DNS 名、IPv4 监听、允许网段及私有运行期 TLS 文件；
只开放既有配对握手、签名同步和受控代理路径，其余路径 404。
网页管理走已认证的本机入口，管理员环境在运行期读取，覆盖来自网页的管理员头，
不会把管理员权限注入节点通信入口，也不将密钥或令牌复制到 Nix store。
真实双节点及候选/申请/同意验收见 [peer-gateway-results.json](peer-gateway-results.json)。
候选来源为自有临时文件，此结果不代替局域网广播发现、真实开机或现网迁移。

## 当前阶段：PC 服务切换前准备（剩余 1 步）

以下三个编号是当前阶段的唯一计数；内部测试不另算步骤。完成一个才减少计数。

- S1 保留现有 CA 信任与证书自动续期；临时服务的离线存储接管、实际运行中自动续期与信任验收通过。
- S2 完成当前主机的可切换配置与预演：转换配置序列化和合成启动、非法发现配置拒绝（不广播）、完整 toplevel 和 Home Manager generation 构建、旧容器自动启动互斥，以及明确的离线备份/切换/回退步骤。
- S3 确认当前文件和媒体功能可继续使用，逐项说明原生核心与保留工具服务的路径，验证必要回退；不可用项必须解决或取得用户明确接受后才能通过。

三步均完成且证据固定，即结束切换前准备，向用户交付实际可执行的切换步骤。
Agent 不执行宿主 switch；离线备份/迁移只在用户明确进入切换步骤、源 writer 已停止后执行。
真实 LAN 发现、PC/NUC 同步、登录/开机和浏览器行为属于切换后的 T005e 验收。
T006 只做已定范围的证据/手册/提交/镜像收尾。
不得将新的重构、抽象、其他平台、全工具迁移或优化加入切换前置条件。
必要的阻塞缺陷须归入 S1–S3，说明影响；确需扩大范围时先由用户决定，不能默默增加步骤。

## S3 调查与接入决定

[file-media-results.json](file-media-results.json)：认证上传/下载/删除、中文/空格/%路径、
Range、Markdown 附件引用与字节、实际 WASM/PDF.js 阅读通过。
媒体与扩展能力仍未编译，12 个处理接口实际返回 404；不以文件可下载宣称处理可用。
本次没有验证视频播放/EPUB 前端阅读，也没有运行实际处理任务。
用户明确选择补齐 PC 处理服务、保持完整功能。S3 未通过，当前仍剩 1 步；
现用 PC/NUC 服务未切换，cutover_ready=false。
下一步接带处理接口的唯一原生工作区装配及受控工具执行器；不得并行写同一 DB。

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

## 当前完整安装候选

S3.6 完成 3/3，产品证据及同一实际主机/HM 固定在
[native-full-install-results.json](native-full-install-results.json)。完整处理选项、独立工具运行时
与启动/回退互斥已装配；没有激活。剩余按产品 024 计数：S3.7 最终组合验收，固定3项。
现用 PC/NUC 不变，cutover_ready=false；历史轻量/PDF 记录不代表当前完整候选。
