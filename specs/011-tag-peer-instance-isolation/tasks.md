# 任务

- [x] 核对 NUC 私人/只读和阿里云服务实际启动命令由 `deploy/scripts/render.py` 生成。
- [x] 只读实例启动命令传入 `--disable-sync`；渲染回归测试通过。
- [x] 本机按标准入口运行 private 镜像 tester 与 NUC 部署预演；镜像传输摘要和入口 smoke 验证通过。
- [x] NUC 5006/5008 已应用配置并验收：私人同步导出 200、只读同步导出 403、只读位置读取 200。
- [ ] 阿里云 public 镜像构建、部署预演与只读实例验收；本次只部署 NUC。
- [x] NUC 私人 HTTPS 5009 的 LAN 身份与挑战精确路由已部署；Caddy 认证匹配器对这两个端点作精确排除，LAN 外访问仍由路由返回 404。PC 使用 NUC CA 验证身份接口 200；功能契约以 tag-all 016 为准。
- [x] NUC 私人 mDNS companion 已显式启用，阿里云和只读实例未启用；PC/NUC 上 `avahi-browse` 均能看见两个服务。候选缓存的周期刷新修复和长期稳定性验证归 tag-all 016。
- [x] 用户完成 liu-bigpc 系统切换；Avahi 处于 active，`eno1` 上 5009 仅允许 LAN，NUC 到 PC 5009 TCP/TLS 可达。旧 PID 清理钩子修复已生效。
- [x] NUC 私人实例使用独立 `tag-peer-admin.env`、PC CA 和 HTTPS 主机名校验；PC/NUC 私人节点分别批准了对方指纹，读取持久批准记录成功。旧同步继续，`sync.require_signatures` 保持关闭。
- [x] 公共 DUFS 镜像的旧认证文件过期时，仅对公共镜像拉取重试匿名访问；NUC infra 备份、传输、激活和 smoke 已通过。
- [x] 为 NUC 网页配对管理页添加 Basic 认证后的专用反向代理与服务端令牌注入；签名申请和回执端点仅在 LAN 私人 HTTPS 入口开放，渲染测试通过。
- [ ] 部署并实测 NUC 网页显示待处理申请、点击同意后双方完成配对；核对只读入口仍拒绝。
