# PC 发布、访问隔离与 NUC 恢复

## 需求与验收

- PC 统一调度构建、备份、传输、摘要校验、激活与 smoke；NUC Podman 私有、阿里云 Docker 公开只读。产品 deploy 可反调父入口，父只调用产品 build。
- NUC 认证可写、密码只读和阿里云匿名只读分别验收直接路由及 UI；只读拒绝私有工具和根路径别名。设备写路由精确允许 music/order、music/playlists、transcriptions/by-key 等既有端点，仍由后端 scoped token 鉴权，不开放通配写入。
- CDN 私有缓存命中前每次 Authelia 鉴权，异常 fail closed；保留源站 forward_auth。device-api 排除交互登录但仍走 scoped token，API 缓存禁用；安全回滚先禁缓存并清缓存后撤触发器。
- Edge 转发错误返回 no-store 502、request_id、stage、elapsed 和 outcome=unknown，不能推断源操作回滚；日志不记 URL/凭据。控制台发布与源码变更分开验收。
- 数据盘按 UUID 保持逻辑路径，数据库存工作区相对路径；Compose up/start/restart 必须等待真实挂载并排除 autofs，占位失败重试，down 不受门禁影响。
- 恢复保留业务文件、隐藏状态、数据库、托管 Git、静态产物、身份和凭据；数据库 integrity_check、摘要与三入口验证都通过才宣称恢复。发布备份不等于整盘备份。
- NUC profile 独立硬件/磁盘报告，安装只使用核验过的稳定磁盘 ID，资料盘排除，真实文件系统尺寸须验证；安装、运行更新、容器发布分开授权。
- newuidmap/newgidmap 使用 /run/wrappers/bin；保持 UID/subuid 与数据归属，DDNS 网卡与回程路由一致。不能用 VM 成功代替真实重启后的挂载/服务验收。

## 已取消

NUC dsh Web 公网入口已在 ca987da 取消：源码与开发环境迁至 PC。本轮不恢复此需求。
