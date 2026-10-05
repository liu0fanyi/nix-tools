# 主机声明式配置与诊断

## 需求与验收

- Tag Browser：`liu-bigpc` 从私有产品仓库锁定独立发行 flake，并在系统应用列表安装候选版；安装前检查精确浏览器输出在 Cachix 中存在。浏览器用户配置与服务端保持独立，NUC、homebox 不安装该桌面包。验证包括锁定版本、缓存命中、完整 NixOS toplevel、Home Manager generation、桌面入口；当前用户的系统激活及真实 GUI 操作由用户执行和验收。

- 三维建模：Home Manager 提供 FreeCAD 用于设备外壳及参数化结构设计，保留已有 Blender 用于手办造型；不默认安装 AI 插件，不接管用户工程。

- EDA 桌面工具：Home Manager 同时提供 KiCad 与嘉立创 EDA 专业版；后者固定官网 Linux x64 包版本与 SHA-256，保留官方图标，启动命令为 `lceda-pro`。为解决 XWayland 环境下 2K 屏字体过小问题，启动脚本需联动 Niri 主屏缩放（`primaryOutputScale`）注入 `--force-device-scale-factor`。不运行上游 root 安装脚本，不代用户 switch；完整系统及 HM 构建与图形验收分别记录。

- 嘉立创下单助手：仅在 liu-bigpc 的 Home Manager 中安装官方 Linux x64 版，固定版本及哈希，提供 `jlc-assistant` 命令与桌面入口；FHS 运行环境须保留 Electron 原生辅助程序的可执行权限，并沿用主屏缩放。以用户实际打开登录窗口为桌面验收，不将登录或下单视为已验证。
- 百度网盘：仅在 liu-bigpc 安装官方 Linux x64 客户端，固定 DEB 版本及哈希，通过独立 FHS 环境提供 `baidunetdisk` 命令与桌面入口；旧版 GTK 依赖从单独锁定的 nixpkgs 输入取得。构建、激活、登录及文件传输分别验收。
- 通知行为：普通 Mako 通知维持 5 秒超时；ChatGPT 与 Antigravity 通知保持可见，直到用户关闭。Blueman 操作菜单执行成功后关闭原通知，避免重复触发过期操作。

- Home Manager standalone 不依赖 NixOS system profile；rerun 使用 flake 锁定 CLI，部署与自检使用同一显式目标；不因普通 switch 自动刷新依赖。
- 主机硬件与角色分别配置，合盖策略可选，外接显示器默认忽略；休眠 swap 容量需覆盖内存。
- Niri 外接竖屏按真实 EDID 规则恢复；Rime-Ice 固定词库，Lua/OpenCC/用户词典可用，逗号句号翻页且不重复启动输入法。
- Avahi 仅清理无效、失活或 PID 复用的旧 pid 文件，活跃 Avahi 进程持有文件不得删除。
- PC 私人节点的五个现有 rootless Podman 容器在用户管理器重新启动后应自动恢复；仅匹配 `dufs-plus-pc` compose 项目及原有 `unless-stopped` 重启策略，不重建容器、卷或其他项目。Tag Browser 的本地标签和工作区依赖该节点的 `127.0.0.1:5006` 接口；服务未启动时须作为连接故障诊断，不视为数据被清空。
- NUC 温度按 coretemp/Package id 0 定位并过滤无效值，不把无效 ACPI 温度显示为高温。
- 密钥库只同步加密 KDBX，明文导出到私有目录；不在 Nix 求值时读共享密钥、不让明文进入 store 或 Git。

## 边界

### liu-bigpc 蓝牙（2026-09-14）

- 仅该主机启用 BlueZ、开机开启适配器与 Blueman 配对管理；不默认开启可发现模式，不自动配对或信任设备。
- Waybar 右侧显示蓝牙开关及连接状态，点击打开 Blueman；其他主机不增加该模块。
- 配置验证与实际 switch 后的适配器/桌面验收分别记录，不替用户执行系统切换。
- Blueman 带操作的请求保留60秒且不进历史，不能永久残留；Mako 显示可点击提示，点击弹出该通知的操作菜单，由用户确认或拒绝，不自动确认配对。应用自身的认证超时仍有效。

操作说明保留 README、nixos/reinstall-checklist.md 和 docs/secret-vault-cli.md；本轮不执行 switch、重启或恢复密钥。

### liu-bigpc 数位笔侧键滚动（2026-09-17）

Wacom One (CTL-472) 的笔无滚轮/触摸环，Linux Wayland 也无 Windows Ink 那种
"笔尖拖动=平移"的系统约定（libinput 只对 libwacom 标注带滚轮的笔产生滚轮轴；
niri 仅转发设备真实上报的数位板滚轮轴；Chromium 明确未实现该协议），因此必须由
一层 evdev→uinput 守护进程翻译手势。

- **手势语义**：按住笔杆侧键（默认下方 BTN_STYLUS）**且笔尖接触板面**后划动 → 滚轮；
  笔**悬空**划动只移动光标、绝不滚动；死区自**笔尖落点**起算。
