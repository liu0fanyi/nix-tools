# 截图后编辑（liu-bigpc / Niri）

原有 `Fn+I` 截图保留。配置接收的是 `Print`，Fn 组合由键盘固件转换；
新增 `Shift+Fn+I`（`Shift+Print`）框选截图后打开 Satty。若键盘未将
Shift+Fn+I 上报为 Shift+Print，需实测键盘事件再调整，不能改掉原截图习惯。

1. 按 Shift+Fn+I，拖动选择区域；Esc 取消选区。
2. 在 Satty 工具栏选择箭头、文字、画框、模糊或裁剪。
3. Ctrl+C 复制编辑结果，然后在目标应用 Ctrl+V 粘贴。文字编辑时先完成输入
   再复制图片，避免复制选中文字。
4. Ctrl+S 保存到 `~/Pictures/Screenshots/Edited-*.png`；Esc 退出，
   不自动保存。临时原图在退出后清理。

可从应用菜单单独打开 Satty，也可运行 `satty --filename /绝对路径/截图.png`。
编辑器按需启动，无后台服务。连续触发快捷键不会打开多个选区或编辑器。

配置由 `/home/liou/nix-tools/home-manager/nix_modules/niri.nix` 管理，规格见
[主机配置](../specs/010-host-configuration/spec.md)。用户在普通终端执行
`cd /home/liou/nix-tools && nu rerun.nu liou --host liu-bigpc` 后实测；
Agent 只构建验证，不代为切换系统。
