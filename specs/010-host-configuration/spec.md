# 主机声明式配置与诊断

## 需求与验收

- Home Manager standalone 不依赖 NixOS system profile；rerun 使用 flake 锁定 CLI，部署与自检使用同一显式目标；不因普通 switch 自动刷新依赖。
- 主机硬件与角色分别配置，合盖策略可选，外接显示器默认忽略；休眠 swap 容量需覆盖内存。
- Niri 外接竖屏按真实 EDID 规则恢复；Rime-Ice 固定词库，Lua/OpenCC/用户词典可用，逗号句号翻页且不重复启动输入法。
- Avahi 仅清理无效、失活或 PID 复用的旧 pid 文件，活跃 Avahi 进程持有文件不得删除。
- NUC 温度按 coretemp/Package id 0 定位并过滤无效值，不把无效 ACPI 温度显示为高温。
- 密钥库只同步加密 KDBX，明文导出到私有目录；不在 Nix 求值时读共享密钥、不让明文进入 store 或 Git。

## 边界

操作说明保留 README、nixos/reinstall-checklist.md 和 docs/secret-vault-cli.md；本轮不执行 switch、重启或恢复密钥。
