# nix-tools Agent 操作入口

核心架构和安全边界以 [.specify/memory/constitution.md](.specify/memory/constitution.md) 为准。本文件只保留执行规则，不追加清理过程、历史操作记录或故障复盘。

## 环境与职责

- **PC**：`liu-bigpc`，仓库 `/home/liou/nix-tools`，产品源码默认在 `/data/project/dufs-plus`、`/data/project/tag-all`。代码编译、镜像构建和 Spec 设计只在 PC 执行。
- **NUC**：`liou@nuc.local`，私有运行与存储环境；接收 PC 构建产物，不编译源码，不擅自执行 NixOS switch。
- **Aliyun**：`root@47.93.153.102`，公网匿名只读环境；仅接收公开镜像，禁止传输私密数据、密钥和 Whisper 模型。

## 常用入口

在仓库根执行，进入 devenv 后可省略 `devenv shell --`：

```bash
devenv shell -- just test
devenv shell -- just sync-todos --dry-run
devenv shell -- just sync-todos
devenv shell -- just -- deploy nuc all --dry-run
devenv shell -- just deploy nuc all
devenv shell -- just deploy aliyun all
devenv shell -- just manage <操作>
```

- 部署必须明确目标 `nuc/aliyun`；组件为 `infra/frontend/tag-server/all/runtime-images`，默认 `infra`。旧 `config` 发布组件不接受，`manage config` 仅指渲染配置。
- 全流程预演使用 `just -- deploy ... --dry-run`；`just --dry-run` 只展开 recipe。先预演，再执行已获授权的发布。
- NUC 使用 private + Podman，Aliyun 使用 public + Docker。这里只调用产品 `just build`，禁止反向调用产品 `deploy`。源码可用 `--frontend-source`、`--tag-source` 指定；`TAG_PODMAN_URL` 仅指向 PC 的 Podman。
- 保留现有 Python 备份、配置、激活和回滚实现，不恢复旧 Shell/Nushell 发布包装。

## 本机系统配置

- `rerun.nu` 默认由用户在普通终端手动运行：`nu rerun.nu liou --host <当前主机名>`。Agent 不代为 switch；只有用户明确要求 Agent 执行时才例外，且必须显式传当前主机名。NUC 的 switch 禁令仍适用。
- 交给用户应用前，完成选项求值、完整 `system.build.toplevel` 和 `home.activationPackage` 构建；涉及服务时核对产物中的 `ExecStart`、用户/组、内核模块及 udev 规则。只构建单个包不足以证明可应用。
- `home.packages` 必须使用目录产物，如 `writePython3Bin`；保留 HM 的 `hm-backup` 备份设置，并从系统服务环境确认 `HOME_MANAGER_BACKUP_EXT`。
- 设备守护进程优先使用系统服务，显式设置 `User`、`SupplementaryGroups`；不能依赖已登录会话或 linger 用户管理器刷新组。`uaccess` 规则必须早于 `73-seat-late.rules`。
- evdev 脚本显式处理 `UInputError`，先成功创建虚拟设备，再 grab 真实设备。
- 静态开发配置由 Nix 单向管理；MIME、输入法等运行时动态配置使用 `force = true`。合法 GUI 增量通过 `scripts/sync-mimeapps.py --apply` 反哺，不在 switch 时静默抹除。
- MIME 基线：`liu-bigpc` 的 HTTP/HTTPS/HTML/XHTML 使用 `tag-browser.desktop`，其他主机保留既定浏览器；magnet/bittorrent 使用 qBittorrent，codex 使用 `chatgpt.desktop`，baiduyunguanjia 使用 `baidunetdisk.desktop`。禁止外部应用劫持。

## 部署与验收

