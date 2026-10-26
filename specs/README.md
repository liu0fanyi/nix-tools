# Nix 配置与发布工具

## 当前情况
- 维护工作站、NUC 发布和桌面应用缓存；Tag Browser nix.83及五个桌面应用升级缓存、完整PC/HM候选均已核验。知识卡固定前端装配已兼容本地WASM/字体并通过预演，未切换服务。
- 32个非xiaoqiang工程已统一为 projects Markdown 总纲，旧工程镜像已备份清理。

- [既有 B 站菜谱快照全量验收完成，网页封面已压缩为 WebP，成品留本机。](010-host-configuration/tasks.md)

## 后续计划
- [按后续实际变更维护项目总纲。](001-spec-driven-workflow/tasks.md)

## 待处理问题
- [用户系统安装与真实窗口验收仍与制品发行分开记录。](014-application-entry-boundary/tasks.md)

- [菜谱食材别名尚未全面归一，整理结果仍是 AI 草稿。](010-host-configuration/tasks.md)

## 最近变化
<!-- recent-commits:start -->
- 2026-10-26 · Pin Tag Browser nix.83 and verify desktop upgrade candidate · `e361c8e`
- 2026-10-26 · Register course library progress summary · `8ff75c8`
- 2026-10-26 · Summarize fixed knowledge card artifact support · `80c1a8f`
- 2026-10-26 · Allow packaged Markdown WASM and fonts in knowledge card frontends · `0858838`
- 2026-10-26 · Compress recipe display covers as resumable WebP derivatives · `da21156`
- 2026-10-26 · fix: 项目总纲发布到用户指定的根 projects 目录 · `62b934a`
- 2026-10-26 · fix: 未推送的总纲引用不生成失效 Git 链接 · `bb4f587`
- 2026-10-26 · feat: 用共享技能联动 Spec 与 Markdown 项目总纲 · `1116fc0`
<!-- recent-commits:end -->
