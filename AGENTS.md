# nix-tools 构建发布入口

控制源码以 PC `/home/liou/nix-tools` 为准，部署细则见 `deploy/AGENTS.md`。
开始规划或实施前通过 SSH 读取 liou@nuc.local:/home/liou/dufs-lan/todos/ 下
a-next.md、a-observe.md、a-done.md；状态变化写回对应文件，不另建冲突计划。

## 常用命令

以下命令在 `/home/liou/nix-tools` 执行；已进入 devenv shell 时可省略前缀。

```bash
devenv shell -- just test
devenv shell -- just deploy nuc infra
devenv shell -- just deploy nuc frontend
devenv shell -- just deploy nuc tag-server
devenv shell -- just deploy nuc all
devenv shell -- just deploy aliyun all
devenv shell -- just -- deploy nuc all --dry-run
devenv shell -- just -- deploy aliyun all --dry-run
devenv shell -- just deploy nuc frontend --frontend-app devices
```

目标 nuc/aliyun 必须明确；组件可用 infra/frontend/tag-server/all/runtime-images，
省略组件时两端都为 infra。infra 是基础设施发布，原 config 发布组件不再接受。
管理器内部 manage config 是渲染配置，含义不同；NUC 运维入口为 `just manage <操作>`。
全流程预演使用 `just -- deploy ... --dry-run`；`just --dry-run` 仅展开 recipe。

## 构建和部署边界

- frontend：调用 PC dufs-plus 的 `just build private/public`，备份、上传并校验前端。
- tag-server：调用 PC tag-all 的 `just build private/public <image>`，备份、传镜像、激活和验收。
- infra：备份并同步非密钥部署文件，PC 拉取并传输基础镜像，校验、应用容器配置并检查入口。
  包括 Caddy、DUFS；NUC 另有只读网关、Authelia、DDNS。不是从源码编译 Caddy。
- all：两个产品与基础设施一起发布；runtime-images 仅传输基础镜像，不切换容器。

NUC 用 private + Podman，阿里云用 public + Docker。所有产品构建在 PC 执行；
服务器只备份、加载和运行。产品 `just deploy` 反向调用这里，所以这里只能调用产品
`just build`，不能调用产品 deploy，避免递归。复杂 Python 配置/备份/激活/回滚代码保留，
不要恢复旧 release-nuc/release-aliyun 等 Shell 包装或产品 .nu/.sh 构建包装。

DUFS 官方镜像标签为 v0.46.0（带 v）。Docker 29 可能以 manifest ID 表示镜像，
与 Podman ID 不同时必须验证远端导出的实际配置字节摘要，不能跳过校验或仅比较版本字符串。
真实生产验收和备份位置见 deploy/docs/production-verification.md。

默认源码目录为 /data/project/dufs-plus 和 /data/project/tag-all，可用
--frontend-source / --tag-source 显式指定。产品通过 NIX_TOOLS_DIR 指定本控制仓库。
TAG_PODMAN_URL 可指定 PC 自己的 Podman 服务；桌面容器受限时使用 PC 宿主执行环境。

## 安全与三种访问场景

NUC dufs-lan 为认证读写，NUC dufs 为密码只读，阿里云为匿名只读；认证、运行能力、
写请求拦截和只读挂载由部署配置控制，不把 public 构建或 UI 隐藏当作安全边界。
保护 Bevy 三个独立目录，不传私有数据、密钥或 Whisper 模型到阿里云，不执行 NixOS switch。
后端激活失败尝试镜像回滚，但不自动恢复数据库、前端或整个站点；发布不是多组件原子事务。
现有 NUC Compose 可能联动重建代理，必须验收恢复。不要跳过 SSH 主机密钥校验。

## 文档发布

用户文档发布到 liou@nuc.local:/home/liou/dufs/nix-tools/，根部 README.md 为索引，
正文放 docs/。本文对应发布副本为 docs/build-agent-guide.md；变更时同步更新索引和副本。
