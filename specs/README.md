# Nix 配置与发布工具

## 当前情况
- [nix.111切页与PDF筛选修复已私有发行，精确签名缓存与完整PC/HM候选核验通过；PC/NUC网页上线，原后端/签名/数据/独立应用保留，仅更新浏览器消费锁，未系统switch。](014-application-entry-boundary/tag-browser-nix111-install-results.json)
- [组合保护网用于固定前端交付：12项实际组合与6项隔离回退通过，任务夹具路径修正后完整重跑且保留原失败日志。](014-application-entry-boundary/tasks.md)
- [DiskTree图形版0.11.0已固定官方包，Niri样例窗口及完整系统/HM构建通过，待用户手动应用并试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)

## 后续计划
- [用户手动应用nix.111，正常完整重开确认版本；真实日常目录体验另行验收。](014-application-entry-boundary/tasks.md)
- [手动应用DiskTree配置并试用图形界面（DT3）。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-03 · Pin signed nix.111 and verify paired reader desktop candidate · `4dfcf02`
- 2026-11-03 · Refresh overview after signed nix.110 desktop candidate · `bd62b7f`
- 2026-11-03 · Pin signed nix.110 and verify full desktop candidate with endpoint frontends · `9937d37`
- 2026-11-03 · Summarize live EdgeOne checks and pending authenticated PDF verification · `a869731`
- 2026-11-03 · Verify live EdgeOne response lengths ranges and anonymous authorization · `037fccb`
- 2026-11-03 · Summarize frontend rollout and pending EdgeOne console update · `92f5ddb`
- 2026-11-03 · Summarize pending NAS edge response verification · `61ae389`
- 2026-11-03 · Preserve identity response lengths for PDF range support · `6a2c486`
<!-- recent-commits:end -->
