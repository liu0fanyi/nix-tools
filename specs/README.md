# Nix 配置与发布工具

## 当前情况
- [工作站工具升级及移除 Cursor 的完整系统和 Home Manager 候选构建通过，PC 已运行对应系统，待日常桌面验收。dsh 插件已实机更新。Podman 6 按用户指示暂缓。](010-host-configuration/tasks.md#工作站工具更新与移除-cursor2026-11-18)
- [Z-Library CLI v0.0.14已接入Nix，独立包、完整PC/HM及网络检查通过；待用户手动应用和登录验收。](010-host-configuration/tasks.md#z-library-终端客户端-nix-接入阶段-zl2026-11-15)
- [Android局域网配对已补齐NUC现用网关两条固定POST路径并reload，真实申请/审批成功；公网移动白名单仍未部署，不扩大外网路由。](014-application-entry-boundary/tasks.md)
- [学习地图独立登记已按037增量候选启用；配置与启动保护摘要同事务切换，后续14文件静态发布不重启，用户学习资料保持。](017-independent-learning-map/tasks.md)
- [定制Trime已由独立产品正式签名发行3.3.14，输入/更新按钮通过；旧原版与知识卡QA已按用户明确授权双份备份后退役，当前默认定制输入法保留。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [知识卡0.1.6预览/公式及PC数学/识图入口已发布可信缓存与Android双渠道，完整PC/HM候选通过；未安装手机或switch，网页事务待本次保存确认，后端及Helix外部改动保持。](014-application-entry-boundary/tasks.md)
- [Codex桌面26.1103.31037修复已实机生效：不可达主机停止自动重连，NUC保持开启；6个内置插件成功物化并复用，无新增权限错误，聊天记录未动。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [Tag Browser nix.132已发行并构建完整系统候选；统一过滤器Web已激活PC/NUC，实际资产/组合/认证/回退通过，现用后端保持，无system switch。](014-application-entry-boundary/tag-browser-nix132-install-results.json)
- [aMule实机High ID与Kad OK验收通过，公网TCP4662可达；清理41条微信映射，其他23条保留，路由表64→26，本轮无需再次rerun。](010-host-configuration/tasks.md#amule-安装与网络引导阶段-am2026-11-04) [DiskTree图形版构建通过，待手动应用试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [深度盘点后的优先清理完成，系统盘71%、可用116.5GiB，/data为67%、可用145.4GiB。镜像、源码和发布产物保留。](010-host-configuration/tasks.md#深度盘点后优先项清理2026-11-18)

## 后续计划
- [输入法实现与正式发行交付已转trime-mobile；旧包退役和当前状态见对应产品，历史QA试用不再作为当前安装状态。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [用户试用正式手机/网页知识卡；PC桌面系统候选需用户手动激活。](010-host-configuration/tasks.md#android-同文中文九宫格阶段-tr2026-11-10)
- [PC最终nix.132锁定已更新，待用户手动rerun及完整重开后试用过滤器；Web已生效，手机APK未更新。](014-application-entry-boundary/tag-browser-nix132-install-results.json)
- [手动试用DiskTree（DT3）；aMule阶段AM已完成，无需再次rerun，微信长期映射配额未配置。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [Tag Browser nix.128已补127遗漏的合法根目录最终校验，并通过实际Firefox读取恢复保护；待用户更新后日常复测，配套服务未激活。](014-application-entry-boundary/tag-browser-nix129-install-results.json)
- [Codex连接与插件权限修复已验收；此前历史会话维护的高I/O不等同本轮两项问题。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-18 · 清理旧构建层、日志和 Cargo 缓存 · `4251f6e`
- 2026-11-18 · 回收旧编译对象和工具下载缓存 · `7b33e98`
- 2026-11-18 · 回收工作站和数据盘的闲置构建缓存 · `98b322a`
- 2026-11-18 · 从工作站配置移除 Cursor · `32bd407`
- 2026-11-18 · 更新工作站浏览器、开发工具和同步客户端 · `2642f91`
- 2026-11-17 · Refresh nix.132 consumer delivery overview · `93285cb`
- 2026-11-17 · Pin signed nix.132 browser and record unified filter frontend activation · `34b03f9`
- 2026-11-17 · Refresh verified PDF cache delivery overview · `bd80837`
<!-- recent-commits:end -->
