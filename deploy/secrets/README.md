# Runtime secrets

这个目录保存 DUFS Plus 实例的运行时凭据。真实凭据文件由 **git-crypt 加密后提交**
（见仓库根 `.gitattributes` 的 `deploy/secrets/** filter=git-crypt`），重装/迁移后
`git-crypt unlock` 即可一键恢复明文，无需逐文件从 KeePassXC 导出。

需要的文件：

- `authelia_jwt_secret`
- `authelia_session_secret`
- `authelia_storage_key`
- `authelia_users_database.yml`
- `dufs-readonly.yaml`
- `caddy_lan_basic_auth`
- 可选：`tag-server.env`

目录权限应为 `0700`，文件权限应为 `0600`（manage.py preflight 会检查）。

## 工作流程

- **首次加入**（在持有明文的部署机上）：`git-crypt unlock` → 放置明文文件 →
  `git add` + `git commit` + `git push`（git-crypt 自动加密后提交）
- **重装恢复**：`git pull` → `git-crypt unlock <key>` → 明文凭据自动出现在本目录
- 加密库中的 git-crypt key 由 KeePassXC 保管（`scripts/vault.sh nix-tools export`）

## 注意

- `.gitignore` 只忽略临时杂项（`*.tmp`/`*.bak`/`*~`）；真实凭据文件**必须**进 git 加密
- 不要提交**未解锁**状态下的明文（git-crypt 未解锁时 add 会原样提交，失去保护）
- 始终先 `git-crypt unlock` 再操作本目录文件
