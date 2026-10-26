> 第一至三节是旧全量镜像方案，保留为历史记录，不得执行。当前实施以“全工作区迁移方案”、共享 work-progress 与中央登记为准；NUC只发布根 projects 的摘要与索引。

# 技术方案：nix-tools 研发规范化与状态镜像实现

- **关联特性**：`specs/001-spec-driven-workflow/spec.md`
- **版本**：1.0.0

---

## 一、架构设计 (Architecture Design)

```
[PC: liu-bigpc]                                [Remote: NUC (liou@nuc.local)]
/home/liou/nix-tools/                          /home/liou/dufs-lan/todos/nix-tools/
├── .specify/memory/constitution.md            ├── README.md (自动生成的总看板)
├── AGENTS.md (操作手册)                         ├── plan.md   (兼容 bevy-project-planner)
├── specs/                                     ├── specs/    (rsync 增量镜像)
│   └── 001-spec-driven-workflow/              │   └── 001-spec-driven-workflow/
│       ├── spec.md                            │       ├── spec.md
│       ├── plan.md                            │       ├── plan.md
│       └── tasks.md                           │       └── tasks.md
├── docs/ (工程文档) ───────────────────────────> ├── docs/     (rsync 增量镜像)
└── scripts/sync-todos.py                      └── edge-functions/
         │
         └── (执行 rsync -avz --delete 与看板渲染)
```

---

## 二、关键实现要点 (Implementation Details)

### 1. 状态看板生成器 (`scripts/sync-todos.py`)
- **扫描 `specs/` 目录**：
  - 遍历所有 `specs/NNN-*/` 子目录。
  - 从 `spec.md` 提取第一行一级标题作为特性名称。
  - 从 `tasks.md` 中用正则匹配 `^\s*[-*+]\s+\[([ xX])\]\s+(.+)$`，统计总任务数、已完成任务数以及完成百分比。
- **渲染 `README.md` (DUFS 概览看板)**：
  - 包含特性规格表格（编号、特性名称、进度百分比、状态、链接）。
  - 包含工程文档直达链接。

### 2. 增量同步协议 (Rsync Commands)
```bash
# 1. 确保远端目标目录存在
ssh liou@nuc.local "mkdir -p /home/liou/dufs-lan/todos/nix-tools/specs /home/liou/dufs-lan/todos/nix-tools/docs"

# 2. 镜像 specs 目录
rsync -avz --delete specs/ liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/specs/

# 3. 镜像 docs 目录 (包含 deploy/docs 产物)
rsync -avz docs/ liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/docs/
rsync -avz deploy/docs/ liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/docs/

# 4. 同步生成的 README.md 看板
rsync -avz /tmp/todos-nix-tools-README.md liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/README.md
```

---

## 三、验证方案 (Verification Plan)

1. 执行 `python3 scripts/sync-todos.py`，观察同步日志与返回码。
2. 通过 SSH 检查 NUC 上的文件：
   `ssh liou@nuc.local "ls -la /home/liou/dufs-lan/todos/nix-tools/specs"`
3. 检查生成的 `plan.md` 格式，确保包含 `## 现在怎样`、`## 下一步` 等段落。

## 当前方案：共享 Markdown 总纲

work-progress 管理集中技能、标准库 Python 工具与工作区一条统一入口。手工摘要在所属仓库 specs/README.md，工具只填最近 Git 区；不从提交猜测后续计划。各仓既有 sync-todos 作为共享 --publish 薄包装；未提供命令的产品直接使用共享工具，不逐仓添加操作规则。

NUC仅写入中央登记的 projects/<登记名>.md 与共享README.md；不上传整套规格、手册、规则、.git、提交正文或 diff，不生成独立页面。DUFS 消费方规格在其005，保留独立 Bevy 产物。首次接入只涉及本次两个仓库，知识卡等其他产品不改。

### Constitution Check

产品状态仍在各自 specs；摘要是有链接的阅读索引而非平行任务源。只本机代码与构建、NUC 资料镜像；不更改后端/用户数据、不进行系统 switch。权限755/644、只发布两个登记Markdown文件且无删除选项，xiaoqiang专用目录不变。无外部参考引入，ref/docs/specs分层以及gitlink完整SHA/浅克隆要求无新增适用项。

验证共享工具的真实临时Git与目标拒绝、既有agent-rules回归/技能校验；DUFS WASM/Rust/private构建及真实构建目录浏览回归；最后两仓提交/推送与白名单资料checksum。

## 全工作区迁移方案与 Constitution Check

中央登记管理32个产品根与worktree别名，overview.py共用手工总纲与Git最近变化，普通sync-todos变薄包装。总纲只有4节，不复制任务/计数；NUC只发布平面Markdown和分类索引，本地详细Spec保留Git。共享子模块不建立第二套规格；源仓独立提交，禁止把上游Zen当推送目标。无远程/敏感历史仓只本地提交，保留原用户改动。

本轮非xiaoqiang工程的进度目标统一projects；用户明确保留xiaoqiang原规则，不参与整理或摘要发布。精确备份后仅清理旧工程目录和已核对工程文件，禁止对todos根或projects使用rsync --delete。先核验新32份摘要、个人保护哈希与备份归档内容，再删除旧名单。无新外部参考、无gitlink/依赖升级，目录分层与固定浅引用要求不变，不部署应用、不操作硬件或数据库。

用户纠正范围后：xiaoqiang已排除，误加的10份本地进度总纲以反向提交恢复；原dufs专用发布区未触碰，新增projects摘要移除。此纠正不启动Gitee权限处理或任何产品发布。
