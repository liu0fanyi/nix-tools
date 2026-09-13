# 全工作区递归复核（2026-09-13）

## 复核时快照与范围

仍有遗漏；此前 30/30 仅证明当时已列入的规格文件与镜像相同，不证明所有散落资料
已归纳。本次重新遍历 /data/project（不跟随符号链接；排除 Git 内部及具名构建缓存），
发现 200 个 Git 标记、30025 个候选文档文件、346 个 doc/docs/documentation 目录，
无遍历错误。标记包括 SDK、上游、缓存和无效 .git，不能计为 200 个产品。

本地重新识别 30 个有规格的工作目录、109 个 feature spec.md；包括独立小智固件。
旧清单是工作区 29 个规格源加外部 nix-tools，分母相同但范围不同。CMT/400m 是
同一 Git 的两个分支工作树。见[机器核验记录](20260913-recursive-reaudit.json)。

这是目录/结构扫描、源码归属与重点旧文档审查，未逐字阅读上游数万份资料，也没有
测试产品功能。已跟踪自有 Markdown 的本地相对文件链接扫描未发现失效候选；不包含
锚点、动态路由、外部 URL 或未提交文件的完整语义验收。本轮未改产品或远端数据。

## 复核时发现的事项（处理结果见下文）

1. **仓库外测试资料**：xiaoqiang/test 中 14 份 Markdown，包括六类设备用例、人工
   手册、结果表和总入口，仍称自己是统一测试管理源。MIC-A006 的 5 MiB 资源门槛、
   MIC-S005 的 300 秒通话采集等用例未找到逐项迁移映射。应按 sip/demo 与 sip_old
   产品归属提炼验收要求，手册回归所属仓库，历史结果核验备份后清理；不能直接整目录
   删除，里面还有脚本、运行报告与 .secrets。旧 SSH 默认跳过 host key 的方式也不能
   原样当成当前操作规范继承。本轮未运行这些脚本。
2. **隐藏旧工作副本**：.remote-work 下 nix-tools、nix-release-scope、tag-all、dufs-plus
   均不是可用 Git checkout。其中 nix-tools/todo.md 仍列已取消的 dsh Web 计划，
   IMPLEMENTATION_PLAN.md 仍列 Clip 历史路线。需要核对独有改动、提炼有效信息并退役
   重复副本；不能恢复已取消需求，也不能根据无 .git 推断全部文件可直接删除。
3. **规格阶段信息不足**：5 个项目的 16 个既有特性没有 plan/tasks 全套：
   esp32-p4-dufs-terminal/002 缺 tasks；tag-all 的 001/002/003/005/006/007，
   esp32-p4-game 的 002/003/004，esp32-focus-writer 的 001/002/003，
   esp32-common 的 001/002/003 缺 plan 和 tasks。部分标明回溯规格，不能据此认定
   功能没做，但也不能宣称流程/待办管理全部完整。应补明确阶段及必要的最小方案/任务，
   不虚构重新实施或验收。writer/000-hardware-selection 目前只有 selection.md，
   是正在维护的选型资料，需与该任务确认规格入口，不混入旧迁移遗漏统计。
4. **长期约束未全部落地**：例如 android-app-kit、bevy-project-planner、bevy-env
   的 constitution 只有 ref/docs/specs 分层，没有工作区要求的外部 Git 浅 submodule、
   固定 SHA 与 plan 检查约束。应逐仓库核对补齐，不用 keyword 扫描结果直接批量替换。
5. **规则入口仍有未版本化文件**：xiaoqiang/AGENTS.md 是普通文件，目录本身无 Git；
   前轮只纳入根 AGENTS 与 work-progress，未纳入这个子工作区入口。可按同样方式归入
   nix-tools 本机规则配置，保持使用路径和仅 dufs 边界。

## 当前开发变化，单独列出

镜像核对时 27/30 一致：tag-all 新增 009-transcription-audio 未同步，bevy-sketch/004
三份规格变化，dufs-plus/003 的 plan/tasks 变化；这三处工作树同时有正在开发的代码。
应由当前任务完成后同步，不在审计中提交或覆盖其代码。dufs-plus 本地 tracking 显示
领先 origin/main 一个提交，需发布收尾时核对远端，不能据此断言之前的推送失败。

## 归属明确或已记录，不当成新产品遗漏

- tag-server/tag-backend/tag-tui 的 Git 独立，功能规格目前由 tag-all 管理；前两者核心
  功能已有父规格，不能按“没有 specs 目录”自动创建重复计划。建议显式说明组件归属。
  tag-server/docs/device-api-v1.md 被 include_str! 嵌入，保留位置有明确约束。
- var/keeb-check/Tanuki 是干净的上游键盘参考，writer 正在选型引用；不是新产品。
  其原始参考最终落 ref 与派生转录落 docs 的工作应随选型整理，当前不可当缓存删掉。
