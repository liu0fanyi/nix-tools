# Tag Server 实例同步隔离

## 范围

私人 NUC 的生成配置须把 mDNS 公布的 `https://nuc.local:5009` 同时写入 tag-server 的 `discovery.advertise_url`，供配对申请回联；仅配置发现 companion 不足以发起申请。

NUC 5006 私人实例保留既有 peer 同步。NUC 5008 只读实例及阿里云只读实例启动 tag-server 时必须传入 `--disable-sync`，由后端拒绝同步导出、导入、主动同步和通知接口。私人主实例由独立的 `[features].tag_peer_sync` 布尔值控制，不从文件写权限、镜像 profile 或主机名推断。只读附加实例固定禁用同步。Tag Server 的功能契约见 `/data/project/tag-all/specs/016-private-peer-discovery/`。

## 验收

- 本机渲染 `home` 配置：私人 `tag-server` 命令无该参数，`tag-server-readonly` 命令有该参数。
- 本机渲染 `aliyun` 配置：唯一的只读 `tag-server` 命令有该参数。
- Tag Server 禁用同步时，`/v1/sync/*` 与 `/tag-api/v1/sync/*` 返回 403，普通位置读取仍可用。
- 生产验收需分别核对 NUC 5006、5008 与阿里云实例；仅渲染测试通过不能宣称已部署。

## NUC 网页配对管理入口

私人 NUC 的 `http://nuc.local:5006/tag-api/peer-manager` 继续受 LAN IP 范围和 Caddy Basic 登录保护。页面只显示待处理申请，不包含管理令牌。Caddy 容器只读挂载同一私人实例的 `tag-peer-admin.env`，启动时加载环境变量，仅在 `/tag-api/v1/peers/web/*` 路由向后端注入 `X-Tag-Admin-Token`；入站申请和签名回执在私人 HTTPS 5009 上仅放行明确的两个路径，仍要求 LAN 来源，且不注入管理员凭据。只读实例、阿里云和其他页面不接收此令牌。写操作由后端额外检查 `X-Tag-Pairing-Intent: 1`。 反向代理仅使用 `header_up X-Tag-Admin-Token ...` 覆盖客户端同名请求头；不得再为同一请求头同时配置删除操作，否则 Caddy 会在设置后将其删除并导致后端 401。

渲染测试检查路由、secret 挂载和只读实例隔离；生产验收须打开 NUC 网页并实际读取待处理申请。

## 私人节点地址

NUC 在 mDNS 中公布 `https://nuc.local:5009`，Caddy 的内部 CA 证书覆盖 `nuc.local`。PC/NUC 的私人 peer 流量直接走局域网，不使用 EdgeOne 域名作为发现地址。现有 `nas.wttliou.top:5009` 仍保留入口供过渡，但 PC 的受信记录在身份与证书核验后改成 `nuc.local`。HTTPS 保留，用于加密和校验节点身份；新增节点首次配对的 CA 引导由 tag-all 016 继续设计。
