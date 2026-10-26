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

## Markdown 总纲阶段（唯一跨仓计数）

- [x] M1 更新共享 work-progress 技能、工作区规则和可复用 Markdown/Git 工具；不逐项目添加 AGENTS。
- [x] M2 当前两仓总纲与 spec 联动、既有镜像入口使用总纲，DUFS 移除独立阅读器和目录接管。
- [x] M3 隔离工具/规则回归、技能校验及 DUFS WASM/Rust/private 构建与目录浏览验证。
- [x] M4 两仓本轮白名单提交推送、NUC Markdown 镜像及 checksum/链接/权限核验；前端上线另行执行。

当前开发与资料阶段4/4完成，剩余0项。共享技能/规则链接、5项工具测试与4项规则测试、技能校验、DUFS WASM/274项Rust/private构建与实际浏览验证通过；两仓已提交推送，NUC阅读入口及specs/docs镜像checksum、链接和权限核验通过。证据见[结果](markdown-overview-results.json)。生产前端仍为现用版本，独立按钮移除待后续发行；不代填上线验收。

## 全工作区总纲迁移（本轮唯一阶段计数）

- [x] P1 盘点当前项目、worktree、旧工程目录及个人资料保护范围。
- [x] P2 对照各仓现有规格/文档重写全部项目简短总纲，保留已有修改与未验收边界。
- [x] P3 更新共享技能、中央登记和旧同步入口，确保仅发布 projects 下 Markdown。
- [ ] P4 链接/技能/发布边界回归、各仓白名单提交及已配置远程推送。
- [ ] P5 新总纲与索引上传 NUC、摘要/权限及完整性核验。
- [ ] P6 旧工程资料精确备份校验后清理，验证个人文件与原专用发布区不变，更新收尾记录。

当前3/6，剩余P4提交与验证、P5发布、P6旧资料清理。全工程仅进度文档与同步工具调整，不做产品部署/硬件操作，不新建远程。已识别42个产品来源；关联worktree和附属源码不重复作为工程。
