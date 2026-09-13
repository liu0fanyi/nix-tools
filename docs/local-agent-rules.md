# 本机工作区规则管理

权威源在本仓库 config/agent-rules/，属于开发环境配置，不代管产品规格。

| 版本化源（相对 nix-tools） | 本机使用位置 |
| --- | --- |
| config/agent-rules/project/AGENTS.md | /data/project/AGENTS.md |
| config/agent-rules/project/xiaoqiang/AGENTS.md | /data/project/xiaoqiang/AGENTS.md |
| config/agent-rules/skills/work-progress/SKILL.md | ~/.codex/skills/work-progress/SKILL.md |
| config/agent-rules/skills/work-progress/agents/openai.yaml | ~/.codex/skills/work-progress/agents/openai.yaml |
| config/agent-rules/skills/work-progress/scripts/work_file.py | ~/.codex/skills/work-progress/scripts/work_file.py |

在本仓库执行 `just agent-rules` 预演，`just agent-rules --apply` 安装符号链接，
`just agent-rules --check` 核验。无 just 时可直接运行 `python3 scripts/agent-rules.py`。
首次接管只允许内容相同的普通文件或不存在的目标；已有不同内容、其他链接或链接父目录
会拒绝操作，先人工对比整合，不提供强制覆盖。全部目标先检查，再逐项安装；中断可重跑。

后续编辑源文件并在 nix-tools 提交、推送，使用位置即时读取同一份内容。仓库 checkout
须保持在当前位置；移动仓库前先安排链接迁移，不盲目覆盖原链接。恢复时先 clone 本仓库，
再运行上述安装和核验入口。技能的 __pycache__ 不纳入 Git。

work_file.py 是保留的旧工作文件兼容工具，不用于 specs 状态维护；本次仅版本化它，
没有运行它或恢复旧计划流程。日常规格同步仍走各产品自己的 sync-todos。

这些配置位于 Home Manager 管理范围之外或尚未接入其配置，因此使用本地显式入口，
不执行 Home Manager/NixOS switch，不向 NUC 安装规则，也不把 config/agent-rules
加入文档镜像白名单。只有本手册和本仓库规格按既有 sync-todos 镜像。
