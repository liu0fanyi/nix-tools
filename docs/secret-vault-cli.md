# KeePassXC 密钥库 CLI 操作

这份手册只记录操作方法，不包含任何真实密码、API Key 或 key 文件内容。

## 基本变量

```bash
DB="$HOME/Sync/secrets/secrets.kdbx"
```

每次 `keepassxc-cli` 操作都会要求输入 KeePassXC 数据库主密码。不要把主密码或真实
密钥写入命令参数、Shell 历史、Git 或本文档。

## 添加 API Key

首次使用时创建 `ai` 分组；如果已经存在，提示群组已存在可以忽略：

```bash
keepassxc-cli mkdir "$DB" ai
```

以 OpenAI 为例，API Key 放在条目的密码字段中：

```bash
keepassxc-cli add \
  --password-prompt \
  --url https://platform.openai.com \
  --notes "OpenAI API key" \
  "$DB" ai/openai-api-key
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

```bash
keepassxc-cli show \
  --show-protected \
  --attributes Password \
  "$DB" ai/openai-api-key
```

更新已经存在的条目：

```bash
keepassxc-cli edit --password-prompt "$DB" ai/openai-api-key
```

如果 API Key 已被服务商撤销或过期，KeePassXC 不能重新生成它；应先在服务商控制台生成
新 Key，再用上面的 `edit` 命令更新条目。

## 把 key 文件作为加密附件保存

API Key 适合放在条目的密码字段；证书、SSH 私钥、git-crypt key 等文件应作为附件保存。
以 `nix-tools` 的 git-crypt key 为例，初始化流程已经封装好：

```bash
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

```bash
keepassxc-cli add \
  --notes "SSH private key; stored as an encrypted attachment" \
  "$DB" infrastructure/example-ssh-key

keepassxc-cli attachment-import \
  --force \
  "$DB" infrastructure/example-ssh-key \
  id_ed25519 \
  "$HOME/.ssh/id_ed25519"
```

如果条目已经存在，只执行 `attachment-import` 即可。`--force` 会覆盖同名附件，确认路径
和条目无误后再使用。

## 导出附件到本机使用

导出到明文目录时先收紧目录权限：

```bash
install -d -m 700 "$HOME/.config/secrets"
keepassxc-cli attachment-export \
  "$DB" infrastructure/example-ssh-key \
  id_ed25519 \
  "$HOME/.config/secrets/id_ed25519"
chmod 600 "$HOME/.config/secrets/id_ed25519"
```

导出 `nix-tools` 的 git-crypt key 应使用专用脚本，它会使用临时文件并自动设置权限：

```bash
bash scripts/export-git-crypt-key.sh
```

`~/Sync/secrets/` 中只放加密的 `.kdbx` 数据库；导出的明文文件放在
`~/.config/secrets/`，不应加入 Git，也不应再放回 Syncthing 同步目录。

## 在另一台已同步的电脑上使用

等待 `secrets.kdbx` 同步完成后，使用同一个数据库主密码打开或执行 CLI 命令。需要
`nix-tools` key 文件时运行：

```bash
bash scripts/export-git-crypt-key.sh
```

不要同时在两台电脑编辑 `secrets.kdbx`，否则 Syncthing 可能生成冲突副本。
