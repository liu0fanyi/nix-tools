# Nix 配置与发布工具

## 当前情况
- [401修复按产品037增量证据上线PC/NUC三项核心，原更新回退6项通过；两端激活约100秒，实际读回核验约232秒。保持严格签名和数据；另已补上线浏览状态别名冲突前端，真实PDF刷新待确认。](014-application-entry-boundary/tasks.md)
- [DiskTree图形版0.11.0已固定官方包，Niri样例窗口及完整系统/HM构建通过，待用户手动应用并试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [PC/NUC规范三入口与严格签名已实际切换，数据库/关系/路径和原开机守卫核验通过；nix.107签名缓存、五应用精确缓存及完整PC/HM候选通过，临时恢复绑定已移除，用户系统安装仍自行执行。](014-application-entry-boundary/canonical-namespace-publication-results.json)

## 后续计划
- [手动应用DiskTree配置并试用图形界面（DT3）。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-02 · Refresh infrastructure overview after incremental rollout · `d52a00c`
- 2026-11-01 · Summarize completed canonical workspace rollout and desktop candidate · `d863b4c`
- 2026-11-01 · Finish strict paired namespace cutover and require entry compatibility on updates · `0030d45`
- 2026-11-01 · Prepare signed nix.107 desktop candidate for canonical workspace roots · `95fe114`
- 2026-11-01 · Include the canonical card library client in the desktop candidate · `ac550c8`
- 2026-11-01 · Reclaim stale Codex plugin staging and unused runtime cache · `adfd5ba`
- 2026-11-01 · Prepare signed nix.106 browser installation for canonical roots · `40d1e5e`
- 2026-11-01 · Root the staged core package with prepared namespace inputs · `2e5b132`
<!-- recent-commits:end -->
