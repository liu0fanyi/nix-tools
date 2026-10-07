# Tasks — 原生核心组合与 PC 切换

- [x] T001–T004 同源认证文件入口、模块与临时组合验收、证据收尾。
- [x] T005a 组合安装 generation 构建（不激活）。
- [x] T005b 合成完整版离线备份、原生读写和保留新写入的回退。
- [x] T005c 固定 PC 只读拓扑/配置预检。
- [ ] T005d PC 切换前准备；以以下 S1–S3 为唯一剩余步骤。
- [ ] T005e 用户实际切换后的入口、同步、发现、登录/开机与回退验收。

## 当前阶段：PC 服务切换前准备（剩余 1 步）

以下三个编号是当前阶段的唯一计数；内部测试不另算步骤。完成一个才减少计数。

- [x] S1 保留现有 CA 信任与证书自动续期；临时服务的离线存储接管、实际运行中自动续期与信任验收通过。
- [x] S2 完成当前主机的可切换配置与预演：转换配置序列化和合成启动、非法发现配置拒绝（不广播）、完整 toplevel 和 Home Manager generation 构建、旧容器自动启动互斥，以及明确的离线备份/切换/回退步骤。
- [ ] S3 确认当前文件和媒体功能可继续使用，逐项说明原生核心与保留工具服务的路径，验证必要回退；不可用项必须解决或取得用户明确接受后才能通过。

三步均完成且证据固定，即结束切换前准备，向用户交付实际可执行的切换步骤。
Agent 不执行宿主 switch；离线备份/迁移只在用户明确进入切换步骤、源 writer 已停止后执行。
真实 LAN 发现、PC/NUC 同步、登录/开机和浏览器行为属于切换后的 T005e 验收。
T006 只做已定范围的证据/手册/提交/镜像收尾。
不得将新的重构、抽象、其他平台、全工具迁移或优化加入切换前置条件。
必要的阻塞缺陷须归入 S1–S3，说明影响；确需扩大范围时先由用户决定，不能默默增加步骤。

## 已通过的依据

- 原生包 HTTP、持久化、单实例与默认停用模块：由 tag-all 024 的 native-results.json 固定。
- 组合安装与合成离线备份/完整二进制回退：[install-results.json](install-results.json)、[migration-results.json](migration-results.json)。
- 工作区映射、三个服务崩溃恢复及整套重启：[stack-runtime-results.json](stack-runtime-results.json)。
- 实际 Caddy 双节点 TLS、批准/签名同步、撤销/重放/错签名拒绝；认证网页管理、发现候选过期过滤及申请/同意：[peer-gateway-results.json](peer-gateway-results.json)。
- 六组路径/身份/发现参数转换回归及现用 PC 只读检查：[pc-preflight.json](pc-preflight.json)。转换仍只在内存中，不是已激活的生产配置。

临时测试不广播，不读取生产 DB/私钥；现用服务未切换。activated=false、cutover_ready=false。
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
