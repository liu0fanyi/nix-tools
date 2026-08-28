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

目录权限应为 `0700`，文件权限应为 `0600`。`manage.py preflight` 会在启动前
自动移除当前用户所拥有普通文件的 group/world 权限，然后再次检查；符号链接或
其他用户拥有的路径仍会报错，避免静默接管不可信文件。

这里是可恢复的加密权威源，不是容器的长期挂载目录。本机渲染时会将已解密
的内容安全同步到 `~/.config/dufs-plus/secrets/`；运行中的容器只读挂载该
稳定路径，因此不依赖 `nix-tools` 工作区的具体位置。

## 工作流程

- **首次加入**（在持有明文的部署机上）：`git-crypt unlock` → 放置明文文件 →
  `git add` + `git commit` + `git push`（git-crypt 自动加密后提交）
- **重装恢复**：`git pull` → `git-crypt unlock <key>` →
  `python3 deploy/scripts/manage.py preflight`。最后一步会将 Git 无法保存的私密权限
  恢复为目录不高于 `0700`、凭据文件不高于 `0600`
- 加密库中的 git-crypt key 由 KeePassXC 保管（`scripts/vault.sh nix-tools export`）

## 注意

- `.gitignore` 只忽略临时杂项（`*.tmp`/`*.bak`/`*~`）；真实凭据文件**必须**进 git 加密
- 不要提交**未解锁**状态下的明文（git-crypt 未解锁时 add 会原样提交，失去保护）
- 始终先 `git-crypt unlock` 再操作本目录文件
