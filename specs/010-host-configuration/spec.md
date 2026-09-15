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
