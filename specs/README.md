# Nix 配置与发布工具

## 当前情况
- [nix.112首屏主题与Markdown配套已发行，精确签名缓存及完整PC/HM候选通过；PC/NUC网页上线，350份组合资源与回退/数据认证保留通过，未系统switch。](014-application-entry-boundary/tag-browser-nix112-install-results.json) [组合保护网补齐三种保留应用根：13项单测、全350份HTTP摘要/12项实际组合及6项隔离回退通过，原断言和失败记录保留。](014-application-entry-boundary/tasks.md)
- [aMule实机High ID与Kad OK验收通过，公网TCP4662可达；清理41条微信映射，其他23条保留，路由表64→26，本轮无需再次rerun。](010-host-configuration/tasks.md#amule-安装与网络引导阶段-am2026-11-04) [DiskTree图形版构建通过，待手动应用试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [系统盘与/data安全清理：当前分别为64%/55%，CMT编译文件再回收约51.8GiB；原镜像标签、服务容器与源码保留；详细清理记录统一见AGENTS第七节。](010-host-configuration/tasks.md#cmt低延迟实验编译缓存清理阶段-sf2026-11-04)

## 后续计划
- [用户手动应用nix.112，正常完整重开确认版本；真实日常目录体验另行验收。](014-application-entry-boundary/tasks.md)
- [手动试用DiskTree（DT3）；aMule阶段AM已完成，无需再次rerun，微信长期映射配额未配置。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-04 · Add aMule with ED2K and Kad bootstrap on the PC · `d6d3e65`
- 2026-11-04 · Summarize verified nix.112 theme delivery · `f62968f`
- 2026-11-04 · Pin signed nix.112 and verify reserved application assets in release fixtures · `ab442cd`
- 2026-11-03 · Refresh overview after verified nix.111 candidate · `5114d6f`
- 2026-11-03 · Pin signed nix.111 and verify paired reader desktop candidate · `4dfcf02`
- 2026-11-03 · Refresh overview after signed nix.110 desktop candidate · `bd62b7f`
- 2026-11-03 · Pin signed nix.110 and verify full desktop candidate with endpoint frontends · `9937d37`
- 2026-11-03 · Summarize live EdgeOne checks and pending authenticated PDF verification · `a869731`
<!-- recent-commits:end -->
