# Nix 配置与发布工具

## 当前情况
- [dsh 已更新至 rc.5，专用官方 Node 与五个插件更新通过启动、PTY 及完整系统/HM 构建；持久入口待用户手动应用。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)
- [嘉立创 EDA 4.1.93 固定包、完整系统/HM和实际入口核对通过，待用户手动应用与接口复测。](010-host-configuration/tasks.md#嘉立创-eda-41-升级阶段-ed4)
- [Tag Browser nix.94父标签/原生下载、五应用缓存和完整PC/HM候选已核验；仅浏览器输入锁更新，PC/NUC配套父级前端已切换，用户系统更新待执行。](014-application-entry-boundary/tag-browser-nix94-install-results.json)

## 后续计划
- [手动应用 EDA 4.1.93、保存后重开并复测网关及工程/ERC接口（ED4.3）。](010-host-configuration/tasks.md#嘉立创-eda-41-升级阶段-ed4)
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)
- [按后续实际变更维护项目总纲。](001-spec-driven-workflow/tasks.md)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-10-30 · Pin Tag Browser nix.94 and verify the complete desktop candidate · `f8f247a`
- 2026-10-30 · Refresh desktop overview for Tag Browser nix.93 · `dc141d8`
- 2026-10-30 · Pin Tag Browser nix.93 and verify full desktop installation candidate · `4b2bf2c`
- 2026-10-30 · Fix dsh startup on NixOS with a dedicated official Node runtime · `6c69b72`
- 2026-10-29 · Stop atop background collection while preserving manual history replay · `d805862`
- 2026-10-29 · Fix Fcitx5 startup ordering and wait for its D-Bus controller · `ba1a2dc`
- 2026-10-29 · Refresh committed nix.92 installation overview · `a4829fe`
- 2026-10-29 · Pin Tag Browser nix.92 and verify signed application caches · `e08722e`
<!-- recent-commits:end -->
