# 生产环境部署指南 (Docker Compose 极简版)

不再依赖服务器上的 Nix 环境，仅需安装 `docker` 和 `docker-compose` 即可运行。

## 1. 本地准备与传输

### A. 前端 (Dufs-plus)
```bash
# 1. 编译前端产物
cd dufs-plus
trunk build --release

# 2. 将 dist 目录同步到服务器的 nix-tools/dist
rsync -avz dist/ root@remote-server:~/nix-tools/dist/
```

### B. 后端镜像 (Tag-server)
```bash
cd tag-all
# 1. 构建本地镜像
nu redeploy.nu

# 2. 流式传输镜像到服务器
podman save tag-server:latest | ssh root@remote-server "docker load"
```

## 2. 一键部署 (服务器端)

在服务器的 `nix-tools` 目录下运行：

```bash
# 启动所有服务 (Caddy + Dufs + Tag-server)
docker compose up -d
```

---

### 📂 目录结构说明
部署完成后，服务器上的 `nix-tools` 目录结构应如下：
- `docker-compose.yml` (容器编排)
- `Caddyfile.prod` (Caddy 配置)
- `dist/` (前端静态文件)
- `dufs_data/` (Dufs 存储路径)
- `tag-db/` (标签数据库存放路径)

### 💡 优势
- **极致轻量**：服务器不再下载数百 MB 的 Nix 运行时（如 glibc、Podman 依赖）。
- **环境隔离**：所有依赖（Caddy, Dufs, Tag-server）均在镜像内部，互不干扰。
- **配置一致**：Caddyfile 已针对容器网络调优，支持 API 优先转发。
