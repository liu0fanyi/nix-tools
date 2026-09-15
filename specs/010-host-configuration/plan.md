# 技术方案

复用 nixos/hosts、Home Manager 模块与 vault 工具。远端旧 todo 中已完成项作为回溯需求，不直接复制旧勾选。

系统构建、运行激活、桌面实机验证是独立阶段，旧记录中 deferred switch 仍不可认定为已激活。

## 宪法检查

蓝牙复用 NixOS hardware.bluetooth / services.blueman，在 liu-bigpc 主机模块启用；
Home Manager Niri 模块按 isLiuBigpc 条件生成 Waybar bluetooth 配置，点击使用 store 中的 blueman-manager。

Mako 对 app-name=blueman actionable 设置独立超时和格式；点击通过 makoctl menu -n "$id"
调用 fuzzel，使用固定程序路径并携带 jq 依赖。普通通知及勿扰模式保留原行为。

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。
