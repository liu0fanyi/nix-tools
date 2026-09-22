# EDA 桌面工具

## 三维结构与造型

`home.nix` 另安装 FreeCAD（设备外壳、精确尺寸、参数化结构件）和 Blender
（手办、自由造型、渲染）。FreeCAD 固定官方 Linux AppImage 1.1.3 与下载哈希，
包定义为 `home-manager/packages/freecad-bin.nix`；启动器搜索 `FreeCAD`，命令为 `freecad`。
本次仅安装应用，不额外安装 AI/MCP 插件；可后续使用内置 Python 宏辅助建模。
两者分别保存源工程；转换 STEP/网格不等于保留原来的参数化历史。

## 电路设计

Home Manager 的 `nix_modules/eda.nix` 同时安装：

- **KiCad**：跟随 `flake.lock` 中的 nixpkgs，含符号/封装/3D 库。启动器搜索
  `KiCad`，终端运行 `kicad`；自动化入口为 `kicad-cli`。
- **LCEDA Pro（嘉立创 EDA 专业版）**：官网 Linux x64 3.2.203，固定 SHA-256。
  启动器搜索 `LCEDA Pro`，终端运行 `lceda-pro`。

嘉立创包定义位于 `home-manager/packages/lceda-pro.nix`，保留上游 Electron 与
原生模块，使用 FHS 兼容运行环境，不执行需要 root 的上游安装脚本，不关闭沙箱。
通过包装脚本将 `config.features.niri.primaryOutputScale` 传入启动参数
`--force-device-scale-factor`，解决 XWayland 环境下 2K 高分屏默认 1.0x 界面与字体偏小的问题。
程序位于只读 Nix store；工程与用户设置仍由应用保存在用户可写目录，未用 HM 接管。
首次激活如有提示，请按官网流程获取免费激活文件。不要在应用内覆盖升级 store 文件；
升级时修改包版本与下载哈希，再重新构建/切换。

用户在完整构建验证通过后，于普通终端执行：

```bash
nu rerun.nu liou --host liu-bigpc
```

Agent 不代为执行 switch。首次桌面验收需分别检查窗口、中文输入、缩放、创建并
保存测试工程，以及 KiCad 3D 视图。构建通过不等于上述图形功能已实测。

官方来源：[下载页](https://lceda.cn/page/download)、
[客户端说明](https://prodocs.lceda.cn/cn/faq/client/)。
