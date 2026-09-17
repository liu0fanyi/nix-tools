# 主机声明式配置与诊断

## 需求与验收

- Home Manager standalone 不依赖 NixOS system profile；rerun 使用 flake 锁定 CLI，部署与自检使用同一显式目标；不因普通 switch 自动刷新依赖。
- 主机硬件与角色分别配置，合盖策略可选，外接显示器默认忽略；休眠 swap 容量需覆盖内存。
- Niri 外接竖屏按真实 EDID 规则恢复；Rime-Ice 固定词库，Lua/OpenCC/用户词典可用，逗号句号翻页且不重复启动输入法。
- Avahi 仅清理无效、失活或 PID 复用的旧 pid 文件，活跃 Avahi 进程持有文件不得删除。
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
- **不破坏原有行为**：普通书写/悬停/笔尖拖动选中不受影响；侧键快速点按仍为正常侧键点击；
  已在书写过程中按下侧键则全程透传（不打断笔迹）；一次手势不会同时选中文本或画线。
- **实现约束**：独占抓取真实笔并镜像出**带 REL_WHEEL 的虚拟笔**，使 niri 将滚轮
  转发给笔尖所在窗口（不移动鼠标指针、不做坐标换算）；**必须先建虚拟设备再 grab**，
  构建失败时不得抓取用户设备。
- **权限约束**：守护进程必须是 **systemd 系统服务**并声明
  `SupplementaryGroups=[input,uinput]`。用户服务不可用——本机启用 linger 使
  `user@<uid>.service` 跨注销存活、长期持有陈旧组快照，且 systemd --user 无
  `CAP_SETGID`（报 216/GROUP）；udev `uaccess` 因 `extraRules` 落在 99-local.rules
  而晚于 `73-seat-late.rules` 亦不可行。详见 docs/pen-scroll.md。
- **范围**：仅 liu-bigpc 启用；不改变其他主机、不修改 niri 上游行为。
- **验收**：单元测试覆盖手势状态机（含"悬空不得滚动"回归）；配置求值与
  `toplevel` 构建通过；实机手势由用户验收，不以构建通过代替。

操作说明见 docs/pen-scroll.md，索引见 README。

