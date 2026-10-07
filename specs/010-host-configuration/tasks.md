# 任务

## Tag Browser 私有候选版系统安装

- [x] 将 Tag Browser 独立 flake 的私有 `stable` 提交锁入 `flake.lock`，仅 `liu-bigpc` 引用其浏览器包。
- [x] `rerun.nu` 在该主机切换前核对 Cachix 精确输出，支持首次使用 `fetch-closure`；系统配置也声明该特性。
- [x] 验证浏览器缓存路径、完整 NixOS toplevel、Home Manager generation 与 `.desktop` 入口，并同步规格镜像。
- [x] 用户在普通终端激活 `nix.6` 后确认设置弹层显示对应发行标签；系统启动路径解析到 `rkr6vns479n3ar7zf8568j11qa5rsm5v`。Agent 未代执行系统 switch。
- [ ] 继续验收尚未覆盖的桌面文件操作、阅读器、媒体与升级回退；先前安装版的 NUC 工作区切换已由用户确认。
- [x] `v0.1.0-nix.7` 锁定到 `248afd1`，Cachix 精确输出 `hrgw8llhmvg81sh1dn0iqi69y05kfs7b`；完整系统与 Home Manager 构建通过。用户在普通终端完成系统切换；系统命令与桌面入口均指向新包。旧窗口仍显示 `nix.6`，关闭后用户确认新窗口显示 `nix.7`。文件操作等真实窗口验收仍按 [手动测试用例](/data/project/tag-browser/specs/009-shared-tag-core/manual-test-cases.md) 执行。

- [x] `v0.1.0-nix.8` 已锁定私有正式 `stable` 提交 `06a9ecd`，Cachix 精确输出 `398kazfrbzxxha1z3wf5vi8rfasyii91` 与私有 Release 附件一致；完整 `liu-bigpc` toplevel `f8q5sf77lyikv73yc6rylx4nhbpvms3w` 构建通过，其中系统浏览器入口解析至该输出，启动脚本显示 `v0.1.0-nix.8`。Home Manager generation `dcaa7vlyc27dy6wdknk026jglscq8k1a` 已核对。Agent 未执行系统 switch；用户实际窗口版本和 M14/M17–M19 人工验收仍待完成。

