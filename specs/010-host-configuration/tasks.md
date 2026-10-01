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
