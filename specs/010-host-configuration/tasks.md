# 任务

- [x] T001 收敛主机配置与密钥维护约束。
- [ ] T002 下次主机变更时分别核对构建、激活与桌面验收，不沿用旧快照作为现状。
- [x] T003 liu-bigpc 启用 BlueZ/Blueman，Waybar 条件增加蓝牙状态与管理入口，不改其他主机。
- [x] T004 验证蓝牙配置求值及 Waybar 生成内容；bluez/Blueman/powerOnBoot 为 true，JSON 有且仅有一个 bluetooth 模块和绝对路径管理入口。
- [x] T006 通过 just sync-todos 同步蓝牙规格与任务状态，checksum 复查通过。

2026-09-14：整机 toplevel.drvPath 求值通过（nmfr49zlkxhxkv842yi33jwcbln4jwxf）；
未执行完整构建、switch 或桌面验收，T005 保持待验证。已有 default.nix 暂存修改未动。
- [ ] T005 用户 switch 后验证 bluetooth.service、适配器与点击配对管理窗口；不自动配对或信任设备。
- [x] T007 为 Blueman 交互通知增加点击操作菜单与可见提示，取消此类通知5秒自动消失；不自动接受配对。
- [ ] T008 验证 Mako 生成配置和菜单脚本；switch 后由用户实测 Confirm/Deny，JBL 配对结果单独核对。

2026-09-14 真实链路验证：复用安装中的 Blueman _NotificationBubble，测试186的直接invoke
及用户点击测试188菜单Confirm均实际收到一次confirm回调；不是只验证菜单exit 0。
JBL随后读取Paired/Bonded/Connected均yes，未删除配对或断开。截图092736确认是旧通知157，
已单独dismiss（非确认/拒绝）；永久超时导致旧请求残留，改60秒且history=false。
图形菜单回调已通过，测试193的Deny菜单也实际收到deny回调；实际全新硬件配对的图形全流程仍未复测，取消及过期测试待补。
60秒/history=false规则求值通过，待用户rerun激活；未执行switch，未把真实配对全流程标记完成。

2026-09-14 Mako：生成配置求值、git diff --check 通过；蓝牙 actionable 规则含独立超时、
提示文本与绑定通知 ID 的菜单入口，普通5秒超时和勿扰模式保留。尚未 switch 或实测点击，
不能据此宣称 JBL 已配对成功。通知保留不延长 BlueZ/音箱自己的认证时限。

2026-09-14 点击失败复现：makoctl menu 缺少程序参数分隔符，Fuzzel 的 --dmenu 被当成
makoctl 参数，报 invalid option。补充 -- 后，用独立测试通知151和无副作用选择器验证
菜单命令退出0；Fuzzel显示测试单独执行，未操作JBL配对。修正后仍需switch及用户点击验收。

- [x] T009 liu-bigpc 增加数位笔"侧键+划动=滚轮"手势守护进程（evdev→uinput 虚拟笔带
  REL_WHEEL），普通划动/绘画不受影响；不改其他主机。
- [x] T010 手势状态机单元测试 14 项通过；`pen-scroll` 经 writePython3 打包成功
  （flake8 构建期校验通过），systemd 单元与 uinput 组求值正确。
- [x] T011 用户 rerun 后实机验收：侧键+**笔尖接触**划动滚动、悬空划动不滚动、
  不选中文本、侧键单击仍是点击、绘画与笔尖拖动选中行为不变（见 docs/pen-scroll.md）。
   2026-09-17 用户确认可用；首轮曾出现悬空也滚动，修正接触判定后通过。

2026-09-16 首次 switch 失败：`writePython3` 产出单文件，`home-manager-path` 的
buildEnv 拒绝合并（"is a file and can't be merged into an environment"）。
改用 `writePython3Bin` 后，`toplevel`、`home-manager-path`(glnpn00angymgmjw4rw3lwhzcxfmbdaq)
与 `home-manager-generation` 均构建通过；`home-path/bin/pen-scroll` 指向
`2wpr1abwcxcv60jv1y3dxpksnmvmwzd8-pen-scroll/bin/pen-scroll`。
教训已记入 docs/pen-scroll.md：只构建单个包不足以发现此类错误，必须构建到
home-manager path / toplevel。仍未 switch，T011 待用户验收。

2026-09-16 第二次 switch：toplevel 构建并激活成功（uinput 组 uinput:x:987:liou 生效），
但 home-manager 激活被 ~/.dsh/hooks/{hooks.json,notify-stop.sh} 两个手写遗留文件阻断
（398ac6d 声明、文件更早手写；HM 报 would be clobbered）。该冲突与本功能无关，但会
阻断整个 HM 激活并连带 pen-scroll 服务装不上。已在 flake.nix 设
home-manager.backupFileExtension = "hm-backup"，求值确认
home-manager-liou.service 环境含 HOME_MANAGER_BACKUP_EXT。用户需重跑 rerun 并重新登录，
T011 仍待桌面手势验收。