- [x] `v0.1.0-nix.10` 已锁定私有正式 `stable` 提交 `e674258`，Cachix 精确输出 `/nix/store/05dxqxf29kvdv7x558lqibfh0byy4yj9-tag-browser-0.1.0` 与私有 Release 附件一致；完整 `liu-bigpc` toplevel `/nix/store/l01rw3di3ppwylxpbh4rs5649ss8z3pf-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 构建通过，系统浏览器入口解析至新缓存输出，Home Manager generation 为 `/nix/store/jm06d763dcrscivd16rv286xy16ri8ps-home-manager-generation`。用户系统激活和真实窗口验收尚未执行。
- [x] `v0.1.0-nix.11` 已锁定 Tag Browser 私有 `stable` 提交 `82f2436016947bb1c22f655a98e01c595721db6f`；Cachix 精确输出 `/nix/store/rj61500r77g02cp5afm1zc6wsh58cwbp-tag-browser-0.1.0` 与发行 CI、本机构建及 Release 附件一致。完整 `liu-bigpc` toplevel `/nix/store/gq4l3r4iqdn98zwyghdkqihacmpxkasj-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 构建通过，系统浏览器命令和桌面入口均解析至该输出；Home Manager generation 为 `/nix/store/9y9hnmq27cf8pjd190ys5wrl27f3wjyh-home-manager-generation`。构建包含工作树中已有的其他依赖锁定和 `gnumeric` 配置变更；本次仅提交 Tag Browser 输入。用户仍需在普通终端执行系统切换，之后实际窗口验证多个 NUC 目录并存和切换。
- [x] `v0.1.0-nix.12` 已锁定私有 `stable` 提交 `ee931f35759b37e0ebdb56d0351c75e1d42e70c8`，Cachix 精确输出 `/nix/store/vyf861h3i89xd8zgq2icq25rw9ig5q9z-tag-browser-0.1.0` 与发行附件及本机一致。普通点击文件默认新开标签页，目录原地导航；Node 40 项、Firefox 浏览器 320 项通过。完整系统 `/nix/store/iqkijp219znkyrpmwhgzgizqcy998czy-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 构建通过，浏览器命令和桌面入口解析至新输出；Home Manager `/nix/store/9y9hnmq27cf8pjd190ys5wrl27f3wjyh-home-manager-generation` 已构建。构建包含工作树已有依赖锁定与 gnumeric 配置，本次仅提交 Tag Browser 输入。用户执行系统切换后验收筛选列表普通点击 Markdown→PDF 时两个文件页并存；Agent 不执行工作站 switch。
- [x] `v0.1.0-nix.13` 已锁定私有 `stable` 提交 `621bbbf829490ccb52f202e70c8e0f85fe81b7cf`；每个文件标签页使用独立 DUFS 消息会话，修复 Markdown→PDF 两页被广播覆盖。Node 40 项、Firefox 351 项检查通过。CI、本机及 Release 输出 `/nix/store/zqix9hzj3iy0f0s0wmbs55z1gf3jn2im-tag-browser-0.1.0` 一致，Cachix 命中，包内修复源码一致。完整系统 `/nix/store/lcfijrv094qkn343dhf7il3im8jfdb8b-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 及 Home Manager `/nix/store/9y9hnmq27cf8pjd190ys5wrl27f3wjyh-home-manager-generation` 构建通过；系统命令和桌面入口均解析至新输出，启动器版本 nix.13。构建包含工作树已有依赖更新与 gnumeric 配置，本次提交仅包含浏览器输入和状态。用户尚需手动系统切换后复核两文件标签各自保留内容及路径。
- [x] `v0.1.0-nix.14` 已锁定私有 `stable` 提交 `aa037654b054a6305d4cbef44a94d8fd3766d6ad`；发布 URL 可见、窄侧栏及宽度记忆、侧栏开关和下载入口。NUC Markdown 目录、保存反馈和工具栏修复已通过 frontend 部署及内容复核。Node 40 项、Firefox 383 项检查通过。CI、本机、Release 与 Cachix 精确输出 `/nix/store/267l93c1ch10vs554r3h2y7kmqa836k9-tag-browser-0.1.0` 一致，包内 JS/CSS 与验证源码一致。完整系统 `/nix/store/6kmg3x22zkqy8wlg3h5jb9pvd2jx3n1b-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 和 Home Manager `/nix/store/9y9hnmq27cf8pjd190ys5wrl27f3wjyh-home-manager-generation` 构建通过；系统命令、桌面入口及激活单元已核对。保留工作树原有依赖更新和 gnumeric 配置，本次提交只含浏览器输入与状态；用户手动系统切换及实际窗口验收待完成。

候选版 `v0.1.0-nix.1` 固定 Tag Browser 提交 `8407033`、缓存输出
`qk0ib615vv19769l9faphk4mazl530da`。Cachix `path-info --refresh` 与
`nix copy --refresh --no-recursive` 均成功；完整 `liu-bigpc` toplevel
`vrh4rlm991kn08zfc6ivq6q7wjs1pyw2`、Home Manager generation
`dcaa7vlyc27dy6wdknk026jglscq8k1a` 构建通过。系统产物的
`sw/bin/tag-browser` 指向缓存包，`share/applications/tag-browser.desktop`
含桌面入口。配置求值含 `fetch-closure`，Home Manager 激活环境含
`HOME_MANAGER_BACKUP_EXT=hm-backup`。未执行 switch 或真实 GUI 验收。

候选版 `v0.1.0-nix.2` 固定 Tag Browser 提交 `95a9b08`，缓存输出
`cwlrzrvysycidl7x4mfkr57655h4n8sh`；发行 CI 与本机构建的 store path 一致，
Cachix narinfo 返回 HTTP 200。更新锁定输入后，完整 `liu-bigpc` toplevel
`qvakvibsz0ccqj73rjy5y0hpg76r1ria` 与 Home Manager generation
`dcaa7vlyc27dy6wdknk026jglscq8k1a` 构建通过；系统产物的浏览器命令与
`.desktop` 均解析至该缓存输出。未执行系统 switch；PC/NUC 直连工作区待实际窗口验收。

候选版 `v0.1.0-nix.3` 固定 Tag Browser 提交 `ca59bb2`，Cachix 输出
`jvaran6c056qvkywvg95zhkj4qvkyib8`；发行 CI 与本机构建路径一致，
Cachix narinfo 返回 HTTP 200。完整 `liu-bigpc` toplevel
`d640zmy849jnivg1picni1i6ww4lwzam` 构建通过，Home Manager generation
`dcaa7vlyc27dy6wdknk026jglscq8k1a` 已包含；系统浏览器命令与 `.desktop`
都解析到新缓存输出。已退出的旧浏览器进程不再阻止启动新版；未执行系统 switch，
真实 GUI 直连 NUC 与 Markdown 粘贴仍待用户验收。

候选版 `v0.1.0-nix.4` 固定 Tag Browser 提交 `3bebb09`，Cachix 输出
`ipbf75js23c6q65pcrk5a25ng872yfah`；浏览器能力检查和 tag API 复用
同来源的 Firefox HTTP Basic 认证，包的运行库路径含 Speech Dispatcher。发行 CI
与本机路径一致，Cachix narinfo HTTP 200；完整 `liu-bigpc` toplevel
`220pscfjw86fjnbndl2q7dbs9wdhiyxd` 构建通过，Home Manager generation
仍为 `dcaa7vlyc27dy6wdknk026jglscq8k1a`；系统浏览器命令与桌面入口
均解析到新缓存输出。未执行 switch；真实 NUC 切换、语音提示和 Markdown 粘贴
待用户在新版图形会话验收。

候选版 `v0.1.0-nix.5` 固定 Tag Browser 提交 `a532532`，Cachix 输出
`7yhknjdwfngaanjf8amwpqs4vvs6nqj5`；401 登录弹层已提供「登录并切换」
和就地反馈，输入凭据用于待切换工作区的验证与保存。发行 CI 与本机输出一致，
Cachix narinfo HTTP 200；完整 `liu-bigpc` toplevel
`677h7ivj5jidhah1d8zqzqh8138371j6` 构建通过，Home Manager generation
`dcaa7vlyc27dy6wdknk026jglscq8k1a`，浏览器命令与 `.desktop` 均解析到新包。
未执行 switch；PC/NUC 实际切换和图片粘贴待用户图形会话验收。

候选版 `v0.1.0-nix.6` 固定 Tag Browser 提交 `8c87a19`，Cachix 输出
`rkr6vns479n3ar7zf8568j11qa5rsm5v`。浏览器设置弹层现显示运行中的
发行标签；用户已确认上一候选版可切换至 NUC。发行 CI 与本机 Nix 构建
路径一致，Cachix narinfo HTTP 200。完整 `liu-bigpc` toplevel
`cqgy0xnpk3fb7w51r8d2sc20b9xkvckf` 构建通过，Home Manager generation
`dcaa7vlyc27dy6wdknk026jglscq8k1a` 已包含；系统命令与桌面入口均解析到
新包。Agent 未执行系统 switch；用户随后完成激活并确认设置弹层的
`v0.1.0-nix.6` 标签，当前系统的浏览器命令也解析到同一缓存包。

## 2026-09-27 桌面应用与通知整理

- [x] T017 封装嘉立创下单助手 5.0.69，提供桌面入口、主屏缩放和可执行的 Electron helper；用户已确认修复版能打开登录窗口。
- [ ] T018 用户登录后验收下单助手的实际业务流程；此前启动验证未覆盖登录。
- [x] T019 封装百度网盘 8.7.0 官方 DEB，使用独立锁定的 GTK2 依赖并仅向 liu-bigpc 提供。
- [ ] T020 用户激活后验收百度网盘启动、登录与文件传输。
- [x] T021 调整 Mako：ChatGPT/Antigravity 通知常驻，Blueman 操作成功后关闭旧提示。
- [ ] T022 用户激活后实测两类常驻通知与 Blueman 操作菜单。
- [x] T023 验证本次 liu-bigpc toplevel、HM generation、相关包和生成配置，记录结果并同步规格镜像。

本次仅提交声明式配置和规格，不执行本机系统 switch。
完整 toplevel `yayldwkq5jnwn34cypk56d6nan74wql8` 与 HM generation
`kaqwjilkfsxsrvfbyb0jklj97jyzjnqs` 构建通过；Mako 求值含普通通知 5000ms、
ChatGPT/Antigravity 0ms 和 Blueman 60000ms。`just test` 通过：deploy 44 项，
scripts 74 项（跳过 4 项）。构建不代表百度网盘和通知交互已经桌面验收。

- [x] T015 安装 FreeCAD，保留 Blender，验证 liu-bigpc 完整系统/HM 构建及桌面入口。
- [ ] T016 用户 switch 后验收 FreeCAD 启动、建模与保存；不代用户激活。

2026-09-20 FreeCAD：官方 AppImage 1.1.3 固定 SHA-256，Nix 封装构建通过；
临时 XDG 目录下 `freecad freecadcmd --version --safe-mode` 返回 1.1.3，退出 0。
桌面入口为 FreeCAD，命令为 freecad，使用官方 SVG 图标；Blender 保留。
完整 toplevel `j8vv5nwlmfa9zfgwcijqkv42gzahws64` 与 HM generation
`64gswn69klvhhidmz5nxzlfbj08wncnc` 构建通过。未 switch、未实测图形建模。
本次不新增服务、组、内核模块或 udev 规则，对应验证项不适用。

- [x] T012 声明 KiCad 与官方嘉立创 EDA 专业版 3.2.203 的独立包和 Home Manager 模块。
- [x] T013 EDA：校验官方包哈希/入口，构建两个应用、liu-bigpc toplevel 和 home-manager-generation。
- [x] T014 EDA：用户手动 switch 后验证启动器、界面缩放、中文输入及工程保存；不代用户激活。

2026-09-23 EDA 缩放：针对用户实测反馈默认 XWayland 下界面与字体过小（96 DPI 1.0x 渲染）的问题，
在 `home-manager/packages/lceda-pro.nix` 增加 scaleFactor 参数与 launcher 包装脚本，
动态注入 `--force-device-scale-factor`；并在 `nix_modules/eda.nix` 中将 `features.niri.primaryOutputScale`
（liu-bigpc 为 1.5）传入。用户手动 switch 后实机验证界面与字体放大生效，大小恢复正常。

2026-09-20 EDA：KiCad 10.0.6 构建及临时 XDG 目录下 `kicad-cli version` 通过。
嘉立创 3.2.203 官网 ZIP SHA-256 已验证；使用 libarchive + C.UTF-8 处理上游中文
EULA 文件名编码不一致，保留许可证，不执行上游 chmod 777/root 安装脚本。
官方 Electron 36.3.1 Node 模式启动成功，12 秒 headless 冒烟测试加载 SQLite，
未传 --no-sandbox，最终由 timeout 停止（124，非正常退出）；出现 fontconfig
兼容警告，未做真实界面验收。图标、desktop 入口与命令均已检查。
完整 toplevel `7avxa1pr11j87jf4pb54wd88aihkbm64` 与 HM generation
`bkj630dbsf392fmf3s2241i0nbfpzpw3` 构建成功，HOME_MANAGER_BACKUP_EXT=hm-backup。
未 switch；本任务不新增服务、组、内核模块或 udev 规则，对应验证项不适用。

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
   后续追加验收：平滑滚动（v120 高分辨率滚轮）与指针落点（复刻 niri 映射后
   偏差 0.000000 px）均已由用户确认"不乱动、很丝滑"。

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

2026-09-17 指针偏移修正：用户反馈"划动时鼠标指针不在原位，结束才恢复"。
根因为坐标映射算法不一致——第一版用**留黑边(letterbox)**，而 **niri 用裁剪填满(cover)**，
非中心位置最大相差约 107 逻辑像素，指针因此落在偏离笔尖处。
已按 niri 的 compute_tablet_position 逐步复刻（含 transform 与 ratio 裁剪分支），
用 niri-ipc 真实双屏几何对照最大偏差 **0.000000 px**（Dell Normal 与 Philips 旋转 90°
均通过）。测试增至 49 项。

2026-09-16 pen-scroll：确认 niri 仅转发设备真实上报的数位板滚轮轴（smithay
`wp_tool.wheel`），libinput 只对 libwacom 标注带滚轮的笔产生该轴，Chromium
`WaylandTabletTool::Wheel()` 明确未实现，故必须软件翻译。已求值 hardware.uinput、
uinput 组、systemd 单元与包构建；未执行 switch，未由 Agent 代改本机系统，
T011 保持待用户验收。

## 2026-09-30 PC 私人节点恢复

- [x] 核对 Tag Browser nix.8 空列表：本机 `127.0.0.1:5006` 无响应，NUC 接口正常；01:01:10 系统收到用户管理器中的 `shutdown` 进程（PID 2293411）发起的整机关机请求；随后用户管理器终止、五个 `dufs-plus-pc` rootless Podman 容器收到停止信号。07:17 再次开机后容器未自动恢复。日志未显示单独停止容器，也不能确定是谁或什么程序启动了 `shutdown`。浏览器运行逻辑未变。
- [x] 启动原有五个容器，确认本机 locations 为 2、tags 为 44，相关 API 返回 HTTP 200；未重建容器或修改持久化数据。
- [x] 为 liu-bigpc 配置 Home Manager 用户 oneshot 服务：用户管理器启动时，仅恢复 compose 标签为 `dufs-plus-pc`、重启策略为 `unless-stopped` 且处于 exited 状态的原有容器。
- [ ] 用户手动 switch 后验证服务已安装，并在下次用户管理器重启后确认 PC 节点自动恢复、Tag Browser 标签及工作区正常显示；Agent 不执行工作站 switch。

- [x] `v0.1.0-nix.15` 已锁定私有 stable `d4fa799ed68cce54f010e4d29040dcf05039bddf`：统一两行头部、列表区域已打开组及真实窗口宽度恢复；Node 40 项、Firefox 361 项通过。私有 Release、CI 36828143469 与本机输出 `/nix/store/yhgcdfw8b0zh39xd4gzf57bsqa4j773n-tag-browser-0.1.0` 一致且 Cachix 命中。完整系统 `/nix/store/pr5dlhxzn7p4xl0hmxh03qbp8myvm6ng-nixos-system-liu-bigpc-26.11.20260922.b6c98e9`、Home Manager `/nix/store/zl7xn3ddcbnl2hiflxxz7vgj8a6bncvc-home-manager-generation` 构建通过，系统命令/桌面入口/激活 ExecStart/hm-backup 均核对。保留工作树原有 AGENTS、依赖和 gnumeric 改动；只提交浏览器输入及发行状态。用户手动切换和试用待完成。

- [x] `v0.1.0-nix.16` 已锁定私有 stable `f3bcdb0958c918a00ca3076bc42dc8352b6f25cc`：共用 Web/文件标签徽标、连续打标保留选择、按约定退出多选；Node 40 项、Firefox 377 项通过。CI 36847770030、本机及私有 Release 输出 `/nix/store/ify4f3jfsn7m5rrl2w3dvy4wfy98274c-tag-browser-0.1.0` 一致，Cachix narinfo 命中。完整系统 `/nix/store/l1250ah7i7gxnz1szw1dcjqzzaim7y8k-nixos-system-liu-bigpc-26.11.20260922.b6c98e9`、Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过；浏览器命令、桌面入口、激活 ExecStart 和 hm-backup 环境核对。保留工作树原有 AGENTS、其他依赖及 gnumeric 改动；仅提交浏览器输入与发行状态。用户手动 switch 和真实安装版试用待完成；宽度沿用 nix.15 修复，未重复修改。

- [x] `v0.1.0-nix.17` 已锁定私有 stable `c694cb44994a6b052b7e5d89746cb42daff1d895`：普通导航复用当前页、每页独立筛选与会话恢复、固定条件摘要；Node 44 项、Firefox 410 项通过。CI 36859693129、本机、私有 Release 与签名 Cachix narinfo 精确输出 `/nix/store/jzj0k8cink35v43lqzxg51fh8k06izqb-tag-browser-0.1.0` 一致，安装包源码/默认启动 3/桌面入口/隔离配置启动核对。完整系统 `/nix/store/cd4ahh890gzz0m4r9g6vmz1181hn59p9-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 和 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过，系统浏览器命令、桌面入口、激活 generation/wrapper 及 hm-backup 环境核对。NUC Markdown 光标行修复已部署，index 摘要 `12df80178bc95455c4e228ae7333e17a8b0227f8b9060a9245a23ac323692612`、备份 `frontend-cvocpxAN.tar`，rsync/认证入口检查及 Bevy 目录保护通过。保留工作树既有 AGENTS、其他依赖及 gnumeric 变更，本次仅提交浏览器输入和发行状态；用户手动工作站 switch 及真实安装版试用尚未执行。

