# Nix 配置与发布工具

## 当前情况
- [手机出站配对与签名文件请求的原生网关白名单已准备并通过 Edge/Caddy专项；未发布，须与具强制Peer签名的新后端按序激活，不能单独扩大公网路由。](014-application-entry-boundary/tasks.md)
- [学习地图独立登记已按037增量候选启用；配置与启动保护摘要同事务切换，后续14文件静态发布不重启，用户学习资料保持。](017-independent-learning-map/tasks.md)
- [定制Trime已由独立产品正式签名发行3.3.14，输入/更新按钮通过；旧原版与知识卡QA已按用户明确授权双份备份后退役，当前默认定制输入法保留。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [知识卡0.1.5字号已发布PC可信缓存/消费者与Android双渠道；完整PC/内嵌HM候选通过，手机未安装本轮、用户自行rerun，网页/后端与Helix外部改动保持。](014-application-entry-boundary/tasks.md)
- [Codex桌面26.1103.31037修复已实机生效：不可达主机停止自动重连，NUC保持开启；6个内置插件成功物化并复用，无新增权限错误，聊天记录未动。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [Tag Browser nix.115已发行，固定内核及可信签名缓存核对通过；仅浏览器消费锁更新，完整PC/HM、菜单／MIME／五原生服务模板和恢复顺序通过，外部Helix改动保留；待用户手动rerun，未执行系统switch。](014-application-entry-boundary/tag-browser-nix115-install-results.json)
- [aMule实机High ID与Kad OK验收通过，公网TCP4662可达；清理41条微信映射，其他23条保留，路由表64→26，本轮无需再次rerun。](010-host-configuration/tasks.md#amule-安装与网络引导阶段-am2026-11-04) [DiskTree图形版构建通过，待手动应用试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [系统盘与/data安全清理：当前分别为64%/55%，CMT编译文件再回收约51.8GiB；原镜像标签、服务容器与源码保留；详细清理记录统一见AGENTS第七节。](010-host-configuration/tasks.md#cmt低延迟实验编译缓存清理阶段-sf2026-11-04)

## 后续计划
- [输入法实现与正式发行交付已转trime-mobile；旧包退役和当前状态见对应产品，历史QA试用不再作为当前安装状态。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [用户试用正式手机/网页知识卡；PC桌面系统候选需用户手动激活。](010-host-configuration/tasks.md#android-同文中文九宫格阶段-tr2026-11-10)
- [PC nix.115消费候选已通过，待用户手动rerun及正常完整重开；整体三端验收与真实日常体验另列。](014-application-entry-boundary/tasks.md)
- [手动试用DiskTree（DT3）；aMule阶段AM已完成，无需再次rerun，微信长期映射配额未配置。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [Codex连接与插件权限修复已验收；此前历史会话维护的高I/O不等同本轮两项问题。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-14 · release: consume verified Knowledge Cards 0.1.5 font controls · `501c1e4`
- 2026-11-14 · Refresh nix.115 installation overview · `96980ef`
- 2026-11-14 · Update Tag Browser consumer to signed nix.115 release · `da6027f`
- 2026-11-14 · Refresh mobile peer gateway preparation overview · `ceae42f`
- 2026-11-14 · Prepare bounded mobile peer routes behind mandatory backend signatures · `3366bb8`
- 2026-11-13 · Refresh learning-map release status overview · `f678148`
- 2026-11-13 · Enable learning-map registration with atomic startup digest updates · `14da43b`
- 2026-11-13 · Refresh learning static delivery status without enabling new registration · `6a0e1bc`
<!-- recent-commits:end -->
