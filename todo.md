# Todo（nix-tools）

## 🔴 DeepSeek 峰谷检测（高峰时暂停工作）

**现状**：DeepSeek 无官方负载/峰谷接口（status.deepseek.com 不存在；api.deepseek.com 仅返回 401/403）。
**机制**：状态文件 `~/.dsh/peak-status`（内容 `peak` 或 `off-peak` + 时间戳）。
**约定**：AI 助手每轮开始检查该文件，若为 `peak` → 警告用户并暂停继续工作。

- [ ] 手动标记：`./scripts/check-deepseek-load.sh peak|off`（已实现）
- [ ] 自动检测：配置 DEEPSEEK_API_KEY 后，脚本自动测 `GET /models` 延迟，> 阈值（默认 5s）标记 peak
- [ ] 定时检测：NixOS systemd timer 或本机 cron 定期跑脚本更新状态
- [ ] 高峰通知：mako 桌面通知（配合 clashtui/mako 已有环境）

## 💤 电源与合盖策略（等 DeepSeek 低谷再弄，避免高峰排队）

- [ ] suspend-then-hibernate：合盖先挂起，超时（如 1h）后自动休眠到磁盘
      （需要 swap 文件/分区 ≥ 内存大小 + `systemd.sleep` 配置）
- [ ] 挂起时 DPMS off（显示器关闭省电，配合 swayidle before-sleep 钩子）
- [ ] 合盖行为策略可选：合盖=仅锁屏 / 合盖=挂起（现状）/ 合盖=休眠
      （`services.logind.lidSwitch` / `lidSwitchDocked`）

## 其他候选

- [ ] mihomo 分流规则细化（国内直连 + 国外代理，当前是全局代理）
- [ ] Rime 词库声明式同步（当前用户词库 userdb 是运行时数据，一次性 scp）
- [ ] waybar 更多模块（温度/风扇、mpris 媒体控制，参考 0xNiri 配置）
