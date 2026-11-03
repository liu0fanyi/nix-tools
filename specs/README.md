# Nix 配置与发布工具

## 当前情况
- [PC/NUC选框与EPUB前端上线并核验数据/认证保留；EdgeOne用户已部署，18次公网只读检查通过；登录后PDF响应和SSR仍待核验。](016-application-release-bundle/selection-range-results.json)
- [nix.110自动入口/统一底栏私有发行、精确签名缓存和完整PC/HM候选已核验；PC/NUC配套前端上线，原后端/严格签名与数据保持，仅更新浏览器消费锁，未系统switch。](014-application-entry-boundary/tag-browser-nix110-install-results.json)
- [组合候选保护网已用于本轮固定前端交付：12项真实组合与输入漂移门槛保持，原更新回退6项通过。](016-application-release-bundle/tasks.md)
- [DiskTree图形版0.11.0已固定官方包，Niri样例窗口及完整系统/HM构建通过，待用户手动应用并试用。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)

## 后续计划
- [用户手动应用nix.110，正常完整重开确认版本；真实日常目录体验另行验收。](014-application-entry-boundary/tasks.md#自动入口及统一底栏nix110配套交付)
- [手动应用DiskTree配置并试用图形界面（DT3）。](010-host-configuration/tasks.md#disktree-图形版安装阶段-dt2026-11-01)
- [在文件管理器双击文档和表格确认默认应用（OF3）。](010-host-configuration/tasks.md#文档与表格默认应用修复阶段-of2026-10-31)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-11-03 · Verify live EdgeOne response lengths ranges and anonymous authorization · `037fccb`
- 2026-11-03 · Summarize frontend rollout and pending EdgeOne console update · `92f5ddb`
- 2026-11-03 · Summarize pending NAS edge response verification · `61ae389`
- 2026-11-03 · Preserve identity response lengths for PDF range support · `6a2c486`
- 2026-11-03 · Refresh infrastructure overview after nix.109 delivery · `eeddace`
- 2026-11-03 · Pin signed nix.109 and verify desktop candidate with live semantic frontends · `c15c3c1`
- 2026-11-02 · Refresh verified nix.108 delivery overview · `00b5f0e`
- 2026-11-02 · Pin signed nix.108 and record verified PC and NUC companion rollout · `0bfc8ab`
<!-- recent-commits:end -->