- **手势结束**：**笔尖离板即停止滚动**（与 libinput on-button scrolling 一致），
  不得因侧键仍按住而把手部回带误判为反向划动；抬笔后保持"已武装"，
  按住侧键可连续多次划动；已滚动过的按压松开侧键时不补发点击。
- **滚动速度**：默认每 **4mm** 笔尖行程一个滚轮刻度（按 ABS_X resolution 换算），
  可用 `pixelsPerTick` 覆盖。
- **起手响应**：越过死区即**立刻**发出第一个滚轮刻度，不得要求先划满一整格；
  后续滚动速率不受此影响。死区默认 **1.5mm**（按分辨率换算，仅吸收点击抖动），
  比一个滚轮刻度小一个数量级。
- **平滑滚动**：滚轮必须走**指针通道的高分辨率滚轮**（`REL_WHEEL_HI_RES`，v120）
  以取得连续跟手；数位板通道的滚轮轴是整数，只能整格跳，不可作为平滑实现。
  起手先发一整格以越过 libinput 的 `ACC_V120_THRESHOLD`（60）预热，
  之后逐步实时转发。因虚拟指针无法跟随焦点输出（会被映射到所有输出的并集），
  必须经 **niri IPC** 取得焦点输出几何并自行映射；IPC 不可用时回退到数位板整格通道。
  坐标映射必须**逐行复刻 niri**（保持比例、裁剪填满 cover，含 transform 处理）：
  用留黑边映射会让指针偏离笔尖数十像素，用户可见为"鼠标跑到别处"。
- **不破坏原有行为**：普通书写/悬停/笔尖拖动选中不受影响；侧键快速点按仍为正常侧键点击；
  已在书写过程中按下侧键则全程透传（不打断笔迹）；一次手势不会同时选中文本或画线。
- **实现约束**：独占抓取真实笔，镜像出**虚拟笔**（应用平时看到的）与**绝对指针**
  （承载平滑滚轮）两个设备；**必须先建虚拟设备再 grab**，构建失败时不得抓取用户设备。
  仅回退路径使用虚拟笔上的 `REL_WHEEL`，此时 niri 会把滚轮转发给笔尖所在表面。
- **权限约束**：守护进程必须是 **systemd 系统服务**并声明
  `SupplementaryGroups=[input,uinput]`。用户服务不可用——本机启用 linger 使
  `user@<uid>.service` 跨注销存活、长期持有陈旧组快照，且 systemd --user 无
  `CAP_SETGID`（报 216/GROUP）；udev `uaccess` 因 `extraRules` 落在 99-local.rules
  而晚于 `73-seat-late.rules` 亦不可行。详见 docs/pen-scroll.md。
- **范围**：仅 liu-bigpc 启用；不改变其他主机、不修改 niri 上游行为。
- **验收**：单元测试覆盖手势状态机（含"悬空不得滚动"回归）与坐标映射（对照 niri
  参考实现，含旋转输出）；配置求值与 `toplevel` 构建通过。
  **2026-09-17 已由用户实机验收**：平滑滚动与指针落点均确认正常。

操作说明见 docs/pen-scroll.md，索引见 README。

### liu-bigpc 截图标注

- 保留原 Print（用户键盘 Fn+I）、Ctrl+Print 和 Alt+Print 截图行为。新增 Shift+Print
  （Shift+Fn+I）框选截图后直接打开 Satty，支持标注、复制及按需保存到
  `~/Pictures/Screenshots/`。Fn 组合由键盘上报，实际组合须桌面验收。
- 仅 liu-bigpc 安装 Satty 与截图编辑入口；无需后台常驻；取消选区不打开编辑器，
  临时原图在编辑器退出后清理。不得因取消编辑自动保存标注图。
- 系统切换与真实桌面快捷键验收由用户执行。

### liu-bigpc 快捷键录屏

- 安装 wf-recorder；Scroll_Lock（用户键盘 Fn+O）首次框选并录屏，
  再次按下正常结束、保存 MP4 到 `~/Videos/Screencasts/`。原截图绑定保持。
- 默认只录系统声音；Waybar 左键菜单选择系统、麦克风、系统+麦克风或无声，
  右键开始/停止。录制期间禁止更换声音来源；没有非 monitor 输入时明确拒绝麦克风录音。
  混音只连接到专用虚拟输出，不将麦克风送入真实扬声器，不改变默认音频设备。
- 原选区分辨率、24fps、H.264 veryfast/CRF24，VBV 4Mbps/8Mb，关键帧间隔48帧；
  声音 AAC 128kbps/48kHz。奇数尺寸补齐为偶数；体积与清晰度、CPU 占用待实机验证。
- Shift+Scroll_Lock（Shift+Fn+O）启动录完编辑的独立流程，成功结束后打开 Screen Cut；
  支持剪头尾与删除中间片段。普通入口不打开编辑器，失败/空视频不打开。
  Screen Cut支持h/l与v/d剪辑、Ctrl+S另存/明确选择后的备份覆盖、Ctrl+C复制编辑结果。
  自动结束录屏时的剪贴板仍指向原录屏，编辑后Ctrl+C更新。
