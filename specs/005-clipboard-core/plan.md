# 技术方案

复用 src/clipboard、discovery、content、transfer、notify 及 mobile 现有模块。平台保存策略与协议策略分开；应用保留独立 Git、构建和发布，父仓库只集中维护规格与集成。

参考副本 refs 按需初始化，不纳入默认检出。Git e8217a1 已确认旧待办中的图片写回与友好 socket 错误早已实现，不再恢复错误状态。

## 宪法检查

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。
