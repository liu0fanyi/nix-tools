# Nix 配置与发布工具

## 当前情况
- [DiskTree图形版0.11.0已固定官方包，Niri样例窗口及完整系统/HM构建通过，待用户手动应用并试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [DOCX等文档默认AbiWord、表格默认Gnumeric已即时修复，14项关联及完整系统/HM构建验证通过，待实际双击确认。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [Tag Browser nix.105及PC/NUC配套已发行：本机打开、PC Home及NUC17根可用；CI签名/五应用缓存和完整PC/HM候选通过，用户系统安装待执行。](014-application-entry-boundary/tag-browser-nix105-install-results.json)

## 后续计划
- [手动应用DiskTree配置并试用图形界面（DT3）。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-01 · Validate the global NUC startup binding before directory writes · `96df2d9`
- 2026-11-01 · Use verified browser directory transactions for NUC shared roots · `a481e2f`
- 2026-11-01 · Add DiskTree graphical disk usage analyzer · `443c0b3`
- 2026-10-31 · Use AbiWord and Gnumeric as default document and spreadsheet editors · `1916917`
- 2026-10-31 · Summarize verified nix.104 browser installation candidate · `a128358`
- 2026-10-31 · Update Tag Browser to nix.104 with verified installation and caches · `f5af860`
- 2026-10-31 · Summarize verified nix.103 browser delivery · `c55fa97`
- 2026-10-31 · Update Tag Browser to nix.103 with verified installation and caches · `525c446`
<!-- recent-commits:end -->
