# Nix 配置与发布工具

## 当前情况
- [定制Trime已由独立产品正式签名发行3.3.14，输入/更新按钮通过；旧原版与知识卡QA已按用户明确授权双份备份后退役，当前默认定制输入法保留。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [知识卡0.1.1可信缓存/消费者与完整PC/HM候选通过，用户选择自己rerun；PC/NUC网页已精简上线，Android原证书同包更新及新发行渠道通过，后端/学习规划保持。](014-application-entry-boundary/tasks.md)
- [Codex桌面26.1103.31037修复已实机生效：不可达主机停止自动重连，NUC保持开启；6个内置插件成功物化并复用，无新增权限错误，聊天记录未动。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [nix.112首屏主题与Markdown配套已发行，精确签名缓存及完整PC/HM候选通过；PC/NUC网页上线，350份组合资源与回退/数据认证保留通过，未系统switch。](014-application-entry-boundary/tag-browser-nix112-install-results.json) [组合保护网补齐三种保留应用根：13项单测、全350份HTTP摘要/12项实际组合及6项隔离回退通过，原断言和失败记录保留。](014-application-entry-boundary/tasks.md)
- [aMule实机High ID与Kad OK验收通过，公网TCP4662可达；清理41条微信映射，其他23条保留，路由表64→26，本轮无需再次rerun。](010-host-configuration/tasks.md#amule-安装与网络引导阶段-am2026-11-04) [DiskTree图形版构建通过，待手动应用试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [系统盘与/data安全清理：当前分别为64%/55%，CMT编译文件再回收约51.8GiB；原镜像标签、服务容器与源码保留；详细清理记录统一见AGENTS第七节。](010-host-configuration/tasks.md#cmt低延迟实验编译缓存清理阶段-sf2026-11-04)

## 后续计划
- [输入法实现与正式发行交付已转trime-mobile；旧包退役和当前状态见对应产品，历史QA试用不再作为当前安装状态。](010-host-configuration/tasks.md#trime正式发行与旧手机包退役2026-11-13状态)
- [用户试用正式手机/网页知识卡；PC桌面系统候选需用户手动激活。](010-host-configuration/tasks.md#android-同文中文九宫格阶段-tr2026-11-10)
- [用户手动应用nix.112，正常完整重开确认版本；真实日常目录体验另行验收。](014-application-entry-boundary/tasks.md)
- [手动试用DiskTree（DT3）；aMule阶段AM已完成，无需再次rerun，微信长期映射配额未配置。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [Codex连接与插件权限修复已验收；此前历史会话维护的高I/O不等同本轮两项问题。](010-host-configuration/tasks.md#codex-桌面卡顿排查与升级阶段-cx2026-11-06)
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-13 · Register Trime QA and record pending phone acceptance · `705cb8d`
- 2026-11-12 · Summarize Trime keyboard improvements and pending pinyin selection · `8d66a28`
- 2026-11-12 · Improve Trime vocabulary, symbols and Helix controls · `99fbdec`
- 2026-11-10 · Summarize the verified Knowledge Cards grid delivery · `f37d7da`
- 2026-11-10 · Pin Knowledge Cards with visible empty cursor and native scrolling · `e863577`
- 2026-11-10 · Summarize Knowledge Cards desktop and frontend delivery · `edf2fed`
- 2026-11-10 · Pin the verified Knowledge Cards desktop update · `0e7a9f3`
- 2026-11-10 · Summarize the Trime Helix QA verification · `fb7e16e`
<!-- recent-commits:end -->
