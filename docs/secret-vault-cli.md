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

API Key 适合放在条目的密码字段；证书、SSH 私钥、git-crypt key、DUFS secrets 等文件应作为附件保存。
所有密钥文件统一用 `scripts/vault.sh` 管理：加密附件存在 `~/Sync/secrets/secrets.kdbx`，
明文目录 `~/.config/secrets/<组名>/` 与 KeePassXC 组结构直接对齐。首次使用先初始化加密库：

```nu
bash scripts/vault.sh init
```

`nix-tools` 的 git-crypt key 在 `nix-tools` 组（条目 `git-crypt-key`，附件 `nix-tools-git-crypt.key`）：

```text
数据库：~/Sync/secrets/secrets.kdbx
组：    nix-tools
条目：  nix-tools/git-crypt-key
附件：  nix-tools-git-crypt.key
导出：  ~/.config/secrets/nix-tools/nix-tools-git-crypt.key
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

导出 `nix-tools` 的 git-crypt key 应使用 `vault.sh`，它会使用临时文件并自动设置权限：

```nu
bash scripts/vault.sh nix-tools export
```

`~/Sync/secrets/` 中只放加密的 `.kdbx` 数据库；导出的明文文件放在
`~/.config/secrets/`，不应加入 Git，也不应再放回 Syncthing 同步目录。

## 在另一台已同步的电脑上使用

等待 `secrets.kdbx` 同步完成后，使用同一个数据库主密码打开或执行 CLI 命令。需要
`nix-tools` key 文件时运行：

```nu
bash scripts/vault.sh nix-tools export
```

不要同时在两台电脑编辑 `secrets.kdbx`，否则 Syncthing 可能生成冲突副本。

## DUFS Plus 运行时 secrets

DUFS Plus 的运行时凭据（`deploy/secrets/` 下的 Authelia/Caddy/DUFS 文件）**已纳入
git-crypt**（见仓库根 `.gitattributes`），以密文提交在 Git 中，与 `secrets/`
（mihomo/Rime）同一套恢复链路。重装/迁移后只需：

```bash
git-crypt unlock ~/.config/secrets/nix-tools/nix-tools-git-crypt.key
```

即可一键恢复 `deploy/secrets/` 下的全部明文凭据，无需逐文件从 KeePassXC 导出。
详细工作流程见 `deploy/secrets/README.md`。
