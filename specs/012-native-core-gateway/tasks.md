# Tasks — 原生核心组合与 PC 切换

- [x] T001–T004 同源认证文件入口、模块与临时组合验收、证据收尾。
- [x] T005a 组合安装 generation 构建（不激活）。
- [x] T005b 合成完整版离线备份、原生读写和保留新写入的回退。
- [x] T005c 固定 PC 只读拓扑/配置预检。
- [ ] T005d PC 切换前准备；以以下 S1–S3 为唯一剩余步骤。
- [ ] T005e 用户实际切换后的入口、同步、发现、登录/开机与回退验收。

## 当前阶段：PC 服务切换前准备（剩余 2 步）

以下三个编号是当前阶段的唯一计数；内部测试不另算步骤。完成一个才减少计数。

- [x] S1 保留现有 CA 信任与证书自动续期；临时服务的离线存储接管、实际运行中自动续期与信任验收通过。
- [ ] S2 完成当前主机的可切换配置与预演：转换配置序列化和合成启动、非法发现配置拒绝（不广播）、完整 toplevel 和 Home Manager generation 构建、旧容器自动启动互斥，以及明确的离线备份/切换/回退步骤。
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

## S2 预演进展（未完成，当前仍剩 2 步）

- [host-preflight-results.json](host-preflight-results.json)：实际 liu-bigpc Home Manager
  generation 构建通过；检查新状态路径、ready/回退模式互斥、旧容器恢复不自动启动。
- [config-runtime-results.json](config-runtime-results.json)：转换后的 TOML 无损往返、
  真实核心读取位置身份、非法内置发现接口在 daemon 创建前拒绝；未广播。
- 13 项配置/离线快照回归：SQLite完整性、metadata/CA/额外状态与私有权限保留，
  回退使用新数据库，拒绝源重启、symlink/危险凭证、覆盖已有目标和目标发布竞争。
- 完整 toplevel 尚未通过：既有 Tag Browser fetchClosure 依赖缓存读取失败；
  本机精确依赖路径有效，缓存 HTTP 请求返回403，原因未进一步确定。未更换浏览器包绕过构建。
- 离线准备工具只完成合成测试；生产 --prepare-offline 未执行，最终用户 switch
  命令和回退 Compose 合并预演尚待完整构建通过后交付。S2 不勾选。
