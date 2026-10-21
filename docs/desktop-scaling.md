# 桌面应用大字与统一缩放

## 统一入口

`liu-bigpc` 的 `features.desktopScaling.scale` 默认读取
`features.niri.primaryOutputScale`，目前为 **1.5**。
主屏 Dell 为 150%，Philips 竖屏为 100%。
[xwayland-satellite 上游说明](https://github.com/Supreeeme/xwayland-satellite#scalinghidpi)
指出混合缩放会采用较小的 DPI，因此 X11 程序在主屏可能很小。

`home-manager/nix_modules/desktop-scaling.nix` 提供统一 XSETTINGS 与
`Xft.dpi`（144 DPI）。服务使用会话导入的 `DISPLAY`，连接触发 satellite 按需启动，
并在显示尚未就绪或连接断开时重试，不硬编码显示编号。
不在整个会话设置 `QT_SCALE_FACTOR` 或 `GDK_SCALE`，避免原生 Wayland 程序重复缩放。

这是 X11 的单一 DPI：移到 100% 副屏仍保持大字，不能按窗口所在屏幕自动切换。
桌面启动器和终端均走相同包装。已有进程通常需要退出重开。

## 应用检查清单（2026-10-09）

| 应用 | 后端或界面类型 | 本次处理与限制 |
| --- | --- | --- |
| FreeCAD 1.1.3 | 官方 AppRun 固定 `xcb`，Qt6/XWayland | 自动读取统一 DPI，隔离 Qt 探针已确认 DPR=1.5 |
| 微信 | 官方自带界面/XWayland | 保留显式 1.5，设置 `QT_FONT_DPI=96` 防止与全局 DPI 叠加 |
| QCAD、Sioyek | 本仓库固定 `xcb`，Qt/XWayland | 启用自动 DPI 与 PassThrough，允许 1.5 的分数缩放 |
| 嘉立创 EDA、下单助手 | Electron/FHS | 原来已有 1.5 参数，改为读取统一入口；不是本次才增加缩放 |
| 向日葵 | GTK3 加自带 CEF，固定 X11 | GTK 控件读取 DPI；CEF 启动传入统一 `--force-device-scale-factor`，自绘内容需重开实测 |
| ChatGPT/Codex | 本次实际主进程为 `--ozone-platform=wayland` | 不属于当前 XWayland；显式设备缩放 1.5 覆盖两块屏幕，保留 Wayland 后端 |
| 百度网盘 | GTK2/GTK3 加内置浏览器/FHS | 系统控件可读取 XSETTINGS；内置浏览器或自绘区域是否跟随需实测 |
| AnyDesk | 官方包装固定 X11 | 标准控件读取统一 DPI，自绘的连接/远端画面不保证跟随 |
| AbiWord、Gnumeric、Sakura | GTK | 走 X11 时可读取 XSETTINGS；原生 Wayland 分支使用显示器缩放 |
| KiCad、KeePassXC、qBittorrent | wxGTK/Qt，可原生 Wayland | 无全局倍率注入；若选择 X11，可读取统一 DPI。当前 qBittorrent 窗口 PID 为自身，区别于 satellite 代理的 X11 窗口 |
| Antigravity、Google Chrome | Chromium/Electron | 未增加强制后端，自动 DPI 行为按应用版本与后端验证 |
| LocalSend、Blender、mpv、Zen、Nautilus | Flutter、自绘或原生 Wayland 能力 | 没有证据表明当前均为 XWayland；不把这些应用误判为 X11，也不保证自绘字体跟随 Xft |

系统字体名称、字号、DPI 与应用缩放是不同设置。网页/Electron CSS、CEF、自绘控件
不一定采用系统字号；DPI 服务覆盖标准控件，独立设备缩放参数补充不采用系统字号的界面。
远端桌面的文字大小仍由远端分辨率和向日葵画面缩放控制。

Codex 还支持 Settings → Appearance 中的 **UI font size** 与 **Code font size**，
可单独调到 16 或 18；这是官方支持的字号选项，不需要修改用户数据库或客户端源码。
来源：[官方设置说明](https://learn.chatgpt.com/docs/reference/settings#appearance)。

## 生效与验证

完整 `liu-bigpc` NixOS toplevel、Home Manager generation 构建通过，
用户服务、系统服务路径及 `HOME_MANAGER_BACKUP_EXT=hm-backup` 已核对。
在独立 satellite/XWayland 显示上启动相同 XSETTINGS，读取结果为 147456（144×1024）；
FreeCAD 自带 PySide6/Qt6 的默认设置与微信使用的基础 DPI+显式倍率组合均为 DPR=1.5，
没有 2.25 叠加。临时进程已关闭，未替换当前桌面的 DPI 服务。
这不是所有应用的真实窗口验收；尤其向日葵内置 CEF 是否保留参数仍需实际确认。

用户在普通终端应用配置：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```

然后确认服务并退出重开相关应用（FreeCAD 先保存工程，Codex 等当前任务结束后再退出）：

```bash
systemctl --user status xsettingsd
xrdb -query
dump_xsettings
```

`xrdb` 应含 `Xft.dpi: 144`，`dump_xsettings` 应含 `Xft/DPI 147456`。
注销再登录可重新建立会话；不要为改字号强行结束现有 XWayland、Niri 或应用。
