# 数位笔侧键滚动（pen-scroll）

Wacom One (CTL-472) 的笔没有滚轮/触摸环，Linux Wayland 也没有 Windows Ink
那种"笔尖拖动 = 平移页面"的系统约定。要让"按住笔杆侧键 + 上下划动"产生滚轮
效果，需要一层软件翻译。本文记录原因、实现与验收方式。

## 为什么配置层面做不到

- **niri**：`input { tablet { } }` 只有 `map-to-output` / `map-to-focused-output` /
  `calibration-matrix` 等，没有手势或滚轮选项。niri 本身**支持**数位板滚轮轴
  （源码 `AxisFrame { wheel }` → smithay `wp_tool.wheel(degrees, clicks)`），
  但只会转发设备真实上报的滚轮。
- **libinput**：只有当 libwacom 认为该**笔工具**带滚轮时，才会为该工具产生滚轮轴
  （`libwacom_stylus_has_wheel`）。CTL-472 的笔不属于这类工具。
- **Chromium / Electron**：`WaylandTabletTool::Wheel()` 注释明确写着
  `Not implemented, wheel on tablet tool is rare.`，即浏览器内核不处理数位板滚轮。
  Firefox/GTK 会把它转成滚动事件。
- **Windows**：不是驱动魔法。Windows 10 起系统把"笔尖拖动"在支持手势的应用里
  翻译成滚动/平移，绘画软件自行声明要笔迹，按住侧键恢复选中。这是应用层约定，
  与 Linux 的差别就在这里。

结论：**只能增加一个 evdev → uinput 的守护进程**，把侧键+划动翻译成滚轮。

## 实现

- `scripts/pen-scroll.py`：守护进程。
  - 独占抓取（`EVIOCGRAB`）真实笔设备，再用 uinput 镜像出一个虚拟笔。
  - 虚拟笔在克隆真实能力之外**额外声明 `REL_WHEEL` / `REL_HWHEEL`**，这样
    niri 才把滚轮转发给笔尖所在表面——滚动不需要移动鼠标指针，也不会打到别处。
  - 普通书写/悬停/笔尖点击原样透传；只有在"按住侧键后越过死区拖动"时才拦截。
  - 拦截期间吞掉压力与 `BTN_TOUCH`，避免同一次拖动又去选中文本或画线。
  - 侧键快速点一下（未越死区）会补发为真正的侧键点击，右键菜单不受影响。
  - 已经在画的过程中才按下侧键 → 全程透传，绝不打断笔迹。
  - 平板拔出后自动等待重连；`SIGTERM`/`SIGINT` 干净退出并 ungrab。
- 手势状态机 `PenScrollEngine` 不依赖 evdev，可脱离设备单元测试。
- 驱动它的 NixOS/HM 声明：
  - `nixos/hosts/liu-bigpc/default.nix`：`hardware.uinput.enable`，并把 `liou`
    加入 `uinput` 组（`/dev/uinput` 为 0660 root:uinput）。
  - `home-manager/nix_modules/pen-scroll.nix`：`systemd.user.services.pen-scroll`，
    仅 `liu-bigpc` 默认启用；源码经 `pkgs.writers.writePython3Bin` 打包并做 flake8 校验。

> **打包陷阱（2026-09-16 实测）**：必须用 `writePython3Bin`，不能用 `writePython3`。
> 后者产出的是**单个可执行文件**，放进 `home.packages` 会在构建 home-manager
> path 时失败：
>
> ```
> pkgs.buildEnv error: The store path ...-pen-scroll is a file and can't be
> merged into an environment using pkgs.buildEnv!
> ```
>
> `writePython3Bin` 产出带 `$out/bin/` 的目录，可正常安装。两者都做 flake8 校验、
> 都带运行期 `libraries` 依赖，差别只在产物形状。
> 教训：只验证"能构建出单个包"不够，必须构建 `home-manager-path` / 完整
> `toplevel`，否则这类"包本身能构建、装不进环境"的错误会漏到用户 switch 才暴露。


