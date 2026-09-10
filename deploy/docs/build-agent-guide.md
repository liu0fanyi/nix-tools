# nix-tools 构建发布与 Agent 协作入口

本文档是 Agent 在本仓库中的主要操作手册（Runbook）。核心架构约束与安全红线以 `.specify/memory/constitution.md`（项目宪法）为准。

---

## 一、环境角色与状态镜像协议

1. **三端环境与角色定义**：
   - **PC（本地开发工作站）**：当前 Agent 会话所在宿主环境（主机名 `liu-bigpc`）。控制仓库为 `/home/liou/nix-tools`，各产品源码位于 `/data/project/`（如 `dufs-plus`、`tag-all`）。拥有完备的 Nix、devenv、Rust、Node 与本地 Podman 工具链。**所有代码编译、镜像构建与 Spec 规格设计必须且只能在 PC 执行**。
   - **NUC（家庭私有服务器）**：主机名 `nuc`（`liou@nuc.local`）。目标运行环境，仅通过 SSH 接收 PC 打包好的 Podman 镜像与静态 dist，作为服务运行与数据存储载体，绝不在此编译源码。
   - **Aliyun（公网只读服务器）**：`root@47.93.153.102`。公网匿名只读运行环境，仅通过 SSH 接收 PC 打包好的 Docker 镜像，绝不在此编译源码，绝不存放私密数据。

2. **权威源与状态镜像协议**：
   - PC `/home/liou/nix-tools` 是代码与 Spec 规格的**唯一权威源**。
   - **状态镜像**：每当有代码更新或任务勾选变动（无论是否涉及部署），必须执行 `just sync-todos`，自动将本地 `specs/`、`docs/` 以及生成的汇总看板 `README.md` 增量镜像到 `liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/`，供云端“项目进展”与 DUFS 实时查阅。
   - 彻底废除旧的 SSH 读写 `a-next.md` 安排计划的方式，不另建脱离仓库的平行计划。

---

## 二、常用命令与预演规则

以下命令在 `/home/liou/nix-tools` 执行；已进入 devenv shell 时可省略前缀。

```bash
devenv shell -- just test                            # 本地单元与回归测试
devenv shell -- just sync-todos                      # 镜像 specs/docs 至 NUC 看板
devenv shell -- just deploy nuc infra                # 部署 NUC 基础设施（Caddy/DUFS/Authelia等）
devenv shell -- just deploy nuc frontend             # 部署前端
devenv shell -- just deploy nuc tag-server           # 部署后端镜像
devenv shell -- just deploy nuc all                  # 全量部署
devenv shell -- just deploy aliyun all               # 阿里云全量部署
devenv shell -- just -- deploy nuc all --dry-run     # 部署全流程预演（不真实切换）
devenv shell -- just manage <操作>                   # NUC 运维管理入口
```

- **目标与组件**：目标 `nuc/aliyun` 必须明确；组件可用 `infra/frontend/tag-server/all/runtime-images`，省略组件时默认为 `infra`。`infra` 是基础设施发布，原 `config` 发布组件不再接受。
- **管理器与预演**：管理器内部 `manage config` 是渲染配置，含义不同；NUC 运维入口为 `just manage <操作>`。全流程预演使用 `just -- deploy ... --dry-run`；`just --dry-run` 仅展开 recipe。

---

## 三、构建与部署边界

1. **组件职责**：
   - `frontend`：调用 PC dufs-plus 的 `just build private/public`，备份、上传并校验前端。
   - `tag-server`：调用 PC tag-all 的 `just build private/public <image>`，备份、传镜像、激活和验收。
   - `infra`：备份并同步非密钥部署文件，PC 拉取并传输基础镜像，校验、应用容器配置并检查入口。包括 Caddy、DUFS；NUC 另有只读网关、Authelia、DDNS。不是从源码编译 Caddy。
   - `all`：两个产品与基础设施一起发布；`runtime-images` 仅传输基础镜像，不切换容器。

2. **单向调度防递归**：
   - NUC 用 private + Podman，阿里云用 public + Docker。所有产品构建在 PC 执行；服务器只备份、加载和运行。
   - 产品 `just deploy` 反向调用这里，因此这里**只能调用产品 `just build`，绝不能调用产品 `deploy`**，避免递归调用。
   - 复杂 Python 配置/备份/激活/回滚代码保留，不要恢复旧 release-nuc/release-aliyun 等 Shell 包装或产品 .nu/.sh 构建包装。

3. **源码与运行环境**：
   - 默认源码目录为 `/data/project/dufs-plus` 和 `/data/project/tag-all`，可用 `--frontend-source` / `--tag-source` 显式指定。
   - `TAG_PODMAN_URL` 可指定 PC 自己的 Podman 服务；桌面容器受限时使用 PC 宿主执行环境。

---

## 四、安全与三种访问场景

1. **访问场景隔离**：
   - NUC `dufs-lan` 为认证读写，NUC `dufs` 为密码只读，阿里云为匿名只读。
   - 认证、运行能力、写请求拦截和只读挂载由部署配置控制，不把 public 构建或前端 UI 隐藏当作安全边界。
2. **绝对安全红线**：
   - 绝对禁止向阿里云公网服务器传输私有数据、密钥或 Whisper 语音转写模型。
   - 保护 Bevy 三个独立目录（`bevy-sketch`、`bevy-game`、`project-planner`），发布时严禁覆盖。
   - 严禁在 NUC 上擅自执行 NixOS switch。

---

## 五、镜像真实性与容灾边界

1. **镜像校验**：
   - DUFS 官方镜像标签为 `v0.46.0`（带 v）。
   - Docker 29 可能以 manifest ID 表示镜像，与 Podman ID 不同时必须验证远端导出的实际配置字节摘要（Config Digest），严禁跳过校验或仅比较版本字符串。
   - 真实生产验收和备份位置见 `deploy/docs/production-verification.md`。
2. **非原子容灾**：
   - 后端激活失败尝试镜像回滚，但不自动恢复数据库、前端或整个站点；发布不是多组件原子事务。
   - 现有 NUC Compose 可能联动重建代理，部署后必须验收恢复。严禁跳过 SSH 主机密钥校验。

---

## 六、文档发布与多端隔离约束

1. **文档闭环**：
   - 用户文档保留仓库权威源文件，并在每次状态变动或任务结束时由 `just sync-todos` 统一镜像同步到 `liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/`。
   - `README.md` 为索引，正文放 `docs/`。本文对应 `deploy/docs/build-agent-guide.md`；变更时同步更新索引和副本。
2. **目录保护隔离**：
   - 不得覆盖 NUC `todos/` 根部三份全局文件或其他工程资料。
   - 不得向 xiaoqiang 专用的 `/home/liou/dufs/` 重建本工程文档。容器发布流程不变。