2026-09-17 第三次：服务已安装并启动，但 /dev/uinput 不可写导致退出循环
（evdev.uinput.UInputError，restart counter 70）。两处修复：(1) 服务加
SupplementaryGroups=[input,uinput]，由 systemd 启动时 setgroups，无需重新登录
（extraGroups 只写 /etc/group，附加组在登录时捕获，故对已有会话无效）；
(2) UInputError 派生自 Exception 而非 OSError，原 except OSError 抓不到，
已改为 retryable_errors() 并在 grab 前检查 /dev/uinput 可写性，且把
build_mirror 移到 grab 之前。toplevel 与 home-manager-generation 构建通过，
生成的 pen-scroll.service 含 SupplementaryGroups=input/uinput 且二进制含新逻辑。
仍未实测桌面手势，T011 待用户验收。

2026-09-17 权限方案定稿：SupplementaryGroups 在 user service 上以 216/GROUP 失败
（systemd#15659：systemd --user 无 CAP_SETGID）；udev uaccess 因 extraRules 落在
99-local.rules、晚于 73-seat-late.rules 的执行点而不生效（nixpkgs#308681）。
两条均回退，最终采用最简单的 extraGroups=[uinput] + **重新登录**。
toplevel 构建通过。**随后定位到真正的根因：本机启用 linger**
（configuration.nix 声明式创建 /var/lib/systemd/linger/liou），user@1000.service
不随注销停止、长期持有首次启动的组快照，因此"重新登录"对本机用户服务永远无效
（实测 id 有 input 无 uinput，而 /dev/uinput 权限正常）。最终改为 **systemd 系统服务**
（nixos/modules/pen-scroll.nix）：由 PID 1 启动、具备 CAP_SETGID，
SupplementaryGroups=[input,uinput] 正常工作且不依赖会话组快照；home-manager 用户服务
已整体移除。生成的 unit 已验证含 SupplementaryGroups=input/uinput、User=liou、
WantedBy=multi-user.target。无需注销/重启，待用户 switch 后验收手势。

2026-09-17 手势语义修正：用户实测反馈"悬空也会滚动"。原因是手势启动只判断越过
死区、未要求笔尖接触板面。已加 tip_down 条件，并把死区锚点改为**笔尖落点**
（先悬空移远再落笔不会立刻滚动）；同时修正 armed 期间被吞掉的落点收尾，
避免出现没有配对的抬笔事件。新增"悬空不得滚动"回归测试，共 25 项 pen-scroll 测试通过。
另外发现构建期 flake8 会报 W503（早先本地用 --max-line-length 未覆盖），
已改为提取 _should_begin_scroll() 规避行首二元运算符。toplevel 构建通过。

2026-09-17 体验修正（用户实测反馈"划动结束后又往回滚一点"）：复现确认这不是
灵敏度/死区问题，而是状态机 bug——抬笔只更新 tip_down、未结束手势，侧键仍按住时
引擎停留在 SCROLLING，把手部自然回带当成反向划动。已改为**笔尖离板即结束手势**并
回到 ARMED（对齐 libinput on-button scrolling：松开指定按钮即 stop_scroll）；
新增 gestured 标志避免滚动过的按压在松开侧键时补发点击。另按用户反馈把滚动速度
从 6mm/刻度调为 4mm/刻度（+50%）。pen-scroll 测试 32 项通过，toplevel 构建通过。

2026-09-17 起手响应修正：用户反馈"向上划相当长度才开始滚动"。量化确认死区只有 0.2mm
（非主因），真正延迟是"必须攒满一整格（4mm）才发滚轮事件"，即离散量化。
改为**越过死区即刻发出第一个刻度**（对齐 libinput "once engaged, any movement will
scroll"）：起始延迟 4.3mm→1.6mm，而同样划 45mm 前后都是 12 格，**速率不变**。
死区同时改为按分辨率换算的 **1.5mm**（原为抽象 20 单位），仅用于吸收点击抖动。
pen-scroll 测试 36 项通过，toplevel 构建通过。

2026-09-17 平滑滚动重构：用户反馈"还是不够顺滑，达不到用笔画线的效果"。
定位到根本限制——**数位板通道的滚轮轴是整数**（libinput 的 tablet_process_relative
只处理 REL_WHEEL，明确忽略 REL_WHEEL_HI_RES），因此只能整格跳。
改为**指针通道 + REL_WHEEL_HI_RES（v120）**，实测三证：libinput 输出连续值
`vert -0.75/-6.0*`；GTK4 客户端收到 `dy=-0.0250`（1/40 格）；应用层确实消费细粒度。
发现 libinput 的 ACC_V120_THRESHOLD=60 会丢弃起手小步，故起手先发一整格预热。
又因虚拟指针无法跟随焦点输出（niri 的 libinput 设备不报告输出，绝对指针会被映射到
双屏并集），增加 niri IPC 查询焦点输出几何并反解坐标；IPC 不可用时自动回退数位板通道。
测试 48 项通过（含坐标映射往返、包围盒、回退、预热），toplevel 与生成的 unit 均验证通过。

2026-09-16 pen-scroll：确认 niri 仅转发设备真实上报的数位板滚轮轴（smithay
`wp_tool.wheel`），libinput 只对 libwacom 标注带滚轮的笔产生该轴，Chromium
`WaylandTabletTool::Wheel()` 明确未实现，故必须软件翻译。已求值 hardware.uinput、
uinput 组、systemd 单元与包构建；未执行 switch，未由 Agent 代改本机系统，
T011 保持待用户验收。

