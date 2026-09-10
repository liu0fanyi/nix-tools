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
