# 任务

- [x] 核对 NUC 私人/只读和阿里云服务实际启动命令由 `deploy/scripts/render.py` 生成。
- [x] 只读实例启动命令传入 `--disable-sync`；渲染回归测试通过。
- [x] 本机按标准入口运行 private 镜像 tester 与 NUC 部署预演；镜像传输摘要和入口 smoke 验证通过。
- [x] NUC 5006/5008 已应用配置并验收：私人同步导出 200、只读同步导出 403、只读位置读取 200。
- [ ] 阿里云 public 镜像构建、部署预演与只读实例验收；本次只部署 NUC。
- [x] NUC 私人 HTTPS 5009 的 LAN 身份与挑战精确路由已加入渲染器，home/阿里云渲染测试通过；尚未部署，功能契约仍以 tag-all 016 为准。
- [x] NUC 私人 mDNS companion 的渲染已加显式 `tag_peer_discovery` 开关，默认关闭；home/阿里云与开启场景渲染测试通过，尚未发布或启用。
- [x] liu-bigpc 的 5009 仅 eno1/LAN 防火墙规则已完成 Nix 求值、完整 toplevel 与 Home Manager generation 构建；按本仓规则未由 Agent 执行系统切换，NUC 到 PC 5009 仍不可达。
- [ ] 2026-09-28 用户两次执行 liu-bigpc switch 均因 Avahi 旧 PID 文件不可删除而返回 4。目录属 avahi，原清理钩子继承服务单元裁剪的能力，root 缺少 CAP_DAC_OVERRIDE；`ReadWritePaths` 已被实测证伪并撤回。现仅将验证旧 PID 的 ExecStartPre 加 `+` 前缀，使其不受主进程能力边界限制；待用户再次 switch 并验收 Avahi、5009 防火墙。
- [ ] 私人 NUC 5009 身份/挑战路由、宿主网络 mDNS companion 与独立 `tag-peer-admin.env` 已完成渲染和 47 项部署测试；PC 私人后端身份接口 200、NUC 到 PC 5009 TCP 可达，NUC private 镜像已通过 tester 并发布。NUC 新实例配置尚待 infra 发布与双端配对验收，签名同步保持关闭。
