# 技术方案

FreeCAD 在 `home.nix` 与 Blender 并列声明，通过 `packages/freecad-bin.nix` 固定官方 1.1.3 AppImage 与 SHA-256，使用 appimageTools 包装。当前 nixpkgs 源码包未命中完整缓存，为避免长时间编译 IFC/FreeCAD 改用同版本官方二进制。验证完整 toplevel、HM generation 和命令/desktop 入口，不执行 switch。

EDA 使用独立 `home-manager/nix_modules/eda.nix` 模块；KiCad 来自锁定 nixpkgs，
嘉立创包位于 `home-manager/packages/lceda-pro.nix`，固定官方 3.2.203 ZIP 与哈希，
使用 buildFHSEnv 保留官方 Electron 及原生模块，生成桌面入口并安装上游图标。
不关闭 Electron 沙箱，不修改用户现有工程。升级需核对下载页、哈希及完整构建。

嘉立创下单助手封装在 `home-manager/packages/jlc-assistant.nix`，复用 FHS/Electron 方案，
并在解包时修正主程序、crashpad 与 sandbox helper 的可执行权限；由 EDA 模块传入
`primaryOutputScale`。百度网盘封装在 `home-manager/packages/baidunetdisk.nix`，
单独使用 `nixpkgs-gtkmm2` 锁定输入补足 GTK2 C++ 运行库，仅在 liu-bigpc 导入。
`flake.lock` 随本次输入变动固定其源及同步刷新过的现有输入。Mako 模块按应用名设置
常驻通知，Blueman 菜单成功返回时清除通知并禁止写入历史。

本次验收先完成包、完整 toplevel、HM generation 与生成配置构建；图形应用的登录、
文件传输及通知交互由桌面实测单独确认。任何构建结果均不等于系统已激活。

复用 nixos/hosts、Home Manager 模块与 vault 工具。远端旧 todo 中已完成项作为回溯需求，不直接复制旧勾选。

系统构建、运行激活、桌面实机验证是独立阶段，旧记录中 deferred switch 仍不可认定为已激活。

## 宪法检查

蓝牙复用 NixOS hardware.bluetooth / services.blueman，在 liu-bigpc 主机模块启用；
Home Manager Niri 模块按 isLiuBigpc 条件生成 Waybar bluetooth 配置，点击使用 store 中的 blueman-manager。

Mako 对 app-name=blueman actionable 设置独立超时和格式；点击通过 makoctl menu -n "$id"
调用 fuzzel，使用固定程序路径并携带 jq 依赖。普通通知及勿扰模式保留原行为。

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。

## 截图标注方案

在 Niri Home Manager 模块中仅为 liu-bigpc 安装锁定 nixpkgs 的 Satty。
`Shift+Print` 调用 writeShellApplication 封装的 `screenshot-edit`，使用现有
slurp 选区、grim 截图，再以临时 PNG 打开 Satty；复制使用 wl-copy，保存路径
使用带纳秒时间戳的 `~/Pictures/Screenshots/Edited-*.png`。flock 防止重复启动，
取消选区直接退出，EXIT trap 清理临时图片。其他截图绑定不变。

宪法检查：仅 PC 权威仓库配置；未引入外部参考源码或文档原件，依赖沿用
锁定 nixpkgs；说明放 docs、需求放 specs；不部署、不执行系统 switch。
验证必须覆盖 liu-bigpc 完整 toplevel、Home Manager generation 和生成 KDL。

## 快捷键录屏方案

仅 liu-bigpc 在 Niri 模块安装锁定 nixpkgs 的 wf-recorder 与 screen-record-toggle。
Ctrl+Shift+Print 通过 flock 串行切换，slurp 取消即退出。录屏运行于专属临时
`nix-tools-screen-record.service`，systemd-run 显式传递 Wayland、运行目录和通知/文件
环境；再次触发用 systemctl stop，只向该单元发 SIGINT 并等待文件正常收尾。
ExecStopPost 替换开始通知，按 SERVICE_RESULT 与文件存在性区分保存/失败。
录制期间 systemd-inhibit 阻止 idle/sleep，结束释放；单元结束自动回收，无常驻服务。
MP4 使用 libx264/yuv420p、30fps、ultrafast/crf23；FFmpeg pad 修正奇数尺寸。

继续遵守上述宪法检查；仅更新 PC 配置和合法资料镜像，不替用户 switch。
验证完整系统/HM、KDL、脚本检查及不捕获桌面的录屏控制测试；真实画面与性能待用户验收。
