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
