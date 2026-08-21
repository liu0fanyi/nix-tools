# KeePassXC 密钥库 CLI 操作

这份手册只记录操作方法，不包含任何真实密码、API Key 或 key 文件内容。下面的命令都按
Nushell 语法写成单行；每次执行一条即可直接粘贴。

## 基本变量

```nu
let db = ($env.HOME | path join "Sync" "secrets" "secrets.kdbx")
```

每次 `keepassxc-cli` 操作都会要求输入 KeePassXC 数据库主密码。不要把主密码或真实
密钥写入命令参数、Shell 历史、Git 或本文档。

## 添加 API Key

首次使用时创建 `ai` 分组；如果已经存在，提示群组已存在可以忽略：

```nu
keepassxc-cli mkdir $db ai
```

以 OpenAI 为例，API Key 放在条目的密码字段中：

```nu
keepassxc-cli add --password-prompt --url https://platform.openai.com --notes "OpenAI API key" $db ai/openai-api-key
```

命令会先要求数据库主密码，再隐藏输入要保存的 API Key。其他服务可以使用类似条目：

```text
ai/anthropic-api-key
ai/gemini-api-key
ai/github-token
```

这里必须使用 `--password-prompt`。不要使用 `--no-password`；它表示关闭数据库主密码，
不是“让条目的密码为空”。

## 查看或更新 API Key

查看条目密码字段（会把 API Key 显示在当前终端）：

```nu
keepassxc-cli show --show-protected --attributes Password $db ai/openai-api-key
```

更新已经存在的条目：

```nu
keepassxc-cli edit --password-prompt $db ai/openai-api-key
```

如果 API Key 已被服务商撤销或过期，KeePassXC 不能重新生成它；应先在服务商控制台生成
新 Key，再用上面的 `edit` 命令更新条目。

## 把 key 文件作为加密附件保存

API Key 适合放在条目的密码字段；证书、SSH 私钥、git-crypt key 等文件应作为附件保存。
以 `nix-tools` 的 git-crypt key 为例，初始化流程已经封装好：

```nu
bash scripts/init-secret-vault.sh
```

它实际保存的位置是：

```text
数据库：~/Sync/secrets/secrets.kdbx
条目：  nix-tools/git-crypt-key
附件：  nix-tools-git-crypt.key
```

保存其他文件时，可以手动创建条目并导入附件。下面示例保存一个 SSH 私钥；路径只指向
本机文件，文件内容不会出现在命令行：

```nu
keepassxc-cli add --notes "SSH private key; stored as an encrypted attachment" $db infrastructure/example-ssh-key
```

```nu
keepassxc-cli attachment-import --force $db infrastructure/example-ssh-key id_ed25519 ($env.HOME | path join ".ssh" "id_ed25519")
```

如果条目已经存在，只执行 `attachment-import` 即可。`--force` 会覆盖同名附件，确认路径
和条目无误后再使用。

## 导出附件到本机使用

导出到明文目录时先收紧目录权限：

```nu
chmod 700 ($env.HOME | path join ".config" "secrets")
```

```nu
keepassxc-cli attachment-export $db infrastructure/example-ssh-key id_ed25519 ($env.HOME | path join ".config" "secrets" "id_ed25519")
```

```nu
chmod 600 ($env.HOME | path join ".config" "secrets" "id_ed25519")
```

导出 `nix-tools` 的 git-crypt key 应使用专用脚本，它会使用临时文件并自动设置权限：

```nu
bash scripts/export-git-crypt-key.sh
```

`~/Sync/secrets/` 中只放加密的 `.kdbx` 数据库；导出的明文文件放在
`~/.config/secrets/`，不应加入 Git，也不应再放回 Syncthing 同步目录。

## 在另一台已同步的电脑上使用

等待 `secrets.kdbx` 同步完成后，使用同一个数据库主密码打开或执行 CLI 命令。需要
`nix-tools` key 文件时运行：

```nu
bash scripts/export-git-crypt-key.sh
```

不要同时在两台电脑编辑 `secrets.kdbx`，否则 Syncthing 可能生成冲突副本。

## DUFS Plus 运行时 secrets

DUFS Plus 部署的运行时 secrets（Authelia/Caddy/DUFS）同样以加密附件形式保存在
`secrets.kdbx` 的 `dufs-plus/secrets` 条目中，与 git-crypt key 同一套保管方式。
这些文件原本只存在于部署机的 `deploy/secrets/`（不入 Git），托管到 KeePassXC 后，
任何一台 Syncthing 同步过的机器都能按需导出。

导入（本机 `deploy/secrets/` → KeePassXC 附件）：

```nu
bash scripts/manage-dufs-secrets.sh import
```

导出（KeePassXC 附件 → 本机 `deploy/secrets/`，自动设置 0700/0600）：

```nu
bash scripts/manage-dufs-secrets.sh export
```

查看已保管的附件清单：

```nu
bash scripts/manage-dufs-secrets.sh list
```

条目固定为 `dufs-plus/secrets`，附件名与 `deploy/secrets/README.md` 列出的必需文件一致
（`authelia_jwt_secret`、`authelia_session_secret`、`authelia_storage_key`、
`authelia_users_database.yml`、`dufs-readonly.yaml`、`caddy_lan_basic_auth`、可选
`tag-server.env`）。所有命令都要求在本机交互式终端运行，主密码只由
`keepassxc-cli` 交互提示。
