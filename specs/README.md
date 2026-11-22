# Nix 配置与发布工具

## 当前情况
- [本机可在 Fuzzel 搜索「系统监控」，也可通过 `just system-monitor` 打开浮窗。首行显示整机 CPU、内存与系统盘 I/O。](010-host-configuration/tasks.md#系统盘与进程监控浮窗2026-11-21)
- [Tag Browser CPU 滚动采样的完整系统与 Home Manager 构建通过，待用户应用并确认本机日志。](010-host-configuration/tasks.md#tag-browser-cpu-滚动采样tc2026-11-20)
- [缺少单个登记来源时其余工程仍可同步，Trime 旧摘要保留，已补同步三份工程总纲。](001-spec-driven-workflow/tasks.md#缺失来源的同步隔离)
- [Screen Mark 0.2.0 已签名发行，完整 PC/HM 构建通过，待用户应用桌面更新。](010-host-configuration/tasks.md#screen-mark-020-发行)
- [知识卡 0.1.16 带 Helix 诊断及截图漏转自动重试，PC 安装候选已验证。](014-application-entry-boundary/tasks.md#知识卡-0116)
- [Tag Browser nix.140 的签名、PC 配置锁及完整系统构建均通过。](014-application-entry-boundary/tasks.md#tag-browser-nix140)
- [共享 Helix 已上线 PC/NUC 前端，知识卡 0.1.10 固定到 PC 安装配置，完整系统候选已验证。](014-application-entry-boundary/tasks.md#共享-helix-正式发布2026-11-19)
- [NUC 私有 Workspace AI 已上线，知识卡 0.1.9 和 Tag Browser nix.133 的 PC 安装配置与完整候选通过验收。](014-application-entry-boundary/tasks.md#nuc-workspace-ai-与桌面应用发行2026-11-19)
- [Helix软换行双宽字符补丁的完整PC/HM构建通过；Agent入口已移除历史流水并精简为操作规则，构建指南改为导航。](010-host-configuration/tasks.md#helix-补丁与-agent-入口精简hp2026-11-19)
- [Holytech已改用完整原始订阅格式并热重载，自动更新保留REALITY公钥；正式台湾A/B测速371/467ms，当前仍选择DMIT。](010-host-configuration/tasks.md#holytech-订阅-reality-参数恢复hu2026-11-19)
- [ClashTUI已固定含订阅节点测速修复的0.3.2开发版；355项测试、真实节点延迟显示及完整PC/HM构建通过，待用户手动应用。](010-host-configuration/tasks.md#clashtui-订阅节点延迟显示更新ct2026-11-18)
- [工作站工具升级及移除 Cursor 的完整系统和 Home Manager 候选构建通过，PC 已运行对应系统，待日常桌面验收。dsh 插件已实机更新。Podman 6 按用户指示暂缓。](010-host-configuration/tasks.md#工作站工具更新与移除-cursor2026-11-18)
- [Z-Library CLI v0.0.14已接入Nix，独立包、完整PC/HM及网络检查通过；待用户手动应用和登录验收。](010-host-configuration/tasks.md#z-library-终端客户端-nix-接入阶段-zl2026-11-15)
- [Android局域网配对已补齐NUC现用网关两条固定POST路径并reload，真实申请/审批成功；公网移动白名单仍未部署，不扩大外网路由。](014-application-entry-boundary/tasks.md)
- [学习地图独立登记已按037增量候选启用；配置与启动保护摘要同事务切换，后续14文件静态发布不重启，用户学习资料保持。](017-independent-learning-map/tasks.md)
- [定制Trime已由独立产品正式签名发行3.3.14，输入/更新按钮通过；旧原版与知识卡QA已按用户明确授权双份备份后退役，当前默认定制输入法保留。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [知识卡0.1.6预览/公式及PC数学/识图入口已发布可信缓存与Android双渠道，完整PC/HM候选通过；未安装手机或switch，网页事务待本次保存确认，后端及Helix外部改动保持。](014-application-entry-boundary/tasks.md)
- [Codex桌面26.1103.31037修复已实机生效：不可达主机停止自动重连，NUC保持开启；6个内置插件成功物化并复用，无新增权限错误，聊天记录未动。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [Tag Browser nix.132已发行并构建完整系统候选；统一过滤器Web已激活PC/NUC，实际资产/组合/认证/回退通过，现用后端保持，无system switch。](014-application-entry-boundary/tag-browser-nix132-install-results.json)
- [aMule实机High ID与Kad OK验收通过，公网TCP4662可达；清理41条微信映射，其他23条保留，路由表64→26，本轮无需再次rerun。](010-host-configuration/tasks.md#amule-安装与网络引导阶段-am2026-11-04) [DiskTree图形版构建通过，待手动应用试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [已清理60份旧 Tag Browser 验收档案，系统盘可用约119.9GiB，/data上一轮清理后可用约145.4GiB。](010-host-configuration/tasks.md#tag-browser-旧验收档案清理2026-11-18)

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
- 2026-11-22 · Pin signed Tag Browser nix.140 for the PC · `ee8588d`
- 2026-11-21 · Launch System Monitor from Fuzzel and show machine totals · `916b008`
- 2026-11-21 · Make the monitor text larger and the window translucent · `e828d2d`
- 2026-11-21 · Open a floating system disk and process monitor · `540551a`
- 2026-11-20 · Pin signed Tag Browser nix.139 for the PC · `df1b79e`
- 2026-11-20 · Update project overview for Tag Browser CPU sampling · `111365b`
- 2026-11-20 · Keep a bounded local CPU history for Tag Browser · `d855284`
- 2026-11-20 · Update project overview sync status · `14ee26f`
<!-- recent-commits:end -->
