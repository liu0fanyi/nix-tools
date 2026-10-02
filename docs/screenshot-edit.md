# 截图编辑与快捷键录屏（liu-bigpc / Niri）

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

## 快捷键录屏

- `Ctrl+Shift+Fn+I`（Ctrl+Shift+Print）：在单个显示器内框选区域后开始；再次按同一组合停止。
- 选区时 Esc 取消；录屏时显示常驻通知，停止后自动复制视频文件，通知给出保存位置。
- 文件保存在 `~/Videos/Screencasts/Recording-*.mp4`；默认无声、30fps、H.264。
- 录屏期间阻止自动空闲/睡眠；没有登录自启动，结束后释放资源。
- 可在终端运行 `screen-record-toggle`，其效果与快捷键一致。
- 失败通知表示文件可能不完整；查看
  `journalctl --user -u nix-tools-screen-record.service` 排查。
- 只停止本入口启动的录屏；自行运行的 wf-recorder 不受影响。

Kooha 提供声音来源、格式、帧率、指针与延迟等图形设置；本配置仅安装 wf-recorder，
不安装 Kooha。软件编码实际 CPU 占用和画面播放效果须 switch 后实测。

## 录屏后粘贴

正常结束录屏后，视频文件会自动放入剪贴板，在支持文件粘贴的应用中按 Ctrl+V
即可添加附件。剪贴板提供的是文件 URI（text/uri-list）；具体聊天软件/网页是否
接受视频文件，须实际试用。若粘贴无反应，可从通知中的路径拖入视频或选择附件。

视频仍保存在 Screencasts 目录。失败录屏或空文件不复制；若提示“已保存，复制失败”，
原文件仍可手动使用。剪贴板拥有者独立于录屏进程存活，被新的复制操作替换后退出，
无需常驻剪贴板管理器或登录自启动服务。
