# Nix 配置与发布工具

## 当前情况
- [Z-Library CLI v0.0.14已接入Nix，独立包、完整PC/HM及网络检查通过；待用户手动应用和登录验收。](010-host-configuration/tasks.md#z-library-终端客户端-nix-接入阶段-zl2026-11-15)
- [Android局域网配对已补齐NUC现用网关两条固定POST路径并reload，真实申请/审批成功；公网移动白名单仍未部署，不扩大外网路由。](014-application-entry-boundary/tasks.md)
- [学习地图独立登记已按037增量候选启用；配置与启动保护摘要同事务切换，后续14文件静态发布不重启，用户学习资料保持。](017-independent-learning-map/tasks.md)
- [定制Trime已由独立产品正式签名发行3.3.14，输入/更新按钮通过；旧原版与知识卡QA已按用户明确授权双份备份后退役，当前默认定制输入法保留。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [知识卡0.1.6预览/公式及PC数学/识图入口已发布可信缓存与Android双渠道，完整PC/HM候选通过；未安装手机或switch，网页事务待本次保存确认，后端及Helix外部改动保持。](014-application-entry-boundary/tasks.md)
- [Codex桌面26.1103.31037修复已实机生效：不可达主机停止自动重连，NUC保持开启；6个内置插件成功物化并复用，无新增权限错误，聊天记录未动。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [Tag Browser nix.128根目录与侧栏恢复修正已发行，签名缓存、实际Firefox及完整PC消费者构建通过；未system switch或切换配套服务。](014-application-entry-boundary/tag-browser-nix128-install-results.json)
- [aMule实机High ID与Kad OK验收通过，公网TCP4662可达；清理41条微信映射，其他23条保留，路由表64→26，本轮无需再次rerun。](010-host-configuration/tasks.md#amule-安装与网络引导阶段-am2026-11-04) [DiskTree图形版构建通过，待手动应用试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [第二轮清理后系统盘74%、可用约106.8GiB，再释放约61.7GiB；已清回收站、旧验收图片和闲置测试目录。源码、聊天记录、发布回滚产物、历史系统代与数据盘保留，详细记录见AGENTS第七节。](010-host-configuration/tasks.md#第二轮大项清理2026-11-16)

## 后续计划
- [输入法实现与正式发行交付已转trime-mobile；旧包退役和当前状态见对应产品，历史QA试用不再作为当前安装状态。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [用户试用正式手机/网页知识卡；PC桌面系统候选需用户手动激活。](010-host-configuration/tasks.md#android-同文中文九宫格阶段-tr2026-11-10)
- [PC nix.128锁定已更新，待用户手动rerun及完整重开，复测页面根、刷新与设置；整体三端验收与真实日常体验另列。](014-application-entry-boundary/tasks.md)
- [手动试用DiskTree（DT3）；aMule阶段AM已完成，无需再次rerun，微信长期映射配额未配置。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [Tag Browser nix.128已补127遗漏的合法根目录最终校验，并通过实际Firefox读取恢复保护；待用户更新后日常复测，配套服务未激活。](014-application-entry-boundary/tag-browser-nix128-install-results.json)
- [Codex连接与插件权限修复已验收；此前历史会话维护的高I/O不等同本轮两项问题。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-16 · Use verified nix.127 browser recovery release · `8ca241a`
- 2026-11-16 · Use verified nix.126 interactive local browsing sidebar · `50253c0`
- 2026-11-16 · Install verified nix.125 shared startup fix without changing the browser engine · `58e798a`
- 2026-11-16 · 清空回收站并回收旧验收渲染产物 · `b8319ea`
- 2026-11-16 · 回收闲置构建缓存并核对镜像与系统回滚保留 · `8f4fb74`
- 2026-11-16 · Update browser startup release overview · `68ca8ce`
- 2026-11-16 · Use local-first nix.124 browser and validate full-matrix bundle evidence · `bc6e3ee`
- 2026-11-16 · Update nix.121 delivery overview · `59a8859`
<!-- recent-commits:end -->
