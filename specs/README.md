# Nix 配置与发布工具

## 当前情况
- [dsh 已更新至 rc.5，专用官方 Node 与五个插件更新通过启动、PTY 及完整系统/HM 构建；持久入口待用户手动应用。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)
- [Helix 输入法恢复已通过构建、隔离验证和用户试用，当前配置方案验收完成。](010-host-configuration/tasks.md#helix-输入法配置试用阶段-hx)
- [Tag Browser nix.92及五应用缓存、完整PC/HM候选已核验；仅浏览器源码锁定更新，本轮无网页服务切换。](014-application-entry-boundary/row-state-install-results.json)

## 后续计划
- [手动应用 dsh 运行时修复并确认实际界面使用（DS3）。](010-host-configuration/tasks.md#dsh-更新与-nix-node-兼容修复阶段-ds2026-10-30)
- [按后续实际变更维护项目总纲。](001-spec-driven-workflow/tasks.md)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-10-30 · Fix dsh startup on NixOS with a dedicated official Node runtime · `6c69b72`
- 2026-10-29 · Stop atop background collection while preserving manual history replay · `d805862`
- 2026-10-29 · Fix Fcitx5 startup ordering and wait for its D-Bus controller · `ba1a2dc`
- 2026-10-29 · Refresh committed nix.92 installation overview · `a4829fe`
- 2026-10-29 · Pin Tag Browser nix.92 and verify signed application caches · `e08722e`
- 2026-10-29 · Restore insert input method when switching Helix modes · `d689e8a`
- 2026-10-29 · Refresh nix.91 installation overview · `147951a`
- 2026-10-29 · Pin Tag Browser nix.91 and verify paired frontend delivery · `283ae06`
<!-- recent-commits:end -->
