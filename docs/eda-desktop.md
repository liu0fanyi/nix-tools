# EDA 桌面工具

## 三维结构与造型

`home.nix` 另安装 FreeCAD（设备外壳、精确尺寸、参数化结构件）和 Blender
（手办、自由造型、渲染）。FreeCAD 固定官方 Linux AppImage 1.1.4 与下载哈希，
包定义为 `home-manager/packages/freecad-bin.nix`；启动器搜索 `FreeCAD`，命令为 `freecad`。
本次仅安装应用，不额外安装 AI/MCP 插件；可后续使用内置 Python 宏辅助建模。
两者分别保存源工程；转换 STEP/网格不等于保留原来的参数化历史。

## 电路设计

Home Manager 的 `nix_modules/eda.nix` 同时安装：

- **KiCad**：固定 `flake.lock` 中独立 `tool-updates` 输入的10.0.7，含符号/封装/3D 库。启动器搜索
  `KiCad`，终端运行 `kicad`；自动化入口为 `kicad-cli`。
- **LCEDA Pro（嘉立创 EDA 专业版）**：官网 Linux x64 3.2.203，固定 SHA-256。
  启动器搜索 `LCEDA Pro`，终端运行 `lceda-pro`。
- **嘉立创下单助手**：官网 Linux x64 5.0.69，固定 SHA-256。
  启动器搜索 `嘉立创下单助手`，终端运行 `jlc-assistant`。

嘉立创包定义位于 `home-manager/packages/lceda-pro.nix`，保留上游 Electron 与
原生模块，使用 FHS 兼容运行环境，不执行需要 root 的上游安装脚本，不关闭沙箱。
通过包装脚本将 `config.features.desktopScaling.scale`（默认继承 Niri 主屏缩放）传入启动参数
`--force-device-scale-factor`，解决 XWayland 环境下 2K 高分屏默认 1.0x 界面与字体偏小的问题。
程序位于只读 Nix store；工程与用户设置仍由应用保存在用户可写目录，未用 HM 接管。
首次激活如有提示，请按官网流程获取免费激活文件。不要在应用内覆盖升级 store 文件；
升级时修改包版本与下载哈希，再重新构建/切换。

下单助手包定义位于 `home-manager/packages/jlc-assistant.nix`，沿用 FHS 兼容运行环境
和 Niri 主屏缩放设置。官方安装脚本会修改 `/opt` 和 `/usr/share` 并放宽文件权限；
本配置仅提取程序文件、图标并生成桌面入口，明确给 Electron 主程序及辅助程序
`chrome_crashpad_handler`、`chrome-sandbox` 设置执行权限。官网 ZIP 未保留 Unix 执行位，
缺少辅助程序权限时会在启动时报告 `posix_spawn: Permission denied (13)`。
登录和下单由用户在应用内完成。

用户在完整构建验证通过后，于普通终端执行：

```bash
nu rerun.nu liou --host liu-bigpc
```

Agent 不代为执行 switch。首次桌面验收需分别检查窗口、中文输入、缩放、创建并
保存测试工程，以及 KiCad 3D 视图。构建通过不等于上述图形功能已实测。

官方来源：[下载页](https://lceda.cn/page/download)、
[客户端说明](https://prodocs.lceda.cn/cn/faq/client/)、
[下单助手下载页](https://download1.sz-jlc.com/download/jlc-order-assistant.html)。


## 嘉立创 EDA 崩溃转储（2026-10-20）

日常使用关闭嘉立创 EDA 的完整内存转储。它主要用于开发者或厂商调试，用户通常
只需保留版本、复现步骤和崩溃日志。2026-10-20 的转储曾造成约30.7G写盘和整机
I/O卡顿；关闭后无法提供对应的完整内存现场，但不影响正常设计和保存工程，
也不会修复导致程序崩溃的错误。

`lceda-pro` 的 FHS 内部启动器在 exec 前设置 `ulimit -S -H -c 0`；软硬限制均为0，
由 Electron 主程序及子进程继承，设置失败则不启动。systemd-coredump 尊重
RLIMIT_CORE，不再为这些进程采集完整内存镜像，仍可记录崩溃基本信息。
不改系统全局转储策略，不影响 KiCad、下单助手和微信，也不关闭应用自身的
Crashpad 报告。直接绕过包装器运行 store 内的原始程序不受此启动器保护。

完整系统与 Home Manager 构建验证通过后，在普通终端手动执行：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```

然后保存工程、完全退出 EDA，再从桌面入口或 `lceda-pro` 重新启动。
已运行的旧进程不会因 switch 自动获得新限制，Agent 不关闭当前窗口。
重开后可核对所有 EDA 进程：

```bash
for pid in $(pgrep -x lceda-pro); do
  echo "PID $pid"
  prlimit --pid "$pid" --core
done
```

SOFT、HARD 应均为0。若厂商明确需要完整转储协助排错，再临时移除这一行、
构建应用并重启，排错后恢复。

验证采用隔离挂载将 EDA 可执行文件替换为资源探针，运行真实 FHS 启动链；
确认软硬限制为0、无法重新提高硬限制、子进程继承和150%缩放/带空格参数转发。
未启动真实 EDA 或制造真实应用崩溃。官方依据：
[systemd-coredump 资源限制说明](https://www.freedesktop.org/software/systemd/man/latest/systemd-coredump.html)。


## FreeCAD / KiCad 更新（2026-10-20）

FreeCAD 1.1.4 和 KiCad 10.0.7 已固定并通过完整系统/HM 构建。隔离临时目录中，
FreeCAD 控制台新建、保存及重开 FCStd、STEP 导出通过；KiCad CLI 原理图 SVG 导出
通过。未操作用户工程或启动真实 GUI。应用后仍需用户确认中文输入、主屏缩放、
工程打开/保存和 KiCad 3D 视图；版本、完整产物及 gh/pnpm 同轮更新见
[工具更新记录](antigravity-update.md)。