- [x] `v0.1.0-nix.18` 已锁定私有 stable `0a53f339933c4c555a1438d63ad4553202ca9eb9`：筛选入口移到固定高度底栏，详情向上展开，列表边界不随条件或展开状态改变。Node 44 项、Firefox 421 项检查通过。CI 36865851454、本机、私有 Release 精确输出 `/nix/store/fzw3rb1x8crzzzinhnzwxfhlgynz4cyl-tag-browser-0.1.0` 一致，Cachix 信任签名核对；PC 归档 SHA256 `b88d3035442a0fb0694185d1bdc7f9194e5d40a42084edd22f15bd904b544a80` 与 GitHub 上传摘要一致，包内 JS/CSS、启动默认 3、发行标签、桌面入口及隔离配置启动核对。完整系统 `/nix/store/0gya2w7xrd0cy5sp1dyh1vzl8yxpbxn8-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 与 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过，系统命令/桌面入口/激活 generation 和 wrapper/hm-backup 均核对。保留工作树既有 AGENTS、其他依赖及 gnumeric 改动，本次只提交浏览器输入和发行状态。未部署 DUFS，用户手动工作站 switch 及安装版试用待完成。

- [x] `v0.1.0-nix.19` 已锁定私有 stable `4fbd40276d71e424f1c0175dff07e5ced583c099`：设置原生顶层浮层避免地址栏遮挡版本号，设置和筛选详情使用适应明暗模式的不透明底色。Node 44 项、Firefox 433 项检查通过；CI 36872101871、本机、私有 Release 与 Cachix 精确输出 `/nix/store/6rcfylmfni7idrqmbah64ngqgzcadvfm-tag-browser-0.1.0` 一致，缓存签名信任核对通过。PC 归档 SHA256 `961da74df18804bcafdeb34446b2f52a22faff00e3a284033605be68d4f6a4da` 与 GitHub 摘要一致，包内 JS/CSS、启动默认 3、发行标签和隔离配置启动核对。完整系统 `/nix/store/swl0qsd5zlidibyh3ziz0nf01h8m3inf-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 和 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建成功；系统命令、桌面入口、激活 generation/wrapper 和 hm-backup 环境核对。保留工作树既有 AGENTS、其他依赖及 gnumeric 改动，仅提交浏览器输入和发行状态。用户手动工作站 switch 及安装版试用待完成。

- [x] `v0.1.0-nix.20` 已锁定私有 stable `754ce75af5594a0366077b7958ec78cd99ab45c7`：已打开固定上方并独立滚动，目录/筛选结果按实际页面与节点上下文恢复滚动位置。Node 44 项、Firefox 456 项检查通过；CI 36875961801、本机、私有 Release 和 Cachix 精确输出 `/nix/store/p94lf165s9krpmsycbpsiakzh1m45szl-tag-browser-0.1.0` 一致，签名信任验证通过。PC 归档 SHA256 `dfd93ab8aa6bf2b16666e91ec24303405f1b1d9310a5adeb3c848bf6f9319a70` 与 GitHub 摘要一致，归档源码、启动默认 3、发行标签、桌面入口及隔离启动核对。完整系统 `/nix/store/fiqwpv6q0nlda5ax6d5a4zfjjcfb4xfw-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 和 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过，命令/桌面入口/激活 generation 与 wrapper/hm-backup 均核对；最终发行记录提交后的系统输出保持一致。保留原有 AGENTS、其他依赖与 gnumeric 变更，仅提交浏览器输入及发行状态。用户手动工作站 switch 及真实安装版试用待完成。

- [x] `v0.1.0-nix.21` 已锁定私有 stable `c8b2262754cab8bd5455aa2967e622ce5151f904`：上下分区支持拖动与键盘调整高度、分别向上/向下折叠，并记忆比例和独立折叠状态，展开恢复滚动位置。Node 44 项、Firefox 481 项检查通过；CI 36881779698、本机、私有 Release 和 Cachix 精确输出 `/nix/store/p6407jikdw2rvi0cr0di8sgsxk6hvfxi-tag-browser-0.1.0` 一致，签名信任验证通过。PC 归档 SHA256 `b7c8e0d53a06509def71a4f41a8973b6ff13f546bd08fc0f4ea1b95667fd0554` 与 GitHub 摘要一致，归档源码、默认会话恢复 3、发行标签、桌面入口和隔离启动核对。完整系统 `/nix/store/nnrk8z7d8i2xn3xwdy39m9bmmrhpqbf6-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 与 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建成功，系统命令/桌面入口/激活 generation 与 wrapper/hm-backup 均核对；最终发行记录提交后的系统输出保持一致。保留既有 AGENTS、其他依赖和 gnumeric 变更，仅提交浏览器输入及发行状态。用户手动工作站 switch 及实际安装版试用待完成。

