# Runtime secrets

这个目录只保存当前实例的运行时 secret，不提交真实内容。

需要的文件：

- `authelia_jwt_secret`
- `authelia_session_secret`
- `authelia_storage_key`
- `authelia_users_database.yml`
- `dufs-readonly.yaml`
- `caddy_lan_basic_auth`
- 可选：`tag-server.env`

目录权限应为 `0700`，文件权限应为 `0600`。

新机器需要通过安全渠道单独提供这些文件。Home Manager 不再生成或保存
DUFS Plus 服务凭据。