## 可调项（`features.penScroll.*`）

| 选项 | 默认 | 说明 |
| --- | --- | --- |
| `enable` | 仅 liu-bigpc | 是否启用守护进程 |
| `pixelsPerTick` | `null` | 每个滚轮刻度对应的坐标单位；null 时按 ABS_X resolution 推算（推荐） |
| `deadzonePixels` | `null` | 划动/点击判定的死区；null 时按分辨率换算为 1.5mm（推荐） |
| `natural` | `true` | 向下拖动 = 内容向下（自然滚动） |
| `horizontal` | `false` | 改为 `REL_HWHEEL` 横向滚动 |
| `barrelButton` | `lower` | `lower` = 下方侧键(BTN_STYLUS)，`upper` = 上方侧键(BTN_STYLUS2) |

**滚动速度**：默认每 **4mm** 笔尖行程 = 一个滚轮刻度（由 ABS_X resolution 自动换算，
CTL-472 上是 400 单位）。本机有效区约 95mm，故一次全幅划动约 24 个刻度、
约 70 行文本，滚一屏约需 53mm。此值 2026-09-17 按用户反馈从 6mm 调快（+50%）；
若仍不合适，用 `pixelsPerTick`（如 `300`）或 `PEN_SCROLL_UNITS_PER_TICK` 覆盖。

**平滑滚动（2026-09-17 重构）**：滚轮改走**指针通道的高分辨率滚轮**
（`REL_WHEEL_HI_RES`，v120 单位，120 = 一格），因此可以按笔的位移连续滚动，
而不是一格一格跳。

为什么必须换通道：**数位板通道的滚轮轴是整数**（libinput 只处理 `REL_WHEEL`，
`tablet_process_relative` 明确忽略 `REL_WHEEL_HI_RES`），所以再怎么调都只能整格跳。

三个实测确认的关键点：

1. **libinput 保留细粒度**：注入 `v120=6` 时观测到
   `POINTER_SCROLL_WHEEL vert -0.75/-6.0*`——连续值，未被取整。
2. **应用真的收得到**：GTK4 探针窗口收到 `dy=-0.0250`（= 3/120），
   即 1/40 格的连续量，证明细粒度贯通到客户端。
3. **libinput 有累加阈值**（`ACC_V120_THRESHOLD = 60`）：从静止开始的小步会被
   *丢弃*，累计到 60 才进入转发状态。因此手势**起手先发一整格（120）做"预热"**，
   之后每一步都实时转发。空闲超过 `WHEEL_SCROLL_TIMEOUT`（500ms）会退回，
   下一次划动重新预热——正常连续划动不会碰到。

**为什么要问 niri 要几何**：虚拟数位板能自动跟随焦点输出
（`input.tablet.map-to-focused-output`），但**虚拟指针不能**——niri 的 libinput
设备永远不报告所属输出，绝对指针会被拉伸映射到**所有输出的并集包围盒**。
双屏下这会让滚动落到错误的屏幕。所以守护进程通过 **niri IPC** 查询焦点输出，
把笔坐标映射到该输出后再反解成指针的绝对坐标。IPC 不可用时自动回退到数位板整格通道
（即旧行为），不会比之前更差。

**坐标映射必须逐行复刻 niri（2026-09-17 修正）**：第一版用"保持比例 + 留黑边
（letterbox）"映射，而 **niri 用的是"保持比例 + 裁剪填满（cover）"**，两者在非中心
位置最多相差约 107 逻辑像素——用户看到的现象是"划动时鼠标指针跑到别的地方"。
现已按 niri 的 `compute_tablet_position` 逐步复刻（含 transform 与
`ratio = tablet_aspect / output_aspect` 的裁剪分支），并用 `niri-ipc` 的双屏实测
几何做对照：**最大偏差 0.000000 px**（Dell 1706×960@1.5x Normal 与 Philips
1080×1920@1.0x 旋转 90° 均通过）。

