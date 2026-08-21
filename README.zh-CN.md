# Nix 工具

本仓库包含宿主机开发环境配置，以及 DUFS Plus 容器部署控制面。

## Home Manager

安装 Nix 后应用宿主机配置：

```bash
nix shell nixpkgs#nushell -c nu ./rerun.nu liou
```

Home Manager 只负责开发应用、Podman 工具、ttyd 和 Podman API socket。
它不再声明 Caddy、DUFS、Tag Server、Authelia、DDNS-Go 或对应的
systemd 服务。

非 NixOS 环境中的 rootless Podman 还需要系统发行版提供
`newuidmap` 和 `newgidmap`，例如 Debian/Ubuntu 的 `uidmap` 包。

## DUFS Plus 部署

应用服务统一由 Compose 部署管理：

```bash
python3 deploy/scripts/manage.py config
python3 deploy/scripts/manage.py ps
python3 deploy/scripts/release-apps.py all
```

实例配置、首次安装、备份、验证和发布命令见
[deploy/README.md](deploy/README.md)。运行时 secret 不进入 Git，单独存放在
`deploy/secrets/`。

需要用户服务在未登录时启动，可启用 linger：

```bash
loginctl enable-linger "$USER"
```

## 远程 NixOS 重装

目标机 `192.168.1.6` 当前使用 16 GiB 独立 swap LV；如果再次执行全盘重装，
仓库提供了安装配置和一键入口，会由 disko 直接划出独立 swap LV。脚本按目标机内存自动选择
16/24/32/64 GiB 档位（也可通过 `NIXOS_ANYWHERE_SWAP_GIB` 或 `NIXOS_ANYWHERE_FLAKE` 手动指定）：

```bash
bash scripts/install-nixos-anywhere.sh
```

脚本默认目标为 `root@192.168.1.6`，会先要求输入 `REINSTALL` 确认，避免误清盘。
确认备份无误后也可以使用 `bash scripts/install-nixos-anywhere.sh --yes` 跳过提示。
自动档位目前要求目标为 x86_64、UEFI/efivars 可写、只有一块内部 `/dev/sda`；其他磁盘、BIOS 或架构会在清盘前停止，需先准备适配的 flake。

安装脚本默认自动探测本机 Clash Verge/mihomo 的 `127.0.0.1:7897`，追加清华 Nix substituter，
并由本机直接推送闭包，避免目标 kexec 环境从远程 cache 慢速补依赖。可用
`NIXOS_ANYWHERE_PROXY_MODE=off` 关闭代理，或用
`NIXOS_ANYWHERE_USE_DESTINATION_SUBSTITUTERS=1` 恢复目标端下载。

