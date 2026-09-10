# 任务清单：001-spec-driven-workflow

- [x] 1. 建立并确立项目宪法 `.specify/memory/constitution.md` <!-- id: 1 -->
- [x] 2. 重构根目录 `AGENTS.md` 为 6 大规范章节，明确 PC 环境角色与状态镜像协议 <!-- id: 2 -->
- [x] 3. 删除冗余的 `deploy/AGENTS.md` 消除重复维护风险 <!-- id: 3 -->
- [x] 4. 创建 `deploy/docs/build-agent-guide.md` 并对齐内容 <!-- id: 4 -->
- [x] 5. 编写 `scripts/sync-todos.py` 实现任务扫描、看板生成与 rsync 同步 <!-- id: 5 -->
- [x] 6. 在 `justfile` 中注册 `sync-todos` 命令 <!-- id: 6 -->
- [x] 7. 执行 `just test` 验证既有测试不受影响 <!-- id: 7 -->
- [x] 8. 执行 `just sync-todos` 完成对 NUC 远端的首次全量状态镜像 <!-- id: 8 -->
- [x] 9. 验收 NUC 端 `todos/nix-tools/` 的 `specs/`、`docs/` 及 `README.md` <!-- id: 9 -->
