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
- [x] P4 链接/技能/发布边界回归、各仓白名单提交及已配置远程推送。
- [x] P5 新总纲与索引上传 NUC、摘要/权限及完整性核验。
- [x] P6 旧工程资料精确备份校验后清理，验证个人文件与原专用发布区不变，更新收尾记录。

当前6/6，剩余0项。32份总纲及索引已发布并逐文件校验；旧52项工程资料备份后清理，36项个人资料保护项不变。26个已配置远程的产品完成推送，6个无远程产品仅本地提交。12项工具/清理测试及共享规则链接检查通过。收尾证据见[结果](workspace-overview-results.json)。全工程仅进度文档与同步工具调整，不做产品部署/硬件操作，不新建远程。已识别32个产品来源；关联worktree和附属源码不重复作为工程。

用户纠正范围后：xiaoqiang已排除，误加的10份本地进度总纲以反向提交恢复；原dufs专用发布区未触碰，新增projects摘要移除。此纠正不启动Gitee权限处理或任何产品发布。

用户最终指定网页根目录 `#/projects?location=default`：发布目标修正为 `/home/liou/dufs-lan/projects/`，旧误放的 `todos/projects` 33份Markdown校验后迁移并移除空目录。共享技能、注册表、发布白名单和各README入口同步修正，xiaoqiang排除与个人资料保护不变。

## 文档规则收尾（本轮唯一阶段计数）

- [x] G1 扫描32个非xiaoqiang产品的现行操作规则、constitution、相关规格及同步入口。
- [x] G2 将旧全量镜像/旧白名单改为共享技能与中央登记，历史验收保留事实且明确不再执行旧步骤。
- [ ] G3 白名单差异、链接、目标和xiaoqiang未变核验，提交推送后同步根projects摘要。

当前2/3，剩余G3核验、提交及摘要同步；无产品部署、硬件操作、用户资料清理或xiaoqiang修改。