- [x] `v0.1.0-nix.22` 已锁定私有 stable `05ec0819d6fbd7a6cfc6491a53b3a017e43e455a`：筛选详情入口统一到标签标题的计数处；无标签/仅排除筛选的目录网格和瀑布流恢复同步滚动，视频定位恢复；标签右键工具栏支持点击外部空白处和 Esc 关闭。Node 44 项、Firefox 498 项检查通过；CI 36889587449、本机、私有 Release 和签名 Cachix 精确输出 `/nix/store/aa8qw1mf5mvylvjvrhzpqz4ngslvp63s-tag-browser-0.1.0` 一致。归档 SHA256 `2f70d37f37fc1fb8381ac26116c18dbbc427905f4c44026684d2bc9bddccdaa0` 与 GitHub 摘要一致；包内源码、默认会话恢复 3、发行标签、桌面入口及隔离启动核对。完整系统 `/nix/store/0llx8a5n56z58svb39k5g77vbb3ldcnj-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 与 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过，系统命令/桌面入口/激活 generation 与 wrapper/hm-backup 环境核对；最终发行记录提交后的系统输出保持一致。保留既有 AGENTS、其他依赖和 gnumeric 变更，仅提交浏览器输入及发行状态。用户手动工作站 switch 和安装版试用待完成。

- [x] `v0.1.0-nix.23` 已锁定私有 stable `7c06dac16068f61b9cb2daff254a2e1d7145bd11`：文件待办琥珀/今日绿色与 countdown 数字按钮，递减到零完成，正文和其他元数据保留；按节点与版本保护写入，保存不重绘列表，保持滚动/URL/筛选/多选。Node 54 项、Firefox 530 项检查通过。CI 36894617831、本机、私有 Release 和签名 Cachix 精确输出 `/nix/store/3pjpf4z8kxz231dkl775myjmd9dqnng9-tag-browser-0.1.0` 一致；归档 SHA256 `1c04ba4dc476787a7b7b24499b33ee43e70a0b3dcd64f5ab798ad9b1cdf627cd` 与上传摘要一致。包内模块、锁定 YAML 与许可证、默认恢复 3、发行标签、桌面入口和隔离启动核对。完整系统 `/nix/store/2a8lwp8r6wkbypi3ybc77s624638yw0c-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 与 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过；系统命令/桌面入口/激活 generation 与 wrapper/hm-backup 环境核对，最终发行记录提交后的系统输出保持一致。保留既有 AGENTS、其他依赖与 gnumeric 改动，仅提交浏览器输入和发行状态。用户手动工作站 switch 与安装版试用待完成。


