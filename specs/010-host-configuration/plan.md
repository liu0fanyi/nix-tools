# 技术方案

FreeCAD 在 `home.nix` 与 Blender 并列声明，通过 `packages/freecad-bin.nix` 固定官方 1.1.3 AppImage 与 SHA-256，使用 appimageTools 包装。当前 nixpkgs 源码包未命中完整缓存，为避免长时间编译 IFC/FreeCAD 改用同版本官方二进制。验证完整 toplevel、HM generation 和命令/desktop 入口，不执行 switch。

EDA 使用独立 `home-manager/nix_modules/eda.nix` 模块；KiCad 来自锁定 nixpkgs，
嘉立创包位于 `home-manager/packages/lceda-pro.nix`，固定官方 3.2.203 ZIP 与哈希，
使用 buildFHSEnv 保留官方 Electron 及原生模块，生成桌面入口并安装上游图标。
不关闭 Electron 沙箱，不修改用户现有工程。升级需核对下载页、哈希及完整构建。

复用 nixos/hosts、Home Manager 模块与 vault 工具。远端旧 todo 中已完成项作为回溯需求，不直接复制旧勾选。

系统构建、运行激活、桌面实机验证是独立阶段，旧记录中 deferred switch 仍不可认定为已激活。

## 宪法检查

蓝牙复用 NixOS hardware.bluetooth / services.blueman，在 liu-bigpc 主机模块启用；
Home Manager Niri 模块按 isLiuBigpc 条件生成 Waybar bluetooth 配置，点击使用 store 中的 blueman-manager。

Mako 对 app-name=blueman actionable 设置独立超时和格式；点击通过 makoctl menu -n "$id"
调用 fuzzel，使用固定程序路径并携带 jq 依赖。普通通知及勿扰模式保留原行为。

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。
