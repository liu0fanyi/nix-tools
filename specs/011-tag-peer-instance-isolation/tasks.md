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
- [x] NUC infra 按统一发布入口完成备份、传输、预检、Caddy 重建与 smoke；未登录访问 `/tag-api/peer-manager` 和 `/tag-api/v1/peers/web/requests` 均返回 401。
- [ ] 在真实网页窗口显示新的待处理申请、点击同意后核对双方配对；只读入口拒绝管理操作仍需现场验收。
- [x] NUC 公布 `https://nuc.local:5009`，Caddy 覆盖该主机名；PC 使用原内部 CA 验证证书，身份端点 200 且连接到 192.168.1.12；PC 发现候选及受信记录均为内网地址，指纹未变。
- [x] 修复 NUC 配对网页请求列表的 401：Caddy 同时设置和删除 `X-Tag-Admin-Token`，当前版本最后执行删除；移除删除规则后，运行中的适配配置只设置该请求头，48 项渲染/发布测试通过，NUC infra 重新部署及入口 smoke 通过。真实浏览器列表刷新仍待用户窗口确认。
- [x] 私人 HTTPS 5009 的节点读取路径从 Authelia 浏览器鉴权中精确排除，并对这组路径统一做 LAN 限制；48 项部署测试及 Caddy 实际配置解析通过。NUC infra 备份、重建和 smoke 完成；PC 用受信 CA 请求 NUC 的位置、Markdown 读取接口均返回 200，文件流返回 206。非 LAN 来源拒绝由配置结构核对，外网实测仍待安全验收。