- [x] 私有 `v0.1.0-nix.24` 已发行并锁定 Tag Browser `7f50e65e1c60d090ec550a9c3de9b459282bffee`：多窗口节点/认证隔离、正常关窗恢复及菜单、目录待办恢复与按标签页隐藏完成。Node 67 项、Firefox 643 项检查通过；最终 Nix 二进制 5/5 快速正常关窗/重启场景通过。CI 37008161500、本机、Release 与签名 Cachix 精确输出 `/nix/store/5ybm3k8ddc36xc1mzzq8b4fx3ysvlxsb-tag-browser-0.1.0` 一致，归档 SHA256 `061ca63477f8bb6c61cdbd636cd65130eee2f41129a14d9310193d31744b8af3` 与 GitHub 上传摘要一致。完整系统 `/nix/store/25d4plwx2cz5yzysqc3vvr0chsc3hipx-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 与 Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过，系统命令/桌面入口/激活 generation 核对。只提交浏览器输入和发行状态，保留原有 AGENTS、其他锁定依赖及 home-manager 改动；构建不表示系统已切换。用户在普通终端运行 `nu rerun.nu liou --host liu-bigpc`，随后按 Tag Browser 012 固定三组收尾检查，Agent 不执行 switch。


- [x] 私有 `v0.1.0-nix.25` 已发行，Tag Browser 锁定 `5206662d05b931b6ff3b0a222e36a5fc2f60b044`：顶部/底部工具栏图标、悬停提示、可访问名称与 32px 点击范围。67 项 Node、713 项 Firefox 检查通过；CI 37016820898、本机、Release 精确输出 `/nix/store/axrq2cjzqlnb4117gyqrs2bkwjgv0b3l-tag-browser-0.1.0` 一致，Cachix 命中和签名信任通过。完整系统 `/nix/store/41wsrqqz1jra4llzy5r9asa6j657vn9z-nixos-system-liu-bigpc-26.11.20260922.b6c98e9`、Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建通过，系统浏览器命令与激活目标核对。保留既有 AGENTS、其他锁定节点与 home-manager 改动，仅更新浏览器输入。Agent 不执行 switch，用户在普通终端运行 `nu rerun.nu liou --host liu-bigpc` 并确认 app nix.25。


- [x] 私有 `v0.1.0-nix.26` 已发行并锁定 `8a2327abe02ebc6b0c94678ffd234d1676139760`：继承 nix.25 工具栏图标，新增 Ctrl+T/切页/关页活动行定位及地址栏左侧原生后退/前进。67 项 Node、724 项 Firefox 检查通过，CI 37020228750 成功，PC/Release/签名 Cachix 精确输出 `/nix/store/8hkindcisj8rm57l0ph60kvqb587sd18-tag-browser-0.1.0` 一致。归档 SHA256 `58681f6ce776c96a094bbec1b466621fe5a109c515da36dc51aa50f8530f15cc` 与上传摘要一致，包内模块/路径边界/临时配置启动/版本核对通过。完整系统 `/nix/store/jch484cbsjqkqplnjfwkb1izqy8alnfv-nixos-system-liu-bigpc-26.11.20260922.b6c98e9`、Home Manager `/nix/store/q15phfx28v6slnc9li55qbl6wfr25f90-home-manager-generation` 构建成功，系统命令、桌面入口及激活目标一致。仅提交浏览器输入与状态；既有 AGENTS、其他依赖及 home-manager 工作树改动保持。Agent 不执行 switch；用户运行 `nu rerun.nu liou --host liu-bigpc`，正常关闭旧窗口后重开并确认 nix.26。

## Satty 截图标注

- [x] 仅 liu-bigpc 加入 Satty，保留原截图键，增加 Shift+Print 框选后编辑。
- [x] 验证完整 toplevel、Home Manager generation、生成 KDL 与脚本依赖；Satty 0.22.0 来自缓存，脚本 ShellCheck 和 Niri validate 通过，安装命令及 HM 激活目标一致。
- [ ] 用户手动 switch 后实测 Shift+Fn+I、标注复制/保存及取消行为。

## wf-recorder 快捷键录屏

- [x] 仅 liu-bigpc 添加 wf-recorder 和 Ctrl+Shift+Print 开始/停止框选录屏，保留截图快捷键。
- [x] wf-recorder 0.6.0：完整系统/HM、KDL 和 ShellCheck 通过；9 项不捕获桌面的控制检查通过，合成视频确认奇数尺寸补齐后 H.264/yuv420p 编码有效，命令及 HM 激活目标核对；真实画面/性能留待用户验收。
- [ ] 用户 switch 后验证 Ctrl+Shift+Fn+I、取消、通知、MP4 播放及 CPU 占用。

## 录屏后复制文件

- [x] 正常停止后自动复制文件 URI，独立剪贴板生命周期，失败保留原文件并通知。
- [x] 完整系统/HM、Niri validate 和 ShellCheck 通过；隔离检查覆盖 URI 特殊字符/MIME、独立剪贴板 owner、复制成功与失败通知、失败/空录屏不复制；未修改当前剪贴板。
- [ ] 用户 switch 后验证视频在目标聊天应用 Ctrl+V 附件粘贴。

## 录屏声音、压缩与轻量剪辑

- [x] 默认系统声音，Waybar 左键选择系统/麦克风/两者/无声，右键开始/停止；
  无麦克风明确拒绝，录制期间拒绝切换，混音模块失败/结束清理且核对所有权。
- [x] 使用24fps、H.264 veryfast/CRF24、VBV4Mbps/8Mb、48帧 GOP、AAC128kbps/48kHz；
  合成720p视频确认24fps H.264及AAC音轨，真实体积、清晰度和CPU待用户试用。
- [x] 添加 Alt+Shift+Print 独立编辑入口，成功结束后打开 Avidemux 2.8.1；普通录屏不打开，
  文档说明 Copy关键帧剪切、另存与原文件剪贴板。
- [x] 8项Python音源/失败清理回归、9项隔离录屏控制检查、ShellCheck、Niri validate、
  Waybar JSON、编辑器实际路径及完整系统/HM构建通过；不捕获真实桌面/音频、不更改剪贴板。
- [ ] 用户手动switch后实测Waybar音源菜单、系统声音、编辑快捷键和MP4剪辑；
  检查实际播放同步、CPU占用与传输体积，接入麦克风后再验证麦克风/混音。

## Avidemux 预览蓝屏修复

- [x] 确认实机使用软件解码但VDPAU显示；添加screen-record-edit合并Qt软件预览/解码偏好，
  自动备份、原子更新，保留其余偏好和视频原文件。
- [x] 完整系统/HM、ShellCheck、Niri validate、HM激活目标与4项隔离配置检查通过；
  独立Xvfb加载9.166秒录屏副本正常退出，帧缓冲截图目视确认画面和Lavcodec/RGB。
  仅写临时HOME，未修改用户当前偏好、未切换系统、未捕获用户桌面。
- [ ] 用户手动switch后关闭旧编辑器并重开视频，验证当前Niri会话中的预览和剪辑。

- [x] v0.1.0-nix.27 已锁定私人 stable f55bed647022a53edc9547bbfa9510196ab64bf7：紧凑原生后退/刷新/前进。CI 37097191342、本机、Release/Cachix 精确输出 /nix/store/kkqb2kyqxvqwqq3vsjssn8xwx8cfwpak-tag-browser-0.1.0 一致，缓存命中与预取通过。完整系统 /nix/store/6brxrs87p668iad3xkyvwk6afr6xg2xh-nixos-system-liu-bigpc-26.11.20260922.b6c98e9 和 Home Manager /nix/store/ibkqmbdcw1b27a751zz1qbidwsa1ics2-home-manager-generation 构建通过。保留工作树既有 AGENTS、home.nix 和其他依赖更新，只提交浏览器锁输入与本条发行状态；未执行用户系统 switch。NUC 前端图片粘贴新鲜位置校验已部署，实际剪贴板待用户验收，详情以 dufs-plus 009 为准。

## Screen Cut菜单、声明式安装与自动编辑
- [x] 固定packages/screen-cut.nix Cachix输出并安装到Niri home.packages；rerun支持首次fetch-closure。
- [x] 用Screen Cut替换录屏编辑接线，成功且--edit才打开刚录制文件，普通/失败/空文件不打开。
- [x] 验证完整liu-bigpc toplevel、Home Manager generation、desktop/KDL/ShellCheck与隔离收尾行为；用户switch待执行。

## 截图/录屏快捷键统一
- [x] 检查现有键位，改录屏为Cmd+S/Cmd+Shift+S，截图保留Fn+I/Shift+Fn+I；手册与规格同步。
- [x] 校验最终KDL的快捷键唯一性和动作、Niri validate、完整系统/HM构建；镜像与提交。
- [ ] 用户应用配置后验证实际键盘截图、录屏与录完自动编辑。

验收：最终126个Niri绑定无重复；Print/Shift+Print/Ctrl+Print/Alt+Print保留，
Mod+S与Mod+Shift+S正确映射普通/--edit录屏，旧录屏组合已移除。
Niri validate、完整liu-bigpc系统与Home Manager构建通过；没有录用户桌面、没有switch。
原Alt+Shift+Fn+I具体实机冲突源尚未确认，不把避开旧组合视为已确认输入法或固件故障。

## HHKB右手Fn区录屏
- [x] 将录屏改为Fn+O（Scroll_Lock）/Shift+Fn+O，保留Fn+I截图与Shift+Fn+I编辑，释放Cmd+S组合；规格手册同步。
- [x] 验证最终绑定唯一性、动作和旧组合移除、Niri validate、完整系统/HM；镜像并提交推送。
- [ ] 用户应用配置后验证HHKB实际Fn+O/Shift+Fn+O识别及录屏收尾编辑。

Fn+O验收：最终126个绑定无重复；Scroll_Lock/Shift+Scroll_Lock正确映射
普通/--edit录屏；Print家族截图和XF86AudioRaiseVolume保留，所有旧录屏组合移除。
Niri validate、完整系统及HM构建通过。实际HHKB按键仍待用户应用配置验证；未执行switch。

## Screen Cut波形与恢复缓存更新
- [x] 发布与核验新版desktop bundle gdybxp8862gwmy6c5qfc70wzm0p072j2；程序pir9q22hmk7vgi00cny9yvc158z4w2ar，三个新增路径签名、bundle归档SHA256通过。
- [x] packages/screen-cut.nix更新固定缓存输出；完整liu-bigpc toplevel mbgs58ij78k7xp9a6mpxr8d4qk9i3kkp、HM 4m2l11gvcvd7y4x8mc3s2a8md5sxzz22构建通过，home-path命令与desktop Exec均指向新版程序。
- [x] 产品27单元测试、合成媒体/软件预览、隔离Xvfb重启后undo/redo与zoom、独立Wayland视频复制回归通过；权威规格为screen-cut 005。
- [ ] 用户普通终端rerun后关闭旧窗口，验收波形、缩放和相同视频恢复。

本次只提交Screen Cut pin与010对应规格；保留既有AGENTS、其他依赖锁和home.nix变更。
构建包含这些工作树已有变更，不代用户执行switch；录屏快捷键与dufs-plus未改。

## Screen Cut切点与手动字幕更新
- [x] 发布并核验006/007运行包、缓存签名及归档摘要，更新固定包pin。
- [x] 验证完整liu-bigpc系统/HM和命令/desktop目标，镜像与提交推送。
- [ ] 用户rerun后验收切点循环、中文IME、字幕保存与复制。

产品权威规格为screen-cut 006/007；用户系统尚未切换。

当前006/007发行：bundle sxr1p0xkxa474c07c0xz6y3lm0m6253w，程序8hl15snq8k9xv7hl8vhj1ngwhp0qizc4；
三输出可信签名、匿名bundle归档长度与SHA256通过。完整系统p9sdw6fwdn8c5bl43xbnzk9j7l75sgmw、
HM 3kzmsikh4r3xzqq9kmy3gc2mhnylma0x构建通过，home-path命令及desktop Exec均指向新版。
产品35单元测试、clippy、旧GUI回归、发行包媒体/字幕/循环与独立Wayland复制通过。
本次只提交pin和010规格，保留AGENTS/flake.lock/home.nix已有变更；未执行switch。

## Screen Cut配乐与麦克风旁白更新
- [x] 发布008运行包，固定bundle arrsa3p4q795xkw02503wrz9xyr4wmq4；程序syk31fg5kxddwg3vmmlp5rrrbz4bvdyg、desktop bxk4vxp8cajacpzfpq1rh2bh2lgny5ps，三输出可信签名及匿名bundle长度/SHA256通过。
- [x] 完整liu-bigpc系统h39k8qir3jxgczimp8l2hraqj38wmfj6、HM xdjymz1d21s68z0082c2p9cw8b8g6cr1构建通过，home-path命令及desktop Exec均指向新版；镜像与提交推送。
- [x] 产品41单元测试、clippy、旧GUI回归、正式程序配音/mock麦克风及wrapper媒体/字幕/循环、独立Wayland复制通过。
- [ ] 用户rerun后关闭旧窗口，实测麦克风旁白、叠加/替换、输入延迟与保存/复制，按产品008 quickstart。

仅提交Screen Cut pin与010规格；保留既有AGENTS、flake.lock、home.nix改动，完整构建包含当前工作树。
录屏快捷键、其他产品不变；自动化不采集真实输入，Agent未执行switch。

## Screen Cut缓存提示
- [x] rerun在liu-bigpc切换前求值screen-cut-binary-path，核对并预取Cachix精确bundle，显示检查/命中信息；错误阻止切换。pin仍仅来自packages/screen-cut.nix。
- [x] nu-check和独立真实缓存检查段通过；完整系统h39k8qir3jxgczimp8l2hraqj38wmfj6与HM xdjymz1d21s68z0082c2p9cw8b8g6cr1构建通过，安装产物保持一致。镜像与提交推送；未执行switch。

- [x] 私有 nix.28 已锁定 Tag Browser d090045a1233ccc5e4f783738acdee813c4e51b3，修复原生导航按钮悬停多余背景。67 项 Node、750 项 Firefox、最终包 5 个多窗口恢复场景及隔离包装器版本启动通过；CI 37123646286 成功，PC/Release/Cachix 精确输出 /nix/store/4c7w0fp52hlwbrp7mnj2bdy3ivdzhrrj-tag-browser-0.1.0 一致，缓存签名导入与验证通过。完整系统 /nix/store/a0ji9jsl8zjlgqbhcdvi43khlp9a1sr9-nixos-system-liu-bigpc-26.11.20260922.b6c98e9 和 Home Manager /nix/store/xdjymz1d21s68z0082c2p9cw8b8g6cr1-home-manager-generation 构建通过，实际系统浏览器路径和激活备份设置核对。只更新浏览器锁节点，保留 AGENTS、home.nix 与其他输入的既有修改；Agent 不执行 switch。用户普通终端执行 nu rerun.nu liou --host liu-bigpc，正常关闭旧窗口再重开确认 nix.28。


## 当前 Tag Browser nix.29 发布

- [x] 锁定私人 stable 66a0b28ff8119fca593f96e734d2b1dc2c209425，默认启用 Firefox 原生兼容 token，修复 Bilibili 浏览器过低跳转。67 项 Node、778 项 Firefox 检查、最终包 5 个多窗口恢复场景通过；CI 37131641915 成功，PC/Release/Cachix 精确输出 /nix/store/krx6h0rdgq803r76pz5zrdsvx38yb5vw-tag-browser-0.1.0 一致，缓存命中和签名验证通过。
- [x] 完整系统 /nix/store/lx962ngr6y98vx7sdkzx8zhqcizpa4il-nixos-system-liu-bigpc-26.11.20260922.b6c98e9 与 Home Manager /nix/store/xdjymz1d21s68z0082c2p9cw8b8g6cr1-home-manager-generation 构建通过，系统浏览器及桌面入口核对。仅更新浏览器锁节点与本段状态，保留既有 AGENTS、home.nix、其他锁节点修改；未执行 switch。
- [ ] 用户在普通终端运行 `nu rerun.nu liou --host liu-bigpc`，正常关闭旧窗口后重新打开，确认 app nix.29 并访问 Bilibili 首页和实际视频。

## Screen Mark 截图编辑器与共享绘画核心

- [x] 声明式安装固定Cachix包、菜单图标及rerun独立缓存命中提示。
- [x] Shift+Fn+I接入Screen Mark，截图脚本隔离回归、Niri配置及唯一快捷键核对通过。
- [x] 当前共享核心版的可信缓存/运行依赖、完整liu-bigpc系统/HM、实际二进制和desktop入口核对通过；规格镜像与提交推送。
- [x] 用户确认当前绘画可用及平滑手感：“可以了，挺好用的”；产品003已完成。
- [ ] 截图键、中文IME、目标网页图片粘贴等实机专项按screen-mark 001追踪。
- [ ] 压力笔宽、悬停/抬笔/移出、翻转橡皮等实机专项按screen-mark 002追踪。

产品功能权威规格在/data/project/screen-mark/specs/，本仓仅管理安装与接线。当前发行pin以packages/screen-mark.nix为准；共享库17测试、本产品9测试/Clippy和正式GUI/tablet-v2回归通过，运行闭包由官方Nix缓存与应用Cachix提供且签名可信。
当前手感已由用户确认；专项检查不因总体反馈自动勾选。Agent不执行switch，保留既有AGENTS、flake.lock、home.nix改动。

## Tag Browser nix.30 安装输入

- [x] 固定 product stable 74c8d27676bc39fcbfd94844b77c3c3eb32e00b9；本机、Release、Cachix 输出 /nix/store/bnx9dp6xpf6y0iakx3mgx9ai5cy6cvzv-tag-browser-0.1.0 一致，缓存受信任签名通过。71 项 Node 和 783 项 Firefox 检查通过，多窗口标签刷新、重复名称反馈已发行；dufs-plus 列表定位修复独立部署 NUC。
- [x] 完整 liu-bigpc toplevel 与 Home Manager generation 构建通过；系统浏览器命令解析到新包。只更新 tag-browser-src 输入，保留既有 antigravity-nix、chatgpt-deb、codex-cli-nix 锁定和 AGENTS/home.nix 改动；不执行 switch。
- [ ] 用户在普通终端激活后关闭旧浏览器，确认 nix.30，验收两窗口标签可见与实际 PDF 定位。产品验收权威源仍为 tag-browser 010、dufs-plus 001；本仓只管理安装。

## YouTube 视频下载工具

- [x] 声明式添加 yt-dlp，核对锁定包默认包含 FFmpeg、Deno 与 yt-dlp-ejs，补充使用说明及 README 入口。
- [x] 构建 liu-bigpc 完整 toplevel 和 Home Manager generation，验证安装命令及依赖。
- [x] 同步规格与文档镜像，独立提交推送本次变更。
- [ ] 用户在普通终端执行系统切换，并以实际 YouTube 视频验收下载。

视频下载工具验证：完整系统 `/nix/store/8js00nzbxdj4hdkk8cy7hs3d3f19l2qy-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 与 Home Manager `/nix/store/ga0drr27wpxgk8pm2carlpn0ihx9462f-home-manager-generation` 构建通过；安装入口的 yt-dlp 版本为 2026.08.19，运行依赖与激活单元核对。构建包含既有工作树配置；本次只提交 yt-dlp 相关变更，未执行 switch 或真实视频下载。

