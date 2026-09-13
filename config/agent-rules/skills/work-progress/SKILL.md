---
name: work-progress
description: 维护本地仓库 specs 中的规格与任务进度，并通过仓库 sync-todos 入口镜像到 NUC 项目进展。适用于工作区项目状态更新与规格文档同步，不用于直接编辑远端平行计划或部署应用。
---

# 工作进展与 Spec 镜像

本技能由 nix-tools 的 `config/agent-rules/skills/work-progress/` 管理，
安装位置通过符号链接引用；修改后在 nix-tools 提交，不另建独立副本。

各产品仓库内的 `specs/` 是需求、方案与任务状态的权威源，NUC 仅供镜像查阅。
目标由项目规则决定：一般工程使用 `dufs-lan/todos/<项目>/`；
`/data/project/xiaoqiang/` 所有工程仅使用 `/home/liou/dufs/<工程发布目录>/`，
禁止 todos 双镜像。既有特殊目录名和文档白名单按子仓库规则，不按本地名字猜目标。
`/data/project` 是多仓库工作区，不在根目录或 nix-tools 中代管其他产品规格。

## 维护本地权威源

接手或切换仓库时，先读适用的上级及目标仓库 `AGENTS.md`、`.specify/memory/constitution.md` 和相关
`specs/NNN-<feature>/`，核对工作树与当前任务。规格由 Spec Kit 流程管理：
`/speckit-specify` → `plan` → `tasks` → `implement` → `converge`。

- `spec.md`：需求与验收标准；`plan.md`：技术方案；`tasks.md`：任务及完成勾选。
- 接口与数据契约放特性目录的 `contracts/`；可判定的长期约束放 constitution。
- 项目说明与参考索引留在仓库 `README.md`、`AGENTS.md`、`docs/`。
- 按已验证事实更新进度，区分实现、构建、部署、实机验收和提交/推送；不把待验收任务勾成完成。
- 不再通过 SSH 编辑远端项目 `plan.md` 或 `a-next.md` 来安排该仓库工作，
  不另建与 specs 竞争的计划。跨项目根部资料按工作区规则查阅，不能因采用新流程自动删除。

## 同步入口与实际行为

已核验的参考实现：
[/home/liou/nix-tools/scripts/sync-todos.py](/home/liou/nix-tools/scripts/sync-todos.py)，
入口定义于 [/home/liou/nix-tools/justfile](/home/liou/nix-tools/justfile)。
使用前读取目标仓库的实际 recipe 和脚本，确认源目录、目的目录及删除范围。

nix-tools 的命令在 `/home/liou/nix-tools` 执行：

```bash
devenv shell -- just sync-todos
```

已进入其开发环境时可用 `just sync-todos`。代码或任务状态变动后，按仓库约定同步，
不要求先部署应用。该脚本的真实行为是：

- 源仓库由脚本自身位置确定；远端固定为 `todos/nix-tools/`，没有通用项目参数。
  从其他工作目录运行它仍只同步 nix-tools，不能用它替代其他项目的同步入口。
- 本地 `specs/` 存在时，用 `rsync --delete` 镜像到远端项目的 `specs/`。
  先确认该目录只含本地权威源的镜像；不得把删除范围扩大到项目根或 `todos/`。
- `docs/` 与 `deploy/docs/` 依次增量同步到同一远端 `docs/`，不带 `--delete`；
  当前脚本遇两者同名文件会拒绝同步，旧远端文档不会自动清理。
- 从各特性 `spec.md` 的一级标题及 `tasks.md` 勾选项生成临时 README 看板，
  上传到远端 `README.md`，不覆盖本地 README。任务列显示已勾选/总数，
  缺少 tasks.md 时显示“未建任务清单”；计数不证明功能验收完成。
- 传输使用 `--chmod=D755,F644`；同步 constitution、AGENTS 和仓库/部署 README 入口，
  不生成旧格式 `plan.md`。支持 `--dry-run` 本地预演，正式同步后按 checksum 回查。
  这是 nix-tools 的白名单，不可套到明确禁止上传规则文件的 xiaoqiang 工程。

其他仓库优先使用其已存在且经过核对的同步入口；若尚无入口，先在该仓库按本次授权范围
适配同步流程与项目路径，再执行。不要直接运行 nix-tools 脚本并宣称已同步其他项目。

## 核验与旧流程边界

执行前简述本轮范围、禁令与精确写入目标，核对实际脚本和可用的 dry-run；
用户已确认的范围不重复询问。同步结束检查退出状态，回读本仓库指定的阅读入口和
本次变动的 specs/docs，核对内容、链接和权限；同时核对目标合法、删除范围及
是否存在任务范围外写入。内容摘要一致不能代替目的地与边界验收。
失败时定位具体步骤；脚本不是原子发布，失败前可能已有部分文件同步，不宣称全部完成。
文档镜像不需要构建或部署 Planner、DUFS 或产品应用。

旧 `scripts/work_file.py` 仅是遗留的远端 Markdown 编辑器，不属于当前维护流程，
不得用它更新 specs 项目的状态。旧远端 plan、资料、备份及画布关联不由本技能自动迁移或删除；
只有另行明确的迁移任务才处理这些内容。