默认的 kexec 模式也会先通过本机代理下载并缓存官方安装镜像（默认在
`~/.cache/nixos-anywhere`），再通过 `nixos-anywhere --kexec` 上传给目标机，避免临时安装系统直连
GitHub 下载约 418 MiB 的镜像。已有镜像可用 `NIXOS_ANYWHERE_KEXEC_PATH` 复用，缓存目录可用
`NIXOS_ANYWHERE_KEXEC_CACHE_DIR` 修改；只有目标机能稳定直连时才显式设置
`NIXOS_ANYWHERE_KEXEC_MODE=remote`。上游参数说明见
[nixos-anywhere custom kexec 文档](https://github.com/nix-community/nixos-anywhere/blob/main/docs/howtos/custom-kexec.md)。

代理和目标地址都不需要写死在脚本中：

```bash
NIXOS_ANYWHERE_TARGET=root@192.168.1.23 \
NIXOS_ANYWHERE_PROXY_URL=http://127.0.0.1:8890 \
NIXOS_ANYWHERE_REMOTE_PROXY_URL=http://192.168.1.3:8890 \
  bash scripts/install-nixos-anywhere.sh --check
```

`NIXOS_ANYWHERE_PROXY_URL` 是本机执行安装时使用的代理；`NIXOS_ANYWHERE_REMOTE_PROXY_URL`
是重装后目标机临时访问本机代理的地址，端口可以不同。未显式设置后者时，脚本会把本机回环地址
替换成到目标机的局域网地址，并在清盘前测试目标机是否能访问；必须使用代理时可设置
`NIXOS_ANYWHERE_REMOTE_PROXY_CHECK=required`，测试失败就会停止。目标 SSH 用户/地址也可拆开配置：
`NIXOS_ANYWHERE_SSH_USER`、`NIXOS_ANYWHERE_SSH_HOST`，但这套清盘流程实际应使用有 root 权限的 SSH 目标。

清华源已经是两层默认配置：脚本本次运行通过 `NIX_CONFIG` 追加
`https://mirrors.tuna.tsinghua.edu.cn/nix-channels/store`，而目标 NixOS 的
`nix.settings.extra-substituters` 也会持久化该源；可用 `NIXOS_ANYWHERE_EXTRA_SUBSTITUTERS`
覆盖本次安装。目标电脑的代理端口变化不会改变 NixOS 配置，只需更新上面的两个 URL。

如果本机有 `nix-tools-git-crypt.key` 和已解锁的 secrets，安装完成后脚本会自动恢复
`mihomo/clashtui`、Rime userdb 和 npm 工具；恢复脚本会通过本机代理预取并缓存
`geosite.dat`、`geoip.dat` 后上传，目标机可达的局域网代理只临时用于首次下载订阅，启动成功后不会把
这个代理写入 NixOS 配置。重启后脚本会先等待目标 SSH 恢复，再执行恢复。默认
`NIXOS_ANYWHERE_RESTORE_SECRETS=required`，在 secrets 不完整时会在清盘前停止；只有明确
想安装不含运行时 secrets 的基础系统时才设置 `NIXOS_ANYWHERE_RESTORE_SECRETS=off`。

统一的个人密钥不放在仓库目录下：KeePassXC 加密库默认位于
`~/Sync/secrets/secrets.kdbx`，由 Syncthing 只同步加密后的数据库；当前机器需要使用的
明文导出文件位于 `~/.config/secrets/<组>/`，默认 git-crypt key 是
`~/.config/secrets/nix-tools/nix-tools-git-crypt.key`。所有密钥统一用 `scripts/vault.sh`
管理（加密库初始化 + 各组的导入/导出）：

```nu
bash scripts/vault.sh init                # 首次创建加密库
bash scripts/vault.sh nix-tools export    # 导出 git-crypt key
```

该 git-crypt key 同时解锁 `secrets/`（mihomo/Rime）和 `deploy/secrets/`
（DUFS Plus 运行时凭据）——两者都以密文存在 Git 中，`git-crypt unlock` 一键恢复明文。

大模型 API key 等其他凭据直接作为 KeePassXC 条目保存，例如 `ai/openai-api-key`，不需要
放入 `~/.config/secrets/`，只有明确要求文件或环境变量的程序才导出一份到那里。目录和数据库
位置可以分别通过 `NIX_TOOLS_SECRETS_DIR`、`NIX_TOOLS_SYNC_DIR`、`NIX_TOOLS_VAULT_FILE` 覆盖。
具体的 CLI 添加、查看、导入附件和导出附件命令见
[KeePassXC 密钥库 CLI 手册](docs/secret-vault-cli.md)。

这一步不能省略：mihomo 的订阅配置属于 secrets，不在 NixOS 闭包中。重装后若未恢复，
mihomo 会自动生成只监听 `127.0.0.1:7890` 且没有 controller 的初始配置，clashtui 就会显示
`connection refused`。

NixOS 还会声明式设置 `clashtui/mihomo` 目录的 setgid/组写权限，并让 mihomo 使用
`UMask=0007`，因此 root 创建的 provider/cache 文件可以继续由 clashtui 管理，首次打开不再需要点击
`Fix now`。

重装前后的完整准备、自动验收和本地桌面手动验收见
[nixos/reinstall-checklist.md](nixos/reinstall-checklist.md)。只做重装前只读预检时运行：

```bash
bash scripts/install-nixos-anywhere.sh --check
```
