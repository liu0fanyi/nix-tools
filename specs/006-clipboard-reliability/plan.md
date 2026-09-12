# 技术方案

src/transfer 分离 crypto、client/server、cache、connections、workspace、staging 与 payload；notify 分离保存/剪贴板和平台通知；mobile 分离引擎、配对、收发、设置与更新。保留事件协议与命令名。

0.1.13 双向文字、逗号文件名、强制停止重开和暂停发送者后手动重试有历史短测；不等于完整矩阵通过。旧 refactor.md 中“友好错误尚未提交”已被后续 Git 55e87b0/e8217a1 的记录取代。

## 宪法检查

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。