**起手响应（2026-09-17 修正）**：**越过死区即刻发出第一个滚轮刻度**，不再等攒满一整格。
滚轮事件是离散的，之前必须先划满 4mm 才出现第一次滚动（用户反馈"要划相当长度才开始"）。
按 libinput 对同类手势的描述（"threshold must be met to engage, but once engaged any
movement scrolls"），现在起始延迟 ≈ 死区（1.5mm），**后续滚动速率不变**
（改动前后同样划 45mm 都是 12 格）。

**死区**：默认 **1.5mm**（由分辨率换算，不再是抽象单位数），只用于吸收点击时的手部抖动。
它比一个滚轮刻度小一个数量级，**不是**起手延迟的主因。可用 `deadzonePixels` 覆盖。

也可用同名环境变量直接运行脚本调试：`PEN_SCROLL_UNITS_PER_TICK`、
`PEN_SCROLL_DEADZONE_PIXELS`、`PEN_SCROLL_NATURAL`、`PEN_SCROLL_HORIZONTAL`、
`PEN_SCROLL_BARREL`。

## 验收

本机用户执行（Agent 不代为 switch）：

```bash
nu rerun.nu liou --host liu-bigpc
```

系统服务由 PID 1 启动并自带 input/uinput 组，**无需注销、无需重启**，直接：

```bash
systemctl status pen-scroll                   # 应为 active (running)
journalctl -u pen-scroll -n 20                # 应打印 "grabbing /dev/input/eventN"
```

若之前装过 home-manager 用户服务，先清掉它的残留失败状态：

```bash
systemctl --user reset-failed pen-scroll 2>/dev/null || true
```

**手势语义（2026-09-17 修正）**：必须是**笔尖接触板面**时划动才滚动。
侧键按住后笔**悬空**移动只移动光标、不滚动；死区从**笔尖落点**起算，
所以"先悬空移到别处再落笔"不会立刻触发滚动。
（初期版本只判断"越过死区"，导致悬空划动也滚动 —— 已修。）

**笔尖离板即结束手势（2026-09-17 修正）**：一次划动结束后抬笔即停止滚动，
不会因为侧键还按着而把手臂回带的动作当成反向划动。
这与 libinput 的 on-button scrolling 一致（松开指定按钮即 `stop_scroll`）。
抬笔后回到"已武装"状态，因此**按住侧键不放可以连续划多次**；
已经滚动过的一次按压在松开侧键时**不会**再补发点击，纯点击行为不受影响。

手工验收：

1. 浏览器里按住笔杆侧键、**笔尖接触板面**垂直划动 → 页面滚动，且**不**选中文本。
1b. 按住侧键但笔**悬空**划动 → 只移动光标，**不**滚动。
1c. 一次划动后**抬笔** → 立即停止滚动，不出现反向回滚；按住侧键可继续下一次划动。
1d. 起手响应：越过约 1.5mm 死区就**立刻**开始滚动，无需先划满一整格。
2. 侧键快速点一下 → 正常侧键点击（右键菜单）。
3. 正常书写、悬停、笔尖点击、按住笔尖拖动选中 → 与改动前一致。
4. 绘画软件里正常画线不受影响。

## 待现场验收项

配置求值、打包（含 `toplevel` 与 `home-manager-path`）与单元测试已在 PC 通过；
**实际 switch、组生效与桌面手势尚未由用户验收**，不得据此宣称功能已完成。

2026-09-17 第三次（结论）：先试 SupplementaryGroups → 216/GROUP；再试 udev uaccess
→ 规则落在 99-local.rules 太晚不生效；最后定位到 **linger 使"重新登录"也无效**。
最终改为 **systemd 系统服务**（toplevel 构建通过，生成的 unit 含
`SupplementaryGroups=input/uinput`、`User=liou`、`WantedBy=multi-user.target`）。