## 本地字幕 OCR 批处理

- [x] 实现固定依赖的独立运行环境、字幕区域探测/手动覆盖、SRT和待检查报告。
- [x] 实现分块续跑、既有输出保护、目录监测和磁盘空间门槛。
- [x] 验证真实视频、顶部字幕、无字幕、续跑与外部编辑保护，启动当前B站目录处理。
- [x] 同步规格与说明，独立提交并推送脚本。

自动字幕未经过全量人工校对；其待检查条目以视频旁的ocr.json为准。

验证：独立Nix运行环境构建及正式入口通过；5项回归检查通过。两段真实视频、顶部字幕片段与无字幕片段完成；顶部自动区域正确，重复4文件全部跳过，外部编辑即使指定replace-owned仍保留，发布中断和检查点恢复结果一致。B站下载改为每5页穿插下载；OCR监测服务已启动。全量OCR与人工校对尚未完成，不能按本验证宣称所有视频适配。

## 视频菜谱工具当前状态

截至2026-10-06；后续顺序见[方案](plan.md#下一步可续跑控制器)。勾选表示对应交付完成，不代表后台AI或人工校对已完成。

### 已完成

- [x] v1菜谱与食材契约、内部/阶段Schema、整理/独立审阅/选图/修复提示词及真实局部示例。
- [x] 固定菜谱库构建、跨记录验收、HTML/Recipe JSON导出、离线目录及食材搜索工具。
- [x] 十份全片OCR试稿：54个步骤、53张实际操作图；来源证据、处理记录、候选与缺图说明保存在Downloads。
- [x] 汇总全部76个食材名称并完成两轮清单审阅与纠错；当前词典v3含60个食材身份、3个上位类，70个名称映射，6个保留歧义。词典与实际目录内嵌索引一致。
- [x] 14项Python结构/输出保护回归及Node检索断言通过；实际10页面、53图片、目录往返、导出一致性及390px宽度通过。
- [x] 真实目录搜索验证：豆腐2道、蘑菇3道、香菇1道、多词AND/可选排除/空结果/清空/分页可用。模拟4200项丰富索引约9.5MB，当前PC Chrome筛选中位1.8ms/P95 2.4ms；仅为模拟规模与本机结果。
- [x] 用户确认十道菜试验效果可用；记录为浏览/试验反馈，未据此提升逐事实审阅或人工校对状态。

交付入口：Downloads/Bilibili/老东北美食 [514273130]/菜谱库试验-10道/index.html。原媒体保留，私有审阅及截图不进入资料镜像。每步3张代表帧加一次定点补帧；全部展示图已查看，未选候选未全量精细核验。鹿茸菇炒香一步因蒸汽遮挡留空。独立语义审阅仍pending，十份试稿均needs_review、human_reviewed=false。

### P0：稳定批处理入口与恢复

- [x] 固化来源/全片字幕准备、候选抽帧及阶段任务包生成，摆脱/tmp试验专用脚本。
- [x] 实现持久任务状态、去重、阶段输入/输出与配置摘要、状态查询/日志、任务包导出/结果导入。
- [x] 验证中断续跑、完成阶段复用、配置变更重算、坏结果隔离和原媒体/已有输出保护。

P0验收：11项新增批处理测试、相关共25项Python回归及3项Node检索测试通过；正式Nix入口通过。十道菜1814条全片字幕登记/种子校验，10个当前独立审阅包及1个真实新视频整理包导出通过，重复运行复用全部成功阶段；视频/字幕/原菜谱库摘要与元数据未变。全部十任务为waiting_review，未导入新的模型结论；报告留Downloads/菜谱工具数据/批处理-10道-P0/P0-validation-final.json，不进入资料镜像。抽帧为每窗口代表策略，按步骤检查点恢复。

### P1：模型接入与十道菜质量复核

- [x] 提供Responses独立适配器、四阶段模型配置、上传范围开关及默认零预算配置样例。
- [ ] 配置真实模型服务、凭证、上传范围与费用上限。
- [x] 实现超时/拒绝/限额暂停、usage费用估算与持久预留、响应恢复、最多两次修复；本地模拟请求测试通过。
- [ ] 配置后验证真实服务与聊天关闭后的独立执行。
- [x] 补齐食材用量独立审阅与视觉observations的证据转换/白名单修复再审阅；保留未知和源冲突。
- [x] 用用户授权的会话子代理独立复核十道菜逐事实证据、食材/用量/数字、步骤完整性和实际选图；修复后复审，未知和结构化覆盖缺口保留。

P1程序验收：相关39项Python回归与Node食材检索断言通过。模拟服务覆盖真实图片请求、零上传/零预算拦截、限流与坏结果限次、超时未知不重复、不可变响应恢复、凭证不落盘和旧请求费率保留；合成资料验证食材全覆盖、修复再审阅及视觉观察帧证据。真实十道菜1814条字幕、157项食材记录的完整审阅任务与模型预览已准备，310个源文件摘要/元数据未变；外部请求0。该准备阶段报告留Downloads/菜谱工具数据/批处理-10道-P1/P1-readiness.json；后续会话子代理验收见下。

P1真实子代理验收：十道1814cue、166事实、157食材、54步；162张新候选实际逐张查看，48步选图、6步缺图。31份独立审阅响应、18份修复响应共73处字段修复与54份选图响应经控制器导入，10任务complete，新库10道均needs_review、55个开放疑点及human_reviewed=false。80食材名称全清单复核，词典revision4（65项，73名映射、6歧义、1组合待映射）；豆腐命中2道、蘑菇3道、香菇1道。修复种子历史input冲突、重复同内容frame组装、非结构化数量原句丢失；精确源码摘要限定仅组装修复复用非assemble缓存。43项Python回归与Node食材检索测试通过。310个原文件元数据、注册媒体与种子摘要未变；外部模型API请求0，不推断会话成本。新库为Downloads/Bilibili/老东北美食 [514273130]/菜谱库试验-10道-子代理复核/index.html；私有结果与报告留P1/子代理复核报告.json，不进入Git/NUC。长期无人值守依旧待配置外部或本地模型。

### P2：小批验证后扩容

- [x] 实现受审阅的完整结构修订准备入口，保留旧来源/ID/证据/问题，变更项强制待审；窄图窗重新取候选并经独立复核，在既有十道完成revision2归档/发布与无视频重建。
- [ ] 继续补齐剩余变式食材索引、复合数量表达与来源歧义；建立绑定原片/字幕/片段的OCR疑点复核回执，不能直接清除原OCR标记来通过删除门槛。
- [ ] 随后处理30–50个视频，验收质量、恢复、耗时/开销及缺图率；每批复核全库食材清单并同步词典与目录。
- [ ] 根据小批结果明确全库运行门槛与资源配置，再安排4000多条处理。

质量补齐验收：既有十道1814cue，修订后275事实、189食材、54步；648张新候选实际逐张查看，53步选图、糯米排骨土豆切配/铺盘1步仍缺图。25份独立全文审阅、6份修复与54份选图响应按原契约接受，全部revision2发布；8道needs_review、2道ready，19项开放来源/结构疑点。10份原OCR报告仍待复核，全部视频保留；310个原文件元数据与10份媒体摘要未变，无视频控制器重建及发布物/索引校验通过。修订入口新待审问题使用版本ID，防止重开并覆盖历史已解决问题；85项Python回归与Node检索测试通过。全部113食材名称/189次出现复核并同步权威词典revision5：83项，新增18项和34别名，103名映射、9歧义、1组合保持未映射；实际目录豆腐2道/蘑菇3道/香菇1道，江米、荷叶、虾皮、白胡椒粉各1道，可选项过滤通过。原下载不续跑，外部模型API调用0；私有报告和食材审阅包仅Downloads/菜谱工具数据/质量补齐-10道。

人工烹饪校对属于可选的独立验收，不由AI审阅或用户接受页面效果自动完成。


## Tag Browser nix.31 安装输入

- [x] 输入改用自有 product-stable，固定 `88c3cab2d49322d0c2e198f57f7250d8ee1cf040`；旧 stable 不再承载现行产品开发。私有 Release/本机/Cachix 输出 `/nix/store/6xc0mnfz4piy09gffzl0grvycw3lbysa-tag-browser-0.1.0` 一致，归档 SHA256、缓存命中、预取及签名核验通过，CI 37457364836 成功。
- [x] 完整系统 `/nix/store/92cw19q6frsal7gw5brgfhm8mhjp6ga5-nixos-system-liu-bigpc-26.11.20260922.b6c98e9` 与 Home Manager `/nix/store/ga0drr27wpxgk8pm2carlpn0ihx9462f-home-manager-generation` 构建通过；系统浏览器命令指向 nix.31，hm-backup 设置保持。只提交浏览器输入及本条安装状态，保留其他锁节点和 AGENTS/home.nix 改动。
- [ ] 用户普通终端执行 `nu rerun.nu liou --host liu-bigpc`，正常关闭旧窗口后确认 nix.31；不由 Agent 执行 switch。真实 PDF 观察按 tag-all 019 P01–P03，产品实现已完成五条固定关卡，不扩大安装验收范围。

### 串行生命周期与视频释放

- [x] 实现大清单持久登记、串行下载/OCR/AI任务交换、保留视频数与磁盘空间门槛。
- [x] 实现逐视频不可变接受归档与固定页面发布、目录索引、删除后独立重建。
- [x] 实现显式删除预演与执行、缺图/开放疑点阻止释放、准确文件身份及隔离删除。
- [x] 验证发布/删除各中断点续跑、源和页面被修改拒绝、符号链接/越界拒绝、完成不重复AI。
- [x] 用真实十道已复核结果验证流程迁入与保留、不删除原视频；全清单登记与合成测试分别验收。

生命周期验收：相关80项Python回归（含37项flow）及Node食材检索测试通过；正式Nix入口help、只读status及完成目录run --watch通过。合成4200条清单登记，单写者、失败容量、双磁盘空间、低频下载参数与已完成下载复用、OCR来源门槛、发布/隔离/unlink中断恢复、误删保护、版本复审、词典更新及任务交换闭环均验收；AI合法回复归档失败保持accepted并可重试，重复递送不重复推进。新下载使用模拟，不据此宣称线上全量可下。真实十道结果归档/发布与无视频控制器重建通过，310个原文件未变，实际视频删除0；十道均needs_review，仍保留原视频。私有报告位于Downloads/菜谱工具数据/串行流程-10道验证，不进入Git/NUC。外部模型调用0；30–50道与4000多条执行尚未完成。

### 单视频紧凑会话与实测

- [x] 实现只带当前阶段必要材料的摘要绑定视图与只读语义预检，保持原契约/全文复审与选图质量门槛。
- [x] 实现真实请求usage逐响应去重与阶段登记，区分缓存输入/非缓存输入/输出和缺记录，回归验证继承记录/冲突计数保护。
- [x] 对一个已有视频重新执行全片本地OCR→全新整理→独立复审/修复→实际选图→图后独立复审→食材清单复核→归档/HTML/JSON/搜索目录，报告真实菜谱阶段用量和开发调度范围。

单视频实测完成至发布与食材复核：6分04秒、153cue、14步/14图，实际查看168候选；全文图后复审覆盖50事实、22食材及26疑点，保留8开放项和OCR pending，status=needs_review，不释放视频。18个全新阶段执行者137次实际请求（含整理重试），输入4,863,774，其中缓存4,430,208、非缓存433,566；输出45,650；总4,909,424。根代理开发/测试/调度截至快照另12,905,697，不能当单视频固定成本。食材词典升为6（2新增、10别名、1歧义），旧ID/别名/歧义保留；全清单覆盖22/22。96项Python回归、词典更新后8项专项、Node检索及8个真实搜索查询通过；原310文件身份未变、归档校验及不调用视频/队列的重建索引相同。后台OCR与初试副本写入冲突触发身份保护，保留审计并换隔离media-root全片重做；只在新任务摘要完全一致时复用本次刚生成的整理回复，未采用既有十道菜谱或旧AI结果。私有任务/图片/用量报告保留Downloads。此样本仍需来源核验，不代表所有菜谱能自动达到ready，也未执行4000条。

### 步骤视频替代视觉选图

- [x] 实现clips配置、独立窗口裁剪、严格片段来源/文件/格式验证及文字复审后直接组装，无视觉AI阶段。
- [x] 实现左文右视频、多帧手动选图、视频/图片/两者显示及本机JSON/JPEG持久保存与导入导出。
- [x] 接入归档/发布/无视频重建及clips释放媒体条件，保持旧图片模式、OCR/事实门槛与不可变归档。
- [x] 完成队列恢复/媒体篡改/选图安全与真实视频演示验收，更新手册并提交推送、镜像规范。

新流程已用同一真实视频演示：完整步骤字幕范围扩展/合并后14个MP4共73,136,953字节，独立片段和原始时间可在右侧播放，无select_images/review_visual任务。复用旧已独立核验的同源文字结果并保存摘要审计，不冒称新模型执行；OCR及文字疑点仍保留，实际删除0，原310文件身份未变。归档、发布及无视频重建通过。100项全套回归通过，随后5项片段专项覆盖完整字幕窗、多窗/恢复、手选保存与同源HTTP保护、无图片ready释放预演/媒体篡改拒绝、修订片段再生成；最终生命周期专项另行复核。隔离Zen配置下实测多张已选图显示及原始时间标签，未读取既有浏览器Cookie。演示、片段、选图与原始报告仅Downloads或临时测试目录；公开仓库仅工具、合成测试和规格。

### 仅使用平台中文 AI 字幕

- [x] 新建 CLI 流程默认 AI-only，先获取字幕再下载视频，不 OCR；保存正负准入回执。
- [x] 缺字幕 skipped 不占容量/不阻断续跑；网络、风控、登录及损坏字幕可 retry，已有文件不因跳过删除。
- [x] 禁止旧字幕/seed/adopt 绕过、绑定 AI 字幕来源、保留文字/片段及删除门槛；新增无 OCR 入口运行环境。
- [x] 完成合成全流程与低频真实视频验证，更新手册，提交推送并按白名单镜像核验。

AI-only 验收：最终117项菜谱Python回归通过，覆盖缺字幕跳过、failed/retry、正负检查点续跑、只获取中文正文、登录/风控/空字幕拒绝、来源回执篡改及完整clips归档/释放预演/无视频重建。正式无OCR入口help和实际处理通过，运行闭包无OCR推理包/启动器。低频真实探测3条已有视频，获取121/131/254条平台ai-zh字幕；中文筛选插件在BV17wYF6mE22实测仅有ai-zh轨道。没有遇到真实缺字幕项，跳过分支用合成数据验证，不据此推断全库字幕覆盖率。

基于121条新平台字幕重新执行整理及独立文字复审（不复用旧OCR菜谱），产出14步、23食材、15个MP4共80,223,948字节，生成HTML/JSON/目录；4个食材搜索、归档与不读取原视频的重建/索引一致通过。保留15开放问题，status=needs_review、human_reviewed=false，OCR与视觉AI调用均0；原417个媒体/字幕文件身份未变，实际删除0。真实毫秒字幕揭示旧SRT解析浮点相加不一致，统一整数秒+毫秒算法并新增真实时间修改仍拒绝的回归，复用已完成文字/片段续跑，不绕过来源核验。试验仅处理一份菜谱，另外两条只保存字幕检查点；未运行4000条。私有媒体/字幕/任务/报告只在Downloads新ROOT；公开Git及NUC镜像仅工具/合成测试/规格手册。

### 精简菜谱与原视频键盘浏览（阶段 S）

- [x] S1：实现只取 AI 字幕和封面、单次文本提取、进度续跑，不下载视频或调用 OCR/切片/复审。
- [x] S2：生成材料/步骤/原封面 HTML/JSON、食材目录和原视频时间链接，产出真实样稿。
- [x] S3：实现按住播放松开停、可调速、真实邻帧键盘浏览及暂停截图原网页脚本，明确 API/截图限制。
- [x] S4：完成合成/真实字幕与封面、隔离 Zen 媒体功能验证及规范收尾、提交推送与白名单镜像。

阶段只按 S1–S4 固定验收项计数；不把用户安装脚本/真实 B 站页面确认冒称程序验收，也不自动扩大至全库或浏览器配置写入。

S1/S2/S4 程序与收尾验收：9 项新增 Python 用例、3 项 Node 食材检索通过；合成清单 4200 条登记，字幕缺失/错误重试/输入与结果篡改/断点重建覆盖。真实样稿复用已验证的 121 条平台 AI 字幕，取得原封面，单次新文本整理生成 19 材料/12 步骤；4 个食材查询与可选食材排除通过，HTML/JSON/目录 HTTP 200，私有元数据路径 404。新 ROOT 文件约 1.97 MB，无视频/OCR/片段/视觉 AI/独立复审，原 417 媒体与字幕文件身份未变。公开 Git 与 NUC 白名单只包含工具、合成测试、规格和手册，真实字幕/封面/AI回复留 Downloads；当前预览 8765 由本任务旧预览切换而来。

阶段 S 验收已完成：0.2.0 用 document-start/page 捕获主页面分片 MP4 帧时间表，实际邻帧键盘浏览、按住/松开、倍速、暂停截图已实现；无额外媒体请求。9 项 Node 帧索引回归覆盖可变样本时长、B 帧重排、默认时长、编辑/时间偏移、64位时间、缺失与乱序/重传分片、任意分块、初始化切换及损坏输入。隔离 Zen 的恒定帧率、timestampOffset、变帧率、带符号 B 帧偏移 4 类素材，共60次显示画面对照独立ffmpeg解码帧全部通过，含2×按住播放后暂停再前后单帧的衔接。比对由本地代码完成，不调用视觉AI。初版探测发现 seekToNextFrame 缺失，且暂停跳转回调时间不是真实源帧 PTS；自然暂停画面还可能与 currentTime 差一帧，已通过立即暂停后稳定到已知真实帧解决，不能仅依据播放时间改变验证逐帧。

默认暂停、按住/松键/失焦暂停、0.25×慢放、输入不抢键、无索引拒绝伪逐帧、关闭模式恢复平台、PNG实际保存及真实跨域截图失败提示回归通过。不支持 Worker/非MP4/sequence/裁剪/复杂编辑表时明确拒绝，缺帧或未缓冲不跳秒猜测。脚本更新到本任务已有8765只读预览，安装或更新后须刷新B站页，以page上下文足够早运行。真实B站+用户脚本管理器组合尚待用户试用，与合成媒体程序验收分开；未擅写真实浏览器配置、下载原站视频或执行四千条处理。只提交本任务工具/测试/规格/手册并推送，NUC白名单预演/摘要同步；保留原有五项未提交配置改动。阶段 S 剩余0项，下一步由用户安装新版并在原视频页试用，站点兼容问题按实际反馈修复。


### 精简十道试验（阶段 T）

- [x] T1：按用户明确删除授权核对本次 B 站原视频及试验输入副本，记录逐文件删除审计，保留字幕/清单/既有菜谱并确认下载停止。
- [x] T2：只获取平台中文 AI 字幕和原封面，完整字幕单次提取材料、用量及制作过程，产出十份新精简菜谱，不用 OCR/视频下载/切片/视觉 AI/独立复审。
- [x] T3：核验十道材料索引、时间引用、断点重建及本地页面，更新规格并提交推送、按白名单镜像。

阶段仅按 T1–T3 三项固定验收计数；用户本轮明确要求删除已有下载视频，此授权替代此前样稿的原视频保留要求，只删除核对过的本次账号原视频及四份原视频输入副本。派生步骤片段及历史菜谱保留，FreeCAD 等其他下载不在范围。实际逐文件清单、字幕、封面和 AI 结果留在 Downloads，公开仓库只记录流程与验收摘要。


T1–T3 实际验收：精确删除209个账号原视频及4份试验输入副本，文件合计21,139,164,975字节，私有逐文件身份与完成审计已保存；208份既有字幕身份未变，57个FreeCAD课程视频保留，派生片段/旧菜谱不删除。宿主无本次下载/OCR活动任务。新独立ROOT登记十条，复用3份有效平台AI字幕缓存、低频新取7份，十条均有字幕（此次真实跳过0，不推断全库覆盖率）。逐条完整读取共1481条字幕后新整理178项材料和86步，JSON/HTML/原封面/食材目录发布10份，ai_draft=true，未调用独立复审或视觉AI。

所有字幕/封面/AI包摘要、真实cue引用、步骤时间顺序与时长范围、发布JSON、封面解码、断点无网络重建及页面摘要一致通过；本地目录和全部菜谱/封面HTTP200，私有配置/数据库/平台元数据路径404。Node食材检索与隔离Zen实际输入搜索（等待页面120ms防抖）、别名、可选筛选、空结果及10张封面加载通过。新ROOT约18.9MB，原视频/OCR/切片为0；字幕不清、用量未知与替代方案保留说明，不假称已人工认证或视觉复核。预览切换到本任务已有8765，不启动四千条处理。

本轮仅提交010规格、精简手册及AGENTS本次清理记录，AGENTS使用独立差异暂存，其他任务原有五份未提交配置/手册改动保留；公开Git/NUC只同步规范和验收摘要，私有原字幕、封面、AI回复、删除清单与浏览器报告留Downloads。阶段T剩余0项，下一步交用户查看十道样稿效果。


### 全量精简菜谱（阶段 U）

- [x] U1：核对完整投稿快照，继承十道完成结果，登记全量去重队列，实现并启动低频有界采集与断点续跑。
- [ ] U2：按已登记清单逐批完成单次AI材料/步骤提取和页面发布；无中文AI字幕跳过，失败单独记账，不用视频/OCR/切片/独立复审。
- [ ] U3：全量结束后核对完成/跳过/失败及清单覆盖、材料检索、页面与输入绑定、重建和报告。

阶段以 U1–U3 三项固定验收计数。采用已完成动态分页快照去重4159条，不冒称当前实时投稿数；前十道完整继承，新ROOT只存字幕、封面、AI任务/结果和页面。后台只采集字幕/封面，每条平台请求间隔15秒，视频间隔至少60秒；待AI输入最多10条，达到上限等待，首个错误标failed并停止，缺字幕独立skipped。AI输出由当前会话逐批产生，不据采集器运行冒称四千道自动整理完成。公开Git/NUC不保存清单正文、字幕、封面或AI回复。


U1启动验收：既有快照complete=true、364页、4159个去重BV ID，记录来源摘要；SQLite备份继承十道登记与完整字幕/封面/AI结果，十份结果逐字节不变，输入包绑定均通过。新增有界collect通过12项精简Python回归，覆盖实际来源准入、待AI上限、排除等待/已完成项、重开检查点、缺字幕、错误停止、普通写锁等待、watch上限等待及停止标记；平台内部15秒间隔、全量额外60秒间隔，默认max_pending=10。宿主后台有界采集已启动，已新取首条218条平台字幕并单次整理发布第十一份，全量库11份页面/封面/JSON/来源摘要验证通过，新增视频文件0。本任务8765已切到全量ROOT，十道样稿目录保留。

当前11/4159份已发布，其他4148条仍需采集或AI整理，不宣称全量完成或模型无人值守；失败/无字幕将分别记账，AI阶段仍依赖活动会话。U1完成，阶段U剩余2项：U2全量逐批整理、U3全量最终核验。实际清单/来源报告/字幕/AI输出及PID/采集日志留Downloads；公开提交仅工具、合成回归及规格手册，其他任务五份未提交改动保留。
