# Todo（nix-tools）

## 💤 电源与合盖策略

- [x] suspend-then-hibernate：合盖先挂起，1h 后自动休眠到磁盘
      （远程 homebox 使用 16 GiB swapfile；需保持 swap ≥ 内存）
- [x] 挂起时 DPMS off（swayidle before-sleep 配合 wlopm，恢复后重新打开）
- [x] 合盖行为集中可选：修改 `nixos/configuration.nix` 的 `lidSwitchAction`
      （支持 lock / suspend / hibernate / suspend-then-hibernate；外接显示器默认 ignore）

## 🌐 外网远程操作 nuc（dsh web 方案）

现状：外网 SSH 到 nuc 走 autossh 反向隧道 + aliyun 跳板（`ssh nuc-remote`），
交互式打字有 ~60ms RTT 卡顿（homebox → aliyun 31ms × 2 回程）。

备选方案：**在 nuc 上跑 dsh web，用外部域名 + Authelia 保护**，外面直接用
浏览器访问（HTTP 走 EdgeOne CDN，比 SSH 隧道流畅）。

- [ ] 验证 EdgeOne 对 dsh WebSocket 长连接的兼容性（dsh 会话/终端/AI 流式都用
      WS；现有 ttyd 也是 WS 但需实测 dsh 的 WS 模式能否过 CDN）
- [ ] nuc 上装 dsh（home-manager 声明式 + dsh-web systemd service，监听 127.0.0.1:3080）
- [ ] EdgeOne 加子域名（如 dsh.wttliou.top）
- [ ] Caddy 配置：dsh 域名 → Authelia 认证 → 127.0.0.1:3080（复用现有 DUFS 架构）
- [ ] Authelia 添加 dsh 的访问规则（建议 2FA）
- [ ] 安全评估：dsh 是完整编程环境（可执行命令/读写文件），公网暴露需谨慎
- [ ] 性能验证：AI 流式输出经 CDN 的延迟（依赖 nuc 上行带宽）

先体验 SSH 隧道卡顿程度再决定是否推进。

## 其他候选

- [x] mihomo 分流规则细化（GeoSite/GeoIP 国内直连 + 国外代理）
- [x] Rime 词库同步（加密快照 + `scripts/sync-rime-userdb.sh` 远程恢复）
- [x] waybar 更多模块（温度、hwmon 风扇转速、MPRIS 媒体控制）