- 取消选区不录制；开始常驻通知，结束替换为保存位置，异常退出提示文件可能不完整。
  仅控制自己的临时用户服务，不停止其他录屏进程；无登录自启动服务，录制期间阻止
  自动空闲/睡眠。重复触发不并发启动，切换及真实画面验收由用户执行。

- 正常结束且输出非空时，自动将视频文件 URI 以 `text/uri-list` 放入 Wayland
  剪贴板，支持文件粘贴的应用可 Ctrl+V；不保证所有聊天/网页输入框接受文件。
  视频原文件继续保留。录屏失败或空文件不更新剪贴板；复制失败仍提示已保存。
  剪贴板 owner 必须独立于录屏服务存活，直到被新剪贴板内容替换。

- Screen Cut从固定Cachix输出声明式安装，提供Cmd+D菜单入口与图标；
  x86_64 Linux Niri宿主通过rerun获取，不依赖/data/project/screen-cut或临时profile安装。
  录屏编辑入口直接传媒体路径，不使用Avidemux的--load；不再修改Avidemux偏好。
  rerun启用fetch-closure以支持首次安装；系统switch仍由用户执行。

### 截图/录屏快捷键统一
- Fn+I截图、Shift+Fn+I截图后编辑，保留Ctrl+Fn+I整屏、Alt+Fn+I窗口截图。
- Fn+O开始/停止普通录屏；Shift+Fn+O录屏后编辑。Shift统一表示带编辑。
- 撤销旧Ctrl+Shift+Print与Alt+Shift+Print录屏入口，不占用现有窗口/工作区快捷键。
- 两个录屏组合均停止同一录屏服务；编辑模式以开始时为准。
- 构建/校验最终生成KDL，无重复绑定；真实键盘冲突与按键识别在用户switch后验收。

### Screen Cut波形与恢复更新
- 声明式安装包更新为含音频波形、时间轴缩放及用户状态目录自动恢复的版本；
  删除历史支持u撤销、Ctrl+r重做，关闭重开后仍有效。产品权威规格在
  /data/project/screen-cut/specs/005-waveform-recovery/；不改dufs-plus、不代用户switch。

### Screen Cut切点预览与手动字幕
- 固定缓存包升级到产品006/007：w/b切点导航、p/P循环、选区s输入字幕，保存/复制烧录字幕；
  字幕和删除共享撤销重做及恢复。波形仍只显示在编辑时间轴。
- 本次只修改包pin和010规格；真实中文IME验收和系统switch由用户完成，其他产品不在范围内。

### Screen Cut配乐与旁白
- 固定缓存包升级到产品008：音频文件/麦克风、叠加/替换、音量/移动/裁剪和统一试听导出；旁白作为普通音频片段。
- 功能权威规格在screen-cut/specs/008-audio-voiceover/；只修改包pin与010规格，不改录屏快捷键或dufs-plus，不代用户switch。

### Screen Cut缓存检查提示
- liu-bigpc的rerun在系统切换前显示Screen Cut缓存检查及命中信息；求值唯一包pin、核对Cachix精确输出并预取，任一步失败明确报错并停止切换。

### Screen Mark独立截图编辑器
- liu-bigpc声明式安装Screen Mark固定缓存包，提供Cmd+D入口与rerun缓存命中提示。
- Shift+Print(Shift+Fn+I)截图编辑改用Screen Mark，框选取消不打开、临时图直到编辑器退出再清理；原截图与视频快捷键不改。功能权威规格在/data/project/screen-mark/specs/001-screenshot-editor/。

Screen Mark数位板与共享核心由产品002/003管理。本仓安装固定缓存包，唯一pin在packages/screen-mark.nix；保持菜单、截图接线与rerun缓存提示。其他系统安装成品无需Bevy checkout或私有Git认证。用户已确认当前绘画可用与平滑手感；专项实机检查按产品任务追踪。

### YouTube 视频下载

- Home Manager 声明式安装锁定 nixpkgs 的 `yt-dlp`，支持视频下载及音频提取；包须包含 FFmpeg、Deno 与 yt-dlp-ejs 依赖。
- 命令、输出路径与更新方式放在 docs；不自动下载视频，不读取浏览器 cookies，不代用户执行系统 switch。
- 验证 liu-bigpc 完整系统、Home Manager generation、实际命令与运行依赖；真实 YouTube 网络下载单独验收。

### 本地字幕 OCR 工具

- 提供脚本从已下载视频的烧录字幕生成UTF-8 SRT，CPU本地处理，不上传媒体或读取Cookie。自动探测字幕位置，允许固定烹饪区域及显式裁剪；不能保证全部字幕样式适配，低置信度/稀疏/未定位结果标记待检查。
- 支持目录批处理、监测新完成视频、60秒检查点、同源同参数跳过、已有/手工编辑字幕保护及低磁盘空间暂停；保留数字变化与原始识别结果，不把自动输出视为人工校对。
- 固定Python依赖与模型随包版本，运行环境缓存于用户目录；不改系统/HM、不刷新锁定、不执行switch。