- NUC `dufs-lan` 为认证读写，NUC `dufs` 为密码只读，Aliyun 为匿名只读。认证、写拦截和只读挂载由部署配置保障，不能依赖 public 构建或隐藏 UI。
- `frontend` 构建并发布静态前端；`tag-server` 构建、传输和激活后端镜像；`infra` 发布基础设施和非密钥配置；`runtime-images` 只传基础镜像，不切换容器。
- DUFS 官方镜像标签是 `v0.46.0`。Docker/Podman 镜像 ID 不一致时，校验实际导出配置字节的 Config Digest，不跳过校验、不只比较版本字符串。
- 备份、生产验收按 [production-verification.md](deploy/docs/production-verification.md)；部署后检查 Compose 联动代理是否恢复。发布不是多组件原子事务，镜像回滚不代表数据库、前端或站点整体恢复。
- 保护 `bevy-sketch`、`bevy-game`、`project-planner` 独立目录，不覆盖个人资料、其他工程或 xiaoqiang 专用目录。
- tag-all 023 完整 Nix 私有镜像仅用于 NUC 的 tag-server/all：先以 `--tag-packaging nix --dry-run` 预演，再由发布器调用 PC `just build-nix private`。保留完整 tester/private 验收，禁止发布 020–022 检查镜像。固定归档、标签、SHA256、配置摘要和探针报告；不导入或清理 PC 默认 Podman。备份后激活并验收全部目标，失败逐项尝试恢复，不自动恢复数据库等数据。
- 原生组合候选遵循 [016 契约](specs/016-application-release-bundle/contracts/bundle.md)：`just native-bundle-create` → `just check-native-bundle` → `just native-bundle <pc|nuc> ...` 预演。隔离检查显式使用已有 `NODE_PATH`、`CHROMIUM_PATH`，不下载浏览器或读取日常 profile。`--prepare` 不代表激活授权；组件或验收器变化需重建重验。旧 `native-release` 仅用于既有流程/恢复。

## SSH 与沙箱

- 禁止跳过 SSH 主机密钥校验。
- DSH 中若报 store 下 `ssh_config.d` 属主错误，使用 `ssh -F ~/.ssh/config`；rsync 使用 `-e "ssh -F $HOME/.ssh/config"`。不要修改用户 SSH 配置。
- `sync-todos`、部署等可用临时 PATH 包装器为 ssh 添加 `-F`，仍调用原发布器。SSH/rsync 串行并留间隔；失败按 `1.5 × 尝试次数` 秒退避重试，不并行传输。

## 规格与进度

- 本仓代码与 `specs/` 是权威源；产品规格留在所属产品。clipboard-sync 的规格例外集中于本仓 `005/006/007`，子模块代码、Git 和构建仍独立。
- 状态变化后按共享 work-progress 更新相关任务和 `specs/README.md`，只提交当前任务文件，保留无关工作树改动。
- `just sync-todos` 先预演再发布，并核验 checksum；只写中央登记的 `/home/liou/dufs-lan/projects/nix-tools.md` 和共享索引 `README.md`。
- 不全量上传 specs/docs/规则，不使用 `--delete`，不恢复旧 `todos/a-next.md`、`a-observe.md`、`a-done.md` 或平行计划，不向 xiaoqiang 专用 `/home/liou/dufs/` 重建本工程文档。
- 阶段交还时按对应 `tasks.md` 报告阶段名称、剩余步骤数量、名称及下一步；完成则明确剩余 0 项。

## 磁盘清理边界

- 清理前确认所属文件系统、实际用途、打开文件、活跃构建及是否存在其他副本；不按目录名猜用途。先用 `df`、`du -x` 逐层定位，再检查 `lsof` 和进程。
- 只处理获授权且已确认可重建的候选。保护源码、个人文件、聊天记录、签名/固件/发布包、唯一备份；不默认清空回收站、日志、系统历史代或整批 `/tmp`。
- 插件 staging 仅清理超过保留期且无占用的候选，保留正式安装与近期目录；只对已确认候选恢复写权限。
- Podman 先检查 `ps -a --external` 及活跃构建；仅清确认闲置的 Storage/PID0 working-container，再按需 `podman image prune -f`。禁止直接 `system prune -a`、container prune、卷清理或 migrate/reset。
- 保留 SSD201/RK3506 交叉编译镜像（含 sip validation 别名）、生产基础镜像、tag-server public/private 和全部现有服务容器；清理前后核对标签/ID及容器状态。受限时使用已有宿主 Podman socket。
- 过程审计留本机，总纲只记录必要结果；不向 AGENTS.md 或本指南追加清理日志，也不另建重复的清理流水文档。
