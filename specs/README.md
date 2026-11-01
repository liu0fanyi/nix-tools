# Nix 配置与发布工具

## 当前情况
- [系统盘已完成安全清理，使用率94%→86%、可用约57G；活跃构建期间保留Podman，操作记录见AGENTS第七节。](010-host-configuration/tasks.md#系统盘安全清理阶段-sc2026-11-01)
- [DiskTree图形版0.11.0已固定官方包，Niri样例窗口及完整系统/HM构建通过，待用户手动应用并试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [规范虚拟根切换事务已实现，16项事务测试和原发行器3项通过，两端服务单元候选未激活；Tag Browser nix.105及PC/NUC配套已发行：本机打开、PC Home及NUC17根可用；CI签名/五应用缓存和完整PC/HM候选通过，用户系统安装待执行。](014-application-entry-boundary/tag-browser-nix105-install-results.json)

## 后续计划
- [手动应用DiskTree配置并试用图形界面（DT3）。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-01 · Reclaim stale Codex plugin staging and unused runtime cache · `adfd5ba`
- 2026-11-01 · Prepare signed nix.106 browser installation for canonical roots · `40d1e5e`
- 2026-11-01 · Root the staged core package with prepared namespace inputs · `2e5b132`
- 2026-11-01 · Require the canonical-capable core before preparing path migration · `d601088`
- 2026-11-01 · Publish browser path migration records only after database commit · `a1856f2`
- 2026-11-01 · Count the independent learning map among active Bevy repositories · `b80aafe`
- 2026-11-01 · Coordinate canonical workspace cutovers without restoring databases · `f098f53`
- 2026-11-01 · Register the independent directory learning map project · `3e5e465`
<!-- recent-commits:end -->
