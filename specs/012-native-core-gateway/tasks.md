# Tasks — 原生核心组合与 PC 切换

- [x] T001–T004 同源认证文件入口、模块与临时组合验收、证据收尾。
- [x] T005a 组合安装 generation 构建（不激活）。
- [x] T005b 合成完整版离线备份、原生读写和保留新写入的回退。
- [x] T005c 固定 PC 只读拓扑/配置预检。
- [x] T005d PC 切换前准备；按 tag-all 024 的 S3.1–S3.7 工作清单计数。
- [ ] T005e 用户实际切换后的入口、同步、发现、登录/开机与回退验收。

## 切换前准备已完成：S3.7 完成 3/3，剩余 0

跨仓库只按 tag-all 024 的 S3.1–S3.7 固定工作清单计数。
本仓不把剩余整个 S3 报为一步；024 是产品权威规格，本段仅记录候选安装状态。

S1/S2 和 S3.1–S3.6 已验收。S3.6 固定 A/B/C 完成 3/3、剩余 0：同一完整静态 CLI 的
包、实际 liu-bigpc toplevel 与 HM 已构建，专用工具存储/启动/重启与同一 DB 锁通过。
证据见 [native-full-install-results.json](native-full-install-results.json)。实际包装/运行时 7 项、
生成守卫 8 项、模块合法/拒绝与默认停用通过；系统和 HM 没有激活，旧五容器仍运行。

S3.7 A/B/C 已完成：9 项完整组合、8 项实际生成守卫、20 项配置/快照/守卫回归通过。
证据见 [native-final-combination-results.json](native-final-combination-results.json)。
首次 executors 父目录缺失已由产品包装安全准备；完整 tools stack 的网关改 Wants，
避免工具故障通过核心 BindsTo 引发 gateway Requires 停止事务竞态。纯核心旧依赖不变。
同一实际主机快照的系统/HM重建，未激活；278 项实际前端资产固定 SHA。
cutover_ready=true 只指合成门槛通过，未迁移生产；真实容器重建未冒充为 CLI 回退结果。

### 当前阶段 T005e：已完成1/3，剩余2项

- [x] T005e-A 离线快照与原生激活，补齐实际网络适配及持久用户服务注册；旧数据库不覆盖。
- [x] T005e-B 用户确认 PC 试用验收；自动网络/处理证据仍见 pc-live-cutover-results.json。
- [ ] T005e-C 登录/重启恢复及真实回退核验，保留新写入并记录结果。

与产品 024 使用同一计数，不重复相加。不会新增重构、其他平台或全工具迁移。
历史 S3/PDF 段落保留当时证据，当前状态以本节和最终组合报告为准。

## 已通过的依据

- 原生包 HTTP、持久化、单实例与默认停用模块：由 tag-all 024 的 native-results.json 固定。
- 组合安装与合成离线备份/完整二进制回退：[install-results.json](install-results.json)、[migration-results.json](migration-results.json)。
- 工作区映射、三个服务崩溃恢复及整套重启：[stack-runtime-results.json](stack-runtime-results.json)。
- 实际 Caddy 双节点 TLS、批准/签名同步、撤销/重放/错签名拒绝；认证网页管理、发现候选过期过滤及申请/同意：[peer-gateway-results.json](peer-gateway-results.json)。
- 六组路径/身份/发现参数转换回归及现用 PC 只读检查：[pc-preflight.json](pc-preflight.json)。转换仍只在内存中，不是已激活的生产配置。

临时测试不广播，不读取生产 DB/私钥；现用服务未切换。当前 activated=false、cutover_ready=true。
实际生产任务、真实开机及 LAN 发现未用合成测试替代。

## S1 验收结果

[peer-renewal-results.json](peer-renewal-results.json)：同一生成的 Caddy 配置增加显式
internal 模式，使用私有存储并禁止系统信任库安装。合成旧服务停止后离线复制存储，
新服务首次沿用缓存叶证书；运行中自动续签后仍被旧根 CA 信任，原 CA 与源快照不变。
未受信任 CA 和节点管理员路径拒绝；实际生成的启动守卫拒绝缺失、644 与 symlink 私钥。
临时证书为 30 秒、续期扫描 1 秒，仅测试调整；产品使用 Caddy 默认值。
默认关闭/静态证书/配置模式安装回归通过，测试进程和存储已清理。
未读取生产私钥，未迁移生产 CA；实际离线复制和启动互斥仍属于 S2 切换方案。

