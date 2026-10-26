---
name: work-progress
description: 项目代码、交付或计划更新后，联动 Spec 维护本地 Markdown 总纲和 Git 最近变化，并只向 NUC todos/projects 发布摘要。适用于项目状态查询、阶段收尾与已授权的批量进度整理，不替代产品部署。
---

# 项目总纲与 Spec 联动

维护源在 nix-tools/config/agent-rules/skills/work-progress，安装位置为符号链接。
所属仓库 specs/NNN-<feature> 仍是需求与任务的权威源；工作区根没有产品规格。

## 更新顺序

1. 读适用 AGENTS、constitution、相关 Spec 和工作树，按实际证据更新原 spec/tasks；区分实现、构建、部署、用户验收，不靠 Git 提交猜上线。
2. 更新本仓 **specs/README.md**：只保留“当前情况、后续计划、待处理问题、最近变化”。前三节每节通常不超过三条；计划链接现有 feature tasks，问题链接既有 issue。没有确认的计划就写明，不自行补功能、不复制任务清单或百分比。
3. 最近变化由工具读取本仓最多八条功能提交标题；既有纯资料/CI/测试记录默认过滤。新提交标题直白说明用户能感知的变化，正文记录实现与验证。不改写旧 Git 历史。代码先提交，再刷新总纲；不为不断追赶最新文档哈希制造提交循环。
4. 总纲随源码版本管理，只提交当前任务白名单，保留原有改动。已有私人仓推送按本仓规则；没有远程或敏感历史暂缓的仓只本地提交，不擅自创建/更改远程。
5. 先预演，再发布摘要和索引，核验 checksum、目标与权限。只维护当前修改项目；用户明确要求批量处理时，才扩大到已确认清单。

```markdown
# 项目名

## 当前情况
- 实际可用到哪里；需要时标明待上线/待验收。

## 后续计划
- [已确认的下一步](NNN-feature/tasks.md)。

## 待处理问题
- 暂无已确认事项，或引用真实存在的 issue。

## 最近变化
<!-- recent-commits:start -->
<!-- recent-commits:end -->
```

示例链接必须替换为实际文件。总纲是原 Spec 的摘要，不是第二套任务源；勾选与验收仍只在原 feature 维护。

## 共用入口

中央登记表：`/home/liou/nix-tools/config/agent-rules/project/projects.json`。
登记每个产品的主来源、worktree 别名及阅读名称。同仓不重复建项目，不把参考 submodule 当新产品。
从别名 worktree 发布会拒绝覆盖主来源；先按所属产品规则核对真实当前分支与总纲再操作，不合并或改写用户分支。

```bash
python3 ~/.codex/skills/work-progress/scripts/overview.py --repo <产品根> --write --dry-run
python3 ~/.codex/skills/work-progress/scripts/overview.py --repo <产品根> --write
python3 ~/.codex/skills/work-progress/scripts/overview.py --repo <产品根> --publish --dry-run
python3 ~/.codex/skills/work-progress/scripts/overview.py --repo <产品根> --publish
```

`--write` 只填本地最近变化；当前情况和计划由 Agent 对照 Spec 维护，不从日志猜未来。
发布只写 `liou@nuc.local:/home/liou/dufs-lan/todos/projects/<登记名>.md` 与同目录 README.md 索引；共享目录永不使用 --delete，不运行 NUC Git。不复制整个 specs/docs/.git、源码、用户文件、配置、凭据或运行产物。
本地引用保留相对路径，发布阅读版转换为现有远程仓的精确提交链接；本地未提交文件或无远程时退化为文字，不虚构 URL。公开/私有策略未确认时不建远程。

普通主仓的 sync-todos 已接入该工具；未接入的旧脚本不能再用于进度发布，尤其不可在旧 worktree 里运行遗留镜像。后续项目在中央登记并核对即可，无需逐项目加 AGENTS。

用户确认 xiaoqiang 不动：本轮批量整理和 projects 登记仅包括非 xiaoqiang 工程。
xiaoqiang 不加入中央 projects 索引，不发布摘要或规格到 todos，不更新其进度文件。
其进度、固件、下载索引及接线/恢复等资料继续按原 `/home/liou/dufs/<工程发布目录>/`
白名单维护。遇到“全部项目”等泛称仍保留这一明确排除，不据泛称推翻例外。

旧 todos 工程资料只在明确清理任务中处理：精确名单、todos 外私有备份、逐文件 SHA 校验、新摘要完整核验之后才能删除；个人待办/学习资料/资产与运行数据保持原样。不因正常收尾再次清理旧资料。

收尾核对本地总纲、Spec、Git 与 NUC 摘要一致。失败报告已完成部分与剩余步骤，不把文档同步称为应用发布。
