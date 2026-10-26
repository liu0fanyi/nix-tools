> 当前阅读方式已由下方“Markdown 总纲”替代原任务看板与 Planner 兼容目标；旧验收只记录历史，不作为新实施要求。

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

## Markdown 总纲（当前需求）

用户取消独立项目进展页面，只阅读 Markdown。每个当前工作仓库维护 specs/README.md，简短概括当前情况、后续计划、待处理问题；计划引用已有 feature spec/tasks，Git 提供最多八条最近功能变化。不要知识卡整理功能，不批量初始化其他工程。

共享 work-progress 技能与工作区上级规则负责每次任务收尾的 Spec→总纲→Git→NUC 联动，无需逐仓添加 AGENTS。总纲与代码一起版本管理；远端 README 是阅读镜像。旧细节资料继续按各工程白名单同步，页面不再遍历 specs 或显示任务百分比。发布总纲不授予应用部署、停服或系统 switch 权限。

验收：工具能在隔离 Git 仓库提取/转义/过滤提交，拒绝越界路径与外链文件，修正移动后相对链接，dry-run 不写入，正式镜像只覆盖本项目 README 并 checksum 回查。DUFS 移除旧入口/资源/目录接管且原浏览能力保留；跨仓唯一阶段 M1–M4。

## 全工作区迁移（用户2026-10-26追加）

当前/data/project所有独立产品（包含Bevy，排除xiaoqiang；nix-tools通过本工作区worktree归入）按共享技能建立本地specs/README.md；同Git仓库不重复列worktree，附属共享应用归所属产品。新版NUC只放projects/<登记名>.md及README.md索引，不再复制所有spec细节。详细引用转换为已存在远程仓库的精确Git提交链接；无远程时不虚构链接，不新建远程。

删除旧todos根部工程镜像及明确的工程历史试验/备份：必须先生成精确名单、建立todos之外的私有备份并逐文件校验，再核对新32份总纲完整，之后清理。个人待办、学习资料、资产目录及所有运行文件/固件/安装包保留。xiaoqiang不参与本轮进度整理与projects发布，进度和专用资料均保持原规则。旧同步入口必须更新，防止旧目录重生；不需要逐项目添加AGENTS。

用户纠正范围后：xiaoqiang已排除，误加的10份本地进度总纲以反向提交恢复；原dufs专用发布区未触碰，新增projects摘要移除。此纠正不启动Gitee权限处理或任何产品发布。
