# nix-tools 项目宪法 (Constitution)

本文档定义 nix-tools 工程不可违背的核心架构原则、安全红线与质量准则。所有通过 Spec Kit 创建的特性规格（`spec.md`）、技术方案（`plan.md`）及实施任务（`tasks.md`）必须严格遵守本宪法。

---

## 核心原则 (Core Principles)

### 原则 I：PC 权威构建与单向调度原则 (PC Build Authority & Anti-Recursion)
- **环境定义**：PC（主机名 `liu-bigpc`，路径 `/home/liou/nix-tools`）是唯一的开发构建工作站，具备完整的 Nix/devenv/Cargo/Node/Podman 工具链。NUC（`liou@nuc.local`）与阿里云（`root@47.93.153.102`）仅作为运行宿主。
- **构建与运行分离**：所有产品代码编译（前端静态资源打包、后端容器镜像构建）必须且只能在 PC 执行；目标服务器仅负责备份、传输、镜像加载（`load`）与容器激活。严禁在远端服务器上执行源码编译。
- **单向调度严禁递归**：部署流程由 PC 统一协调，调用各产品的 `just build private/public`；严禁调用下游产品的 `deploy` 快捷命令，避免反向递归调用。
- **实现维护**：保留复杂的 Python 配置渲染、备份、镜像激活与回滚逻辑，不回退为旧 Shell 或 Nushell 临时包装。

### 原则 II：严格三级隔离与绝对安全红线 (Three-Tier Isolation & Absolute Security)
- **三级访问场景**：
  1. NUC `dufs-lan`：局域网认证读写；
  2. NUC `dufs`：局域网密码只读；
  3. 阿里云：公网匿名只读。
  访问场景的写请求拦截、运行能力与只读挂载由部署配置严格控制，严禁将前端 UI 隐藏或公网构建当做安全边界。
- **绝对安全红线**：
  - 绝对禁止向阿里云公网服务器传输私有数据、私钥、或 Whisper 语音转写模型。
  - 严格保护 Bevy 独立资产目录（`bevy-sketch`、`bevy-game`、`project-planner`），发布时严禁覆盖或删除。
  - 严禁在 NUC 上擅自执行 NixOS switch。

### 原则 III：镜像实体真实性与非原子容灾边界 (Image Verification & Non-Atomic Recovery)
- **镜像摘要强校验**：DUFS 官方镜像标签必须为 `v0.46.0`（带 v 前缀）。Docker 29 manifest ID 与 Podman ID 不同时，必须验证远端导出的实际配置字节摘要（Config Digest），严禁跳过校验或仅比对版本字符串。
- **非原子容灾假设**：发布不是跨组件的原子事务。后端容器激活失败时仅尝试单点镜像回滚，系统不自动恢复数据库、前端或整个站点；所有发布必须进行人工与自动化验收。
- **连接安全**：严禁跳过 SSH 主机密钥校验。现有 NUC Compose 可能联动重建代理，部署后必须验收恢复代理连通性。

### 原则 IV：单源 Spec 规范与状态镜像协议 (Single-Source Spec & State Mirroring)
- **唯一事实源**：本仓库本地的 `specs/` 目录是所有功能特性、架构改造与实施任务的唯一权威事实源。禁止建立脱离仓库的平行待办或冲突计划。
- **状态镜像义务**：每当有代码更新或任务清单勾选变动，必须执行 `just sync-todos` 将状态与文档镜像同步至 `liou@nuc.local:/home/liou/dufs-lan/todos/nix-tools/`，保持云端看板（DUFS）实时可见。

---

## 治理规则 (Governance)

1. **最高约束力**：本宪法优先级高于日常开发习惯与临时脚本。任何与本宪法冲突的方案设计在 `/speckit-plan` 阶段均视为审查不通过。
2. **修订程序**：宪法原则的修改必须有明确的技术理由，并经由显式确认与记录。

**版本**: 1.0.0 | **批准日期**: 2026-09-10 | **最近修订**: 2026-09-10
