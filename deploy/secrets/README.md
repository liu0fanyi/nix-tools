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

本机首次切换可以运行：

```bash
python3 scripts/import-current-secrets.py
```

脚本从现有 git-crypt 工作区、Authelia 用户文件、Tag Server env 和当前 Caddyfile 导入，不会打印 secret 内容。
