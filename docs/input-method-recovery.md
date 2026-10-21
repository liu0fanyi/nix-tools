# XWayland 输入法候选窗恢复

2026-10-09 实机排查：Fcitx5 日志记录 X11 显示断线，微信仍能输入拼音，
但候选窗不出现。重新调用 `OpenX11Connection` 创建候选 UI 后仍无效；
DebugInfo 显示微信的 `fcitx4` 输入上下文没有显示分组。
重启 `fcitx5-daemon.service` 后上下文重新进入 X11 分组，用户确认微信候选词恢复，
微信未关闭。此结论对应本次故障，不代表其他应用偶发问题都已验收。

`home-manager/nix_modules/fcitx5.nix` 为 liu-bigpc 的 Niri 会话增加
`fcitx5-x11-reconnect.service`。它读取会话 DISPLAY，确认 Fcitx 的 X11 连接，
通过 `xprop -spy` 等待显示断开；断开时重启输入法服务，重建客户端上下文。
正常运行时阻塞等待，不轮询、不周期重启。普通服务停止不会触发恢复。
已有连接是正常状态；其他连接错误由 systemd 每三秒重试。

显示连接断开后的恢复可能清除尚未提交的拼音，不关闭微信或其他应用。
配置仅修复已观察到的 X11 断线场景，不调整所有应用的输入法后端。

完整系统与 Home Manager generation 构建、恢复单元执行路径及 HM 备份选项已核对。
临时独立 D-Bus/Xvfb/Fcitx 会话用于验证健康时等待、X 显示断开后请求恢复；
测试替换了 systemctl 操作为标记写入，不调用真实会话的服务管理器。

用户在普通终端应用：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
systemctl --user status fcitx5-x11-reconnect.service
```

再次遇到同类故障，可先执行：

```bash
systemctl --user restart fcitx5-daemon.service
```

然后按 Esc，重新输入拼音。若仍异常，需进一步核对当时的焦点、输入上下文和候选窗，
不要直接结束 XWayland 或微信。
