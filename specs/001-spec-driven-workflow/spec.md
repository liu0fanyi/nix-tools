# 特性规格：nix-tools Spec-Driven 研发体系规范化与远端状态镜像

- **编号**：`001`
- **标识**：`spec-driven-workflow`
- **状态**：`实施中 (In Progress)`
- **创建时间**：2026-09-10

---

## 一、背景与目标 (Context & Objectives)

此前 `nix-tools` 的任务与研发规划依赖远端 NUC 的扁平 Markdown 便签（`a-next.md` / `a-observe.md` / `a-done.md`），不仅与仓库代码版本脱节，也无法利用现代化的 Spec-Driven（规格驱动）自动化开发工具。

本特性的目标是：
1. 正式确立 `nix-tools` 的 Spec Kit 规范化研发流程，建立项目宪法（`constitution.md`）与操作手册（`AGENTS.md`）。
2. 将本地 `specs/` 确立为需求、方案与任务拆解的唯一权威事实源。
3. 建立自动化的状态镜像协议与命令（`just sync-todos`），使开发过程中的任务清单与工程文档自动增量同步到 NUC `todos/nix-tools/`，供云端 DUFS 和项目进展看板实时查阅。

---

## 二、用户场景与体验 (User Scenarios)

1. **场景 1：任务规划与启动**：
   - 用户与 Agent 启动新任务或重构时，统一在本地仓库通过 Spec Kit 生成规范的 `specs/NNN-<feature>/`，包含 `spec.md`（需求与验收标准）、`plan.md`（技术架构方案）、`tasks.md`（原子任务清单）。
2. **场景 2：状态自动镜像到云端**：
   - Agent 每次推进任务（勾选 `tasks.md`）或完成代码提交时，执行 `just sync-todos`。
   - 用户在手机或远程电脑打开 NUC 的 DUFS（`todos/nix-tools/`）时，能够立刻看到清晰的任务看板和实时的完成度百分比，无需登录本地终端即可了解项目状态。
3. **场景 3：无缝对接云端项目进展看板**：
   - 自动生成的看板与 `plan.md` 兼容现有的 `bevy-project-planner`，使 NUC 的“项目进展”应用能自动读取 `nix-tools` 的任务卡片与进展条。

---

## 三、验收标准 (Success Criteria)

- [x] **CR-1**：`.specify/memory/constitution.md` 经批准生效，包含 PC 权威构建、三级安全隔离、镜像真实性、单源 Spec 与同步边界五项核心原则。
- [x] **CR-2**：根目录 `AGENTS.md` 紧凑重构，删除冗余的 `deploy/AGENTS.md`。
- [x] **CR-3**：提供可重复运行的 `just sync-todos` 命令，能将 `specs/`、`docs/` 及生成的汇总看板可靠增量同步至 `liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/`。
- [x] **CR-4**：同步到远端后的目录包含结构化的 `specs/` 镜像以及符合旧前端格式的 `plan.md` 兼容层。
