# 实施方案

## Constitution Check

本仓只负责配置渲染及发布入口；Tag Server 功能实现归 `/data/project/tag-all/specs/016-private-peer-discovery/`。符合 PC 权威构建、目标实例隔离和不向阿里云传私密数据的宪法约束。部署前按既有 `just -- deploy ... --dry-run` 核对源、目标、删除范围与回滚；NUC 已按此流程构建并备份，阿里云尚未部署。

## 路径

在 compose 实例渲染器中，对 NUC 只读服务固定加参数；主实例读取独立的 `features.tag_peer_sync`，阿里云将其配置为 `false`，NUC 私人实例配置为 `true`。渲染测试分别检查三种命令，再按正常发布流程验收。

NUC 实施时先通过 `just deploy nuc tag-server` 构建、备份并激活新镜像。`just deploy nuc infra` 已同步新配置，但在拉取 DUFS 基础镜像时被注册表认证拒绝，未进入 `manage up`；随后使用仓库提供的 `just manage preflight`、`config`、`up --confirm` 和 `smoke` 完成配置应用与验收。阿里云须独立预演和发布，不从 NUC 的结果推断其已生效。