- 小智 rag-eval-output 有 7 份历史生成报告，属于运行产物；若清理须先核对是否仍有
  独有评测依据，不必为每份报告新建 spec。
- xiaoqiang/build-output、backup、test/results，顶层 Config/Database/Log 等属于
  构建/运行/恢复内容，不能以资料清理名义无差别删除。SDK、模型、上游参考不建产品规格。
- signature-server 整库历史敏感信息处理、失效 encryption/.git 指针与远程备份，
  小智容器 UID/GID 构建复验，仍是此前已记录后续事项；它们不阻止文档归纳。

## 建议处理顺序

先将 xiaoqiang/test 有效用例逐项映射到所属 spec，再核对并退役 .remote-work 旧副本；
随后逐仓库补规格阶段、长期约束和子工作区规则版本化。活跃开发的同步由对应任务收尾。
本报告记录复核结果，不代替各产品规格，也不授权部署或硬件测试。

## 本轮非活跃项处理结果

用户授权先处理遗漏、正在开发项目跳过。本节更新前文审计快照，不把未处理项改为完成。

| 审计项 | 本轮结果 |
| --- | --- |
| xiaoqiang/test 的 14 份 Markdown | 6 份用例正文进入 sip/demo/003 与 sip_old/005 的 contracts；人工手册进入 sip/demo/docs；补全 sip_old 对话筒共通判据的隐含引用。6 份 RESULTS 删除，根 README 改为工具入口，原用例/手册位置为兼容链接。脚本、.secrets、results 产物保留。 |
| 非活跃隐藏副本 | .remote-work/nix-tools（5084 文件/链接）及 nix-release-scope（43）校验私有备份后删除工作副本。 |
| 非活跃规格缺口 | terminal/002 的 tasks，game/002/003/004 与 common/001/002/003 的 plan/tasks 共 7 组补齐。回溯实现与后续复验区分，UI 重设计仍待实施。 |
| 长期约束 | terminal、game、android-app-kit、dufs-client-rs、bevy-env、canvas-kit、foundation、planner、device-bean-mobile 共 9 个 constitution 补齐外部参考、固定 SHA/shallow、来源分层和 plan 检查；修正 bevy-env 已有私有远程的过期表述。 |
| 未版本化规则 | xiaoqiang/AGENTS.md 纳入 config/agent-rules/project/xiaoqiang/AGENTS.md，与根规则/技能由同一安装器管理，原位置链接读取。没有把 xiaoqiang 的 dufs 例外扩展到其他工程。 |

### 旧副本有效信息映射

- nix-tools/todo.md：主机休眠/合盖/swap、Rime、mihomo 与桌面配置对应 specs/010-host-configuration；dsh Web 对应 specs/009-infrastructure 的已取消项，不恢复。
- IMPLEMENTATION_PLAN.md：Clip 协议、发现加密、手动接收、通知去重与配对对应 specs/005；资源限制、错误恢复与诊断对应 specs/006；CI 精确 revision、安装器、自检、缓存及公开发行门槛对应 specs/007。旧测试数字只作历史依据。
- nix-release-scope/deploy 文档：PC 发布、NUC/公网分层、摘要验收、Edge/Authelia 及失败回滚对应 specs/009 与现有 deploy/docs；旧副本不再作为运行操作入口。
- 未逐项替换旧副本的源码/制品；整个副本保存在本机私有恢复目录，独有旧文件没有丢失，也没有作为当前有效代码重新合并。

### 备份与验证边界

本机恢复目录 `/home/liou/.local/state/spec-cleanup/20260913-inactive/`：test-markdown 保存原 14 份文件及 SHA256.json；remote-work 保存两份原副本及逐文件 SHA256/链接目标清单。复制后与源逐项相同才删除原位置。仅本机保存，不加密、不上传这批备份。

本轮不执行产品构建或硬件测试。规则安装器 4 项回归通过，5 个规则链接核验通过；变更文档相对文件链接、兼容链接及 Git diff 检查通过。测试要求归并不代表当前板端已通过。

### 按用户要求未处理

tag-all、bevy-sketch、dufs-plus、esp32-focus-writer 的开发工作树、规格与镜像由原任务收尾；即使检查期间它们变成干净也不自动纳入本轮。.remote-work/tag-all 和 .remote-work/dufs-plus 同样保留。
tag-all 6 组与 writer 3 组历史 feature 的 plan/tasks，以及这些活跃工程的规则缺口未在本轮补齐。个人文件、上游/SDK、运行与构建产物、已记录的 signature-server 远端和小智构建债务维持原边界。

本轮 12 个文档仓库已提交推送并完成各自 NUC 镜像 checksum 回查；sip/demo 与 foundation 先推，随后更新 sip 与 bevy-env 对应 gitlink。活跃子仓库指针未由本轮更新。提交与验证记录见 [非活跃收尾记录](20260913-inactive-close.json)。SIP 文档只写 dufs/sip-demo 与 dufs/sip-old，其余按各自 todos 目录同步。