2026-09-17 第三次：服务已装上并启动，但启动即退出，日志为

```
evdev.uinput.UInputError: "/dev/uinput" cannot be opened for writing
```

两个独立问题：

1. **权限**：`/dev/uinput` 是 `0660 root:uinput`，进程必须带上 `uinput` 组。
   **决定性发现：本机启用了 linger**（`nixos/configuration.nix` 声明式创建
   `/var/lib/systemd/linger/liou`），因此 `user@1000.service` **不随注销停止**，
   会一直持有**首次启动时**的组快照 —— 所以"重新登录"根本没用来刷新它的组，
   home-manager 用户服务永远看不到 `uinput` 组（实测 `id` 里有 `input` 却没有
   `uinput`，而 `/dev/uinput` 权限本身正常）。

   两条"在用户服务里补组"的路都已被上游证实不可行：
   - `systemd.user.services.<x>.Service.SupplementaryGroups`：systemd --user 没有
     `CAP_SETGID`，`setgroups()` 失败，服务以 **216/GROUP** 直接退出
     （[systemd#15659](https://github.com/systemd/systemd/issues/15659)）。
   - udev `uaccess` tag：执行点是 `73-seat-late.rules`，规则必须早于它；而
     `services.udev.extraRules` 固定写进 **99-local.rules**，太晚
     （[nixpkgs#308681](https://github.com/NixOS/nixpkgs/issues/308681)）。

   **最终方案：改成 systemd 系统服务**（`nixos/modules/pen-scroll.nix`）。
   由 PID 1 启动，具备 `CAP_SETGID`，`SupplementaryGroups = [ "input" "uinput" ]`
   正常工作，且**完全不依赖登录会话与组快照** —— 一次 switch 立即生效，
   无需注销、无需重启。因此 home-manager 里那个用户服务已整体移除。

2. **代码缺陷**：`evdev.uinput.UInputError` 派生自 `Exception` 而**不是** `OSError`，
   原来的 `except OSError` 抓不到它，于是每次启动都抛裸 traceback 并被 systemd
   反复重启（实测 restart counter 到 70）。已改为 `retryable_errors()` 同时捕获
   两者，并在 `main()` 循环里先检查 `/dev/uinput` 可写性，给出可操作的提示而不是
   崩溃。另外把 `build_mirror()` 移到 `device.grab()` **之前**：虚拟设备建不起来时
   绝不先抓取真实笔，避免把用户的笔“卡死”。

**为什么不再用"加组 + 重新登录"**：linger 让 `user@1000.service` 跨注销存活，
其组快照不会刷新，该方案在本机永远不会生效。系统服务方案绕开了整个问题。

2026-09-16 第二次 switch：系统部分（toplevel）构建并激活成功，`uinput` 组
（`uinput:x:987:liou`）生效；但 home-manager 激活被 `~/.dsh/hooks/hooks.json` 与
`notify-stop.sh` 阻断（手写遗留文件非符号链接，HM 报 "would be clobbered"）。
该冲突与本功能无关（由 398ac6d 声明、文件更早手写于 10:13/10:23），但一次冲突
会阻断整个 HM 激活，连带 pen-scroll 用户服务装不上。已在 flake.nix 设
`home-manager.backupFileExtension = "hm-backup"`（非破坏性改名备份），求值确认
`home-manager-liou.service` 环境含 `HOME_MANAGER_BACKUP_EXT=hm-backup`。

2026-09-16 首次 switch 失败于 `home-manager-path`（`writePython3` 产物是文件，
见上文打包陷阱）；改用 `writePython3Bin` 后完整 `toplevel` 与
`home-manager-generation` 均构建通过，`home-path/bin/pen-scroll` 已正确链接，
用户服务单元指向该路径。仍待用户重新 switch 与实测。


