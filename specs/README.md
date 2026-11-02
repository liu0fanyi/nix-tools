# Nix 配置与发布工具

## 当前情况
- [nix.108私有发行/精确签名缓存和完整PC/HM候选已核验；PC/NUC配套前端激活，原后端与严格签名保持。仅更新浏览器消费锁，未执行系统switch。](014-application-entry-boundary/tag-browser-nix108-install-results.json)
- [组合候选保护网已用于本轮固定前端交付：12项真实组合与输入漂移门槛保持，原更新回退6项通过。](016-application-release-bundle/tasks.md)
- [DiskTree图形版0.11.0已固定官方包，Niri样例窗口及完整系统/HM构建通过，待用户手动应用并试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)

## 后续计划
- [用户手动应用nix.108，正常完整重开确认版本；真实日常目录体验另行验收。](014-application-entry-boundary/tasks.md#浏览器nix108与配套前端交付)
- [手动应用DiskTree配置并试用图形界面（DT3）。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-02 · Pin signed nix.108 and record verified PC and NUC companion rollout · `0bfc8ab`
- 2026-11-02 · Require real frontend and backend combination evidence before bundle preparation · `da0cb27`
- 2026-11-02 · Refresh infrastructure overview after incremental rollout · `d52a00c`
- 2026-11-01 · Summarize completed canonical workspace rollout and desktop candidate · `d863b4c`
- 2026-11-01 · Finish strict paired namespace cutover and require entry compatibility on updates · `0030d45`
- 2026-11-01 · Prepare signed nix.107 desktop candidate for canonical workspace roots · `95fe114`
- 2026-11-01 · Include the canonical card library client in the desktop candidate · `ac550c8`
- 2026-11-01 · Reclaim stale Codex plugin staging and unused runtime cache · `adfd5ba`
<!-- recent-commits:end -->
