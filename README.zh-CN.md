# Nix 工具

本仓库包含 Nix 配置和工具。

## 安装

要在任何 Linux 发行版上安装 Nix，推荐使用 [Determinate Systems Nix Installer](https://github.com/DeterminateSystems/nix-installer)：

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

## 使用方法

### 密钥管理 (Git-Crypt)

本仓库使用 `git-crypt` 保护敏感凭据（在 `secrets.json` 中）。

**初始化**:
1. 初始化: `git-crypt init`
2. 导出密钥（请通过安全方式备份！）：`git-crypt export-key ./git-crypt-key`

**使用**:
- `secrets.json` 在仓库中是加密的，可以安全提交。
- **在新机器上使用**:
    1. 克隆仓库。
    2. 将你备份的 `git-crypt-key` 复制到仓库根目录。
    3. 运行: `git-crypt unlock ./git-crypt-key`
    4. `secrets.json` 现在应该可以读取了。

### 初始化 HomeManager

首次运行 `rerun.nu` 脚本，请使用（请将 `liou` 替换为你当前的用户名）：

```bash
nix shell nixpkgs#nushell -c nu ./rerun.nu liou
```

默认情况下启用所有功能。要使用“精简”版本（不含 Fcitx5 和 Podman），请运行：

```bash
nix shell nixpkgs#nushell -c nu ./rerun.nu liou --full=false
```

## GPU 设置（非 NixOS）

如果你在非 NixOS 系统上并需要 GPU 支持（例如用于 Alacritty），可能需要使用 `sudo` 运行以下命令：

```bash
sudo /nix/store/9mn5fg9rdw4p8kw0nqz0h5ymwjxhb6is-non-nixos-gpu/bin/non-nixos-gpu-setup
```

## 故障排除

### 应用未在菜单中显示

如果你无法在系统的应用菜单中看到 Alacritty、Zellij 或 Sakura 等应用：

**注销并重新登录**：在非 NixOS 系统上，桌面环境通常需要新的会话来获取 `XDG_DATA_DIRS` 中的新路径。

### 不受信任的 substituter 警告

如果你看到类似 `warning: ignoring untrusted substituter...` 的警告：

这是因为你的用户不在系统 Nix 配置的 `trusted-users` 列表中。运行以下命令修复它：

```bash
echo "trusted-users = root $USER" | sudo tee -a /etc/nix/nix.custom.conf
# 然后重启 nix-daemon
sudo systemctl restart nix-daemon
```

### Podman 服务未启动

如果 `ddns-go` 或 `rustfs` 没有自动启动：


**启用 Linger**：在通用 Linux 上，用户服务仅在你登录时运行。要让它们从启动时运行（并确保它们正确启动），请启用 linger：
    ```bash
    loginctl enable-linger $USER
    ```

### DDNS-GO 休眠后无法工作

如果系统休眠/睡眠唤醒后 `ddns-go` 停止工作，重启服务通常可以修复：

```bash
systemctl --user restart podman-ddns-go
```

**网络配置说明**：
`ddns-go` 通常要求光猫处于 **桥接模式 (Bridge Mode)**，并由路由器进行 PPPoE 拨号上网。你需要知道宽带的拨号账号和密码来进行此配置。如果光猫处于路由模式，`ddns-go` 可能会获取到内网 IP（如 192.168.x.x）而非公网 IP。

如果需要手动重置密码（例如忘记密码）：

```bash
# 将 'YourNewPassword' 替换为你想要的新密码
podman run --rm -v $HOME/.config/ddns-go:/root docker.io/jeessy/ddns-go -resetPassword YourNewPassword
systemctl --user restart podman-ddns-go
```

### 错误：未找到 "newuidmap"

如果在日志中看到类似 `exec: "newuidmap": executable file not found in $PATH` 的错误：

Rootless Podman 需要在主机系统上安装 `newuidmap` 和 `newgidmap` 工具（不仅仅是通过 Nix），因为它们需要 setuid 权限。在基于 Debian 的系统（如 Pop!_OS、Ubuntu）上：

```bash
sudo apt update
sudo apt install uidmap
```

### Podman 配置选项

有关 Home Manager 中更多 Podman 配置选项，请查看：[Home Manager Options - Podman](https://home-manager-options.extranix.com/?query=podman&release=release-25.11)
