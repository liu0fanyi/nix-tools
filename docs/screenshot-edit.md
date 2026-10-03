# 截图编辑与快捷键录屏（liu-bigpc / Niri）

原有 `Fn+I` 截图保留。配置接收的是 `Print`，Fn 组合由键盘固件转换；
新增 `Shift+Fn+I`（`Shift+Print`）框选截图后打开 Satty。若键盘未将
Shift+Fn+I 上报为 Shift+Print，需实测键盘事件再调整，不能改掉原截图习惯。


| 操作 | 快捷键 |
| --- | --- |
| 框选截图 | Fn+I |
| 框选截图后编辑（Satty） | Shift+Fn+I |
| 开始/停止框选录屏 | Cmd+S |
| 录屏后自动编辑（Screen Cut） | Cmd+Shift+S |
| 截取整个屏幕 | Ctrl+Fn+I |
| 截取当前窗口 | Alt+Fn+I |

Shift统一表示带编辑；录屏两种组合都能停止正在录制的视频，是否编辑由开始时的组合决定。
原Ctrl+Shift+Fn+I、Alt+Shift+Fn+I录屏绑定撤销。Cmd对应Niri的Mod/Super。

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

- `Cmd+S`（Mod+S）：在单个显示器内框选区域后开始；再次按同一组合停止。
- 选区时 Esc 取消；录屏时显示常驻通知，停止后自动复制视频文件，通知给出保存位置。
- 文件保存在 `~/Videos/Screencasts/Recording-*.mp4`；默认只录系统声音，24fps、H.264 + AAC。
- 录屏期间阻止自动空闲/睡眠；没有登录自启动，结束后释放资源。
- 可在终端运行 `screen-record-toggle`，其效果与快捷键一致。
- 失败通知表示文件可能不完整；查看
  `journalctl --user -u nix-tools-screen-record.service` 排查。
- 只停止本入口启动的录屏；自行运行的 wf-recorder 不受影响。

软件编码实际 CPU 占用和画面播放效果须 switch 后实测。

## 录屏后粘贴

正常结束录屏后，视频文件会自动放入剪贴板，在支持文件粘贴的应用中按 Ctrl+V
即可添加附件。剪贴板提供的是文件 URI（text/uri-list）；具体聊天软件/网页是否
接受视频文件，须实际试用。若粘贴无反应，可从通知中的路径拖入视频或选择附件。

视频仍保存在 Screencasts 目录。失败录屏或空文件不复制；若提示“已保存，复制失败”，
原文件仍可手动使用。剪贴板拥有者独立于录屏进程存活，被新的复制操作替换后退出，
无需常驻剪贴板管理器或登录自启动服务。

## 声音和文件大小

Waybar 的摄像图标显示当前录屏声音，录制时变红并显示圆点：

- 左键选择“系统声音 / 麦克风 / 系统+麦克风 / 无声”，选择保留到下次；默认系统声音。
- 右键开始/停止普通录屏；录制期间不能更换音源，先停止再选。
- 系统声音录制默认输出设备的 monitor；麦克风选默认非 monitor 输入，
  默认输入是 monitor 时改选第一个非 monitor 输入，没有则提示错误。
- 系统+麦克风通过临时虚拟输出混合，结束清理，不把麦克风播放到扬声器，
  不改变系统默认输入/输出。当前检查仅发现 monitor，尚无可用麦克风输入。

保留选区原分辨率，24fps、H.264 veryfast/CRF24，VBV 视频码率4Mbps、缓冲8Mb，
声音 AAC 128kbps/48kHz。相比 ultrafast 压缩更好，但编码 CPU 负载更高，适合文字/操作演示。
持续接近码率限制时约31MB/分钟（含声音，不是文件大小硬上限）；静态画面通常更小，
动态复杂画面可能牺牲细节。画面质量和负载需要真实试用，录小区域也能减少体积。

## 录屏后剪辑

### Screen Cut菜单与录屏后自动编辑

在普通终端执行：
```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```

Cmd+D搜索Screen Cut，按o选视频；Cmd+Shift+S开始框选录屏，结束后自动打开刚录制视频。
Cmd+S保留普通录屏、不打开编辑器。h/l定位、v选区、d删除，Ctrl+S保存，
Ctrl+C导出并复制编辑结果。复制仍是文件URI，dufs-plus视频粘贴未增加。

安装引用固定Cachix版本，不依赖开发机源码路径；其他x86_64 Linux Niri宿主也通过rerun安装。
系统切换后才可用，Agent只构建验证、不执行switch。