## S2 预演完成（当前仅剩 S3）

- [host-preflight-results.json](host-preflight-results.json)：最终完整 liu-bigpc 系统及对应 HM 已构建，
  精确产物与 GC 根固定；未激活。实际主机源码已捕获为同一不可变 Nix快照，
  系统/HM均从该快照构建；hm-backup保护已核验。使用实际主仓已有主机修改，没有将其无关改动提交。
- [config-runtime-results.json](config-runtime-results.json)：配置无损往返与真实核心启动，非法发现接口拒绝；无广播。
- 20 项配置/离线快照/模式守卫回归通过；源重启、覆盖/竞争、非私有/缺失文件均拒绝。
- [mode-guard-results.json](mode-guard-results.json)：六项真实临时 ExecCondition 检查。
  两项放行实际执行启动桩；源未停、旧状态、原生未停或镜像不符实际没有执行启动桩。
  实际 Podman socket 在 PrivateUsers/PrivateMounts 下只读可达；未启动生产容器。
- [rollback-merge-results.json](rollback-merge-results.json)：五个各自固定镜像、新 DB/metadata/CA/认证/信任证书，
  实际 Compose 合并通过。原生期间新写入保留，旧源凭证不能覆盖快照中的新值。
- 候选替换旧恢复逻辑，只在 ready + container-mode 下检查实际挂载/镜像及原生停止后恢复固定五容器；
  原生三个服务要求源容器全部停止。默认主机配置仍不启用候选。
- 已审查明确的用户离线准备、固定系统激活、只创建后核验再启动回退、开机恢复及返回原生顺序。
  手册以 nix-tools docs/native-pc-cutover.md 为准；普通 rerun 不包含候选，不用于原生试用升级。
- S2 已通过，当前仅剩 S3。生产离线准备/实际 switch/真实开机未执行，cutover_ready=false。
  S3 通过前不向用户要求执行停机或切换。

只读核对确认现用 PC 核心/发现容器镜像不同；快照分别固定原镜像，不要求相同、不替换版本。合成合并与启动守卫以不同镜像复验通过；五个现用容器仍在运行。

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

### T005e-A 真实切换修正（2026-10-09）

本次只切 PC，NUC 保持现状。首次停止旧恢复单元误杀同 cgroup 的 conmon；五容器实际退出。离线准备随后因旧 PC 无 basic_auth 而拒绝，未生成 ready、未激活、未改源数据库。旧服务已按固定名称恢复并核验5006为200。
候选补显式 loopback 认证模式，仅127.0.0.1免登录；其他消费者仍默认 Basic Auth，peer TLS/签名/管理员路径不放宽。迁移拒绝已有认证或 imports，不静默降级。候选恢复单元 KillMode=process；停旧单元前加临时同等覆盖并复核真实状态。
仍属既有 T005e-A 的阻塞修正，不新增阶段项。T005e 三项仍未完成；部署后再核验实际功能与重启。

### 当前实际运行状态（2026-10-09）

[PC实际切换结果](pc-live-cutover-results.json)：T005e-A已完成，当前T005e为1/3、剩余2项。旧五容器已停止、原数据库不覆盖，PC原生服务已运行。实际文件映射、PDF/EPUB处理、配对/证书和PC–NUC同步200通过；同步此次无差异，不声称已验证新的界面写入。
静态二进制缺少宿主mDNS支持，现保留旧ExtraHosts为服务私有只读hosts；使用既有批准HTTPS同步地址且保留原签名策略。迁移新增不歧义/不丢凭证的地址适配，24项回归通过。
核验期间另一宿主更新移除试用HM单元，已保留当前系统其他配置，通过持久用户单元注册恢复；GC根和旧恢复互斥守卫保留。仅核对启用与真实加载路径，未重启或注销，NUC部署未变。快捷入口已纳入网络和注册，不重复准备现有快照。
下一步B：正常界面试用，验证新写入在另一节点可见及LAN发现；C：方便时真实重启/登录恢复，按既有范围记录回退验证。T006收尾仍在上述验收之后。

## 当前用户验收及后续

用户确认 PC 试用已验收，授权继续 NUC。T005e-B 记用户验收通过；未逐项确认的
真实开机与生产容器回退不制造通过证据。当前执行以 013 / 产品025 的 N1–N6 为准。
