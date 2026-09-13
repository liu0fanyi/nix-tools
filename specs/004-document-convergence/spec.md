# 文档归属与规格单源核验

## 范围

复核本地 18 个工程、nix-tools 及其 clipboard-sync 子模块，与 NUC todos、历史 nix-tools checkout 和资料区交叉核对。个人事项、上游资料、许可、运行数据不转为产品 spec；初轮 xiaoqiang 仅盘点；后续按用户逐仓库授权扩展，最新边界见下文。

## 验收标准

- 需求与验收在 specs；契约在 contracts；约束在 constitution；操作说明和参考保留原有适当入口。
- Clip 的唯一规格源是 nix-tools/specs；子模块只保留操作说明和指向父仓库的入口。不建立第二套待办。
- 源文件与镜像按 SHA-256 核对；已取消需求不恢复成待办，旧验证不冒充本轮实测。
- 每个尚未闭环项明确记录，不以文件存在或任务勾选推断内容完整迁移。
- 删除前需逐条核对内容去向；混合文档中个人和暂缓项目内容保留。


## 2026-09-13 后续授权收尾

软件工程范围已扩展到 xiaoqiang，包括独立 sip_old 与小智；signature-server 功能改造暂缓，文档已按用户澄清归纳并同步。hardware-relation-studio 经用户确认归属 bevy-project-planner。
各产品需求仍由自身仓库管理，本规格仅记录迁移审计，不代管产品待办。
详见[本轮记录与保留边界](contracts/20260913-software-convergence.md)。


## 工作区规则版本化（用户授权）

根 AGENTS 与 work-progress 完整技能由 nix-tools 的 config/agent-rules 管理，
本机使用位置以符号链接引用。安装必须先核对所有目标：不存在或内容相同才接管，
不同本地内容或其他链接必须保留并报错；提供预演、安装、只读核验和可重复运行入口。
不迁移产品 spec，不执行系统切换，不将规则配置加入 NUC 文档同步白名单。
