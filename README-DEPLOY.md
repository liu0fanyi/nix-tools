# 生产环境部署指南 (精简版)

采用 **“Caddy 托管静态 UI + Dufs 纯净数据服务”** 的解耦架构，无需在服务器上维护源码。

## 1. 本地准备与传输

### A. 前端 (Dufs-plus)
```bash
# 1. 编译前端产物
cd dufs-plus
trunk build --release

# 2. 将 dist 目录同步到服务器 (路径必须与 caddy-prod.nix 一致)
rsync -avz dist/ root@remote-server:~/dufs/dist/
```

### B. 后端镜像 (Tag-server)
```bash
cd tag-all
# 1. 构建本地镜像
nu redeploy.nu

# 2. 流式传输镜像到服务器
podman save tag-server:latest | ssh root@remote-server "podman load"
```

## 2. 应用配置 (服务器端)

在服务器的 `nix-tools` 目录下运行：

```bash
# 一键激活生产环境配置 (Podman + Caddy)
nu rerun.nu production
```

---

### 💡 备注
- **Dufs**: 使用官方 `sigoden/dufs` 镜像，由 Nix 自动从 Registry 拉取。
- **存储路径**: 默认所有数据存放在 `~/dufs/`，静态 UI 存放在 `~/dufs/dist/`。
- **域名修改**: 若更换域名，请编辑 `home-manager/nix_modules/caddy-prod.nix`。
