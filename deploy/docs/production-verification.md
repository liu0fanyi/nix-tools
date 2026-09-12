# 发布验收手册

验证当前实际发布版本，不能把 Git 中旧镜像哈希作为现网状态。

| 场景 | 必测 |
| --- | --- |
| NUC 5006 认证读写 | 匿名拒绝、认证读取、授权临时文件写入和删除、完整工具入口 |
| NUC 5008 密码只读 | 匿名拒绝、认证可读、文件/标签写入拒绝、私有工具直达与别名拒绝 |
| 阿里云匿名只读 | 源站及 CDN 可读、写入拒绝、私有工具入口拒绝 |

比较 index 引用的 JS/WASM/CSS 与服务器摘要，运行发布器 checksum 和相应源站/CDN smoke。浏览器验证旧 Board 偏好在只读站不加载画板，检查资源错误及 pageerror。凭据只用内存，不保存认证 trace/HAR。

精确设备写路由仍由 scoped token 控制；匿名 order、playlists、transcriptions/by-key 请求应拒绝。路由开启不等于完整业务验收；真实数据删除需单独授权。

数据配置备份默认在 ~/.local/state/dufs-plus/backups，前端备份在 frontend-backups；本次具体位置以发布器输出为准。核对受保护 Bevy 产物未改变、代理联动重建后恢复；镜像回滚不自动恢复数据库。规格见 [基础设施](../../specs/009-infrastructure/spec.md)。
