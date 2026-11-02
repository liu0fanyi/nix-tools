# 原生应用组合候选与启动验收

用户已确认沿跨链路架构审查继续，当前实施第一阶段保护网。权威在nix-tools；产品逻辑、身份/迁移协议及writer重构属于后续阶段，不扩展本阶段。

## 需求
- 显式候选包含固定后端包及验证证明、固定前端及构建证明、两端共享revision/实际Firefox桥WASM、API/namespace/Storage协议以及独立应用逐文件摘要。
- 来源、制品、执行器/验收器任一变化均使原组合结果失效；不只看文件名或布尔passed。后端证明复用037严格准入，纯前端不重编译后端。
- 新原生组合入口默认只核验；prepare需要当前完整组合成功证明，然后复用原摘要绑定管理器。它不执行apply/rollback、备份恢复或系统switch，不绕过原管理器任务/漂移/状态检查。
- 实际隔离组合使用选定包内Rust CLI及实际前端，真实DUFS文件入口和临时规范namespace；strict签名保持，LAN浏览器Basic读取manifest与locations成功，未签名sync拒绝，未授权/跨Origin访问拒绝。
- 浏览器不mock API/manifest；以临时Storage检验正常/同值别名合并/不同进度拒绝/未知旧操作/重启幂等，核对真实HTML/WASM摘要及独立应用保留。
- 失败不产生可prepare组合；测试网络只允许临时loopback origin，绝不读日常profile、生产数据库/密码或远端数据。
- 保留旧native-release供既有流程/恢复；不把该路径旧证据当新组合验收。普通新候选走native-bundle；后续全面替换另按验证推进。

## 边界
本阶段只开发与隔离验收，不实际发布。复用固定后端/前端，不重新构建Firefox、Rust或工具镜像。原完整门槛/回退边界保持；依赖、结构变化仍按原策略。
