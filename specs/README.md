# Nix 配置与发布工具

## 当前情况
- 常规PC／NUC更新以用户当轮“上线”为切换授权，不再追加保存关闭问答；既有预演、回退、备份与实际验收保持。
- 维护工作站、NUC 发布和桌面应用缓存；Tag Browser nix.86及五个桌面应用升级缓存、完整PC/HM候选均已核验；本轮PC／NUC配套前端切换已验收。知识卡固定前端装配已兼容本地WASM/字体并通过预演，未切换服务。
- 32个非xiaoqiang工程已统一为projects总纲；[既有菜谱快照与WebP封面验收完成，成品留本机。](010-host-configuration/tasks.md)

## 后续计划
- [按后续实际变更维护项目总纲。](001-spec-driven-workflow/tasks.md)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-10-27 · Pin Tag Browser nix.86 and verify full desktop upgrade candidate · `2962a4b`
- 2026-10-27 · Summarize verified nix.85 consumer and manual installation step · `e263e50`
- 2026-10-27 · Pin Tag Browser nix.85 and verify full desktop upgrade candidate · `48867f6`
- 2026-10-27 · Summarize deployment authorization policy and current delivery state · `5a98674`
- 2026-10-27 · Accept explicit deployment requests as routine native switch authorization · `6c8e397`
- 2026-10-26 · Summarize verified nix.84 release and manual installation · `b7f3a2b`
- 2026-10-26 · Pin Tag Browser nix.84 and verify full desktop upgrade candidate · `837a7ad`
- 2026-10-26 · Summarize verified nix.83 desktop upgrade candidate · `a3c56a7`
<!-- recent-commits:end -->
