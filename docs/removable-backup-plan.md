# 可移除 U 盘关键数据轮换备份计划

## 目标

在主机、电源或系统突然故障时，可以直接拔下 U 盘，在另一台机器上读取关键文件并继续工作。

首期只备份不可轻易重新生成的数据：

- Git 工程中已跟踪的文件，以及未被 `.gitignore` 忽略的未跟踪文件；
- 尚未推送的 Git commit、branch 和 tag；
- Zen Browser 的 Spaces、Folders、固定标签页和容器配置；
- 后续显式加入白名单的文档或小型配置目录。

不备份构建产物、依赖缓存、下载缓存、媒体缓存等可重新生成的数据。

## 总体方案

准备两个约 180 GB 的 U 盘，按文件系统 UUID 识别并挂载到稳定路径：

```text
/mnt/backup-a
/mnt/backup-b
```

采用轮换方式：

- 一个 U 盘可以连接主机，接受定时或手动备份；
- 另一个完成备份后安全卸载，作为离线副本；
- 每周或每月交换两个 U 盘；
- 两个盘都保存可独立恢复的完整副本，不使用 RAID 或纠删码拆分数据。

后台任务由 systemd user service 和 timer 驱动。任务发现没有目标 U 盘时正常退出，不把“盘未插入”视为错误。

## U 盘目录布局

每个盘使用相同布局：

```text
critical-backup/
├── current/
│   ├── projects/
│   ├── zen/
│   └── files/
├── history/
│   ├── projects/
│   └── zen/
├── git-bundles/
├── manifests/
└── logs/
```

- `current`：可直接浏览和复制的最新文件；
- `history`：被覆盖或删除前的旧版本；
- `git-bundles`：每个 Git 仓库的完整引用备份；
- `manifests`：备份时间、源路径、目标 UUID、校验结果和工具版本；
- `logs`：每次运行的简短日志。

U 盘应使用 Linux 权限和符号链接语义完整的文件系统（优先 ext4）。若必须兼容 Windows，可使用 exFAT，但需要接受权限、符号链接和文件名语义不完整，并在实现时采用兼容策略。

## 工程文件选择

不能直接把 `.gitignore` 作为 `rsync --exclude-from` 使用，因为 rsync 与 Git 的忽略规则并不完全相同，尤其是嵌套 `.gitignore` 和否定规则。

由 Git 生成准确文件清单：

```bash
git -C "$repo" ls-files \
  --cached \
  --others \
  --exclude-standard \
  -z
```

再交给 rsync：

```bash
git -C "$repo" ls-files \
  --cached \
  --others \
  --exclude-standard \
  -z |
rsync -a --from0 --files-from=- "$repo/" "$destination/"
```

该清单包括：

- 所有已跟踪文件；
- 未被 Git 忽略的未跟踪文件；
- 已跟踪但后来匹配 `.gitignore` 的文件。

它不会包含 `.git` 目录。为保存尚未推送的提交和引用，每个仓库另行生成 bundle：

```bash
git -C "$repo" bundle create "$bundle_path" --all
```

实现时还需处理：

- Git submodule：递归发现并分别备份工作区和 bundle；
- 非 Git 目录：必须显式加入普通文件白名单，不自动备份整个父目录；
- 文件名中的换行和特殊字符：全程使用 NUL 分隔；
- 运行期间文件变化：记录 rsync 返回值，并在失败时保留上一个有效版本；
- bundle 生成失败：不得用空文件覆盖上一次成功的 bundle。

## 版本保留与删除策略

首版不直接使用无保护的 `rsync --delete`。

建议行为：

1. 新文件和变化文件同步到 `current`；
2. 被覆盖或从源端消失的旧文件移动到带时间戳的 `history`；
3. 仅在一次同步完整成功后更新 manifest；
4. 历史版本按保留策略清理，而不是立即删除。

初始保留建议：

- 最近 24 小时内每次成功备份；
- 最近 30 天每天一个版本；
- 最近 12 个月每月一个版本；
- 清理前检查目标 UUID，禁止对未知路径执行递归删除。

如果 exFAT 上实现历史快照过于复杂，首版可采用“当前镜像 + 覆盖前文件归档”，不依赖硬链接。

## Zen Browser 备份

当前 NixOS 主机的 Zen Profile 是：

```text
/home/liou/.config/zen/2hhzc29e.Default Profile
```

首期备份：

```text
zen-sessions.jsonlz4
containers.json
```

规则：

- Zen 运行时跳过会话备份，不强制关闭浏览器；
- Zen 完全退出后才复制，因为退出过程会写回最终会话状态；
- 每次更新 `current/zen` 前保留上一版到 `history/zen`；
- 不在两台机器上自动双向合并，导入和导出必须是明确的 push/pull 操作；
- 恢复前自动备份目标机器原有文件；
- 两台机器尽量使用相同 Zen 版本。

Windows 端后续提供独立 PowerShell 脚本，通过 `about:support` 确认实际 Profile 路径，不硬编码用户名。脚本同样需要确认 Zen 进程已经退出。

## systemd 任务设计

计划增加：

```text
critical-backup.service
critical-backup.timer
```

建议 timer 每 15 或 30 分钟触发一次，并带随机延迟，避免固定时刻与其他磁盘任务竞争。

service 需要满足：

- `Type=oneshot`；
- 使用 `flock` 或 systemd 的单实例语义防止任务重叠；
- 设置适度的 I/O 和 CPU 调度优先级，避免明显影响交互和大文件传输；
- 仅允许写入已验证 UUID 对应的备份根目录；
- U 盘未挂载、只读或剩余空间不足时安全退出并记录原因；
- 不自动挂载未知设备；
- 休眠或关机时不强行延长系统停止过程；
- 可通过 `systemctl --user start critical-backup.service` 手动触发。

配置应允许声明：

```nix
backupTargets = [
  {
    uuid = "待填写";
    mountPoint = "/mnt/backup-a";
  }
  {
    uuid = "待填写";
    mountPoint = "/mnt/backup-b";
  }
];

gitRepositories = [
  # "/home/liou/project/example"
];

plainPaths = [
  # "/home/liou/Documents/important"
];
```

具体 UUID 和源目录在实施前通过只读命令确认，不在计划阶段猜测。

## 命令行接口

计划提供统一命令：

```text
backup-critical status
backup-critical run
backup-critical run /mnt/backup-a
backup-critical verify /mnt/backup-a
backup-critical list-history
backup-critical restore-project <project> <destination>
backup-critical zen-push <shared-directory>
backup-critical zen-pull <shared-directory>
```

`status` 至少显示：

- 当前识别到的目标盘和 UUID；
- 最近一次成功、失败或跳过时间；
- 最近一次 manifest；
- 剩余空间；
- Zen 是否因仍在运行而被跳过；
- Git bundle 是否通过验证。

## 完整性校验

每次备份至少检查：

- rsync 返回码；
- Git bundle 使用 `git bundle verify`；
- 关键 Zen 文件存在、大小非零且成功复制；
- manifest 原子写入，不能留下代表“成功”的半成品记录。

定期运行完整校验：

- 对关键小文件保存 BLAKE3 或 SHA-256；
- 每月读取并验证两个 U 盘；
- 每季度进行一次实际恢复演练，而不只检查文件存在；
- 发现损坏时从另一 U 盘修复，但先保存损坏样本和日志。

## 恢复流程

### Git 工程

1. 从 `git-bundles/<project>.bundle` 克隆仓库；
2. 将 `current/projects/<project>` 覆盖到新工作区；
3. 检查未提交和未跟踪文件；
4. 单独恢复 submodule；
5. 运行项目自己的依赖安装或构建步骤，重建被忽略内容。

### Zen Spaces

1. 安装与来源尽量一致的 Zen 版本并启动一次；
2. 使用 `about:support` 确认目标 Profile；
3. 完全退出 Zen；
4. 备份目标的 `zen-sessions.jsonlz4` 和 `containers.json`；
5. 从 U 盘复制文件；
6. 启动 Zen 并检查 Spaces、Folders、固定标签页和容器；
7. 恢复异常时退回导入前备份。

## 实施阶段

### 阶段 1：只读盘识别与手动备份

- 确认两个 U 盘的 UUID、文件系统和健康状况；
- 确定需要备份的 Git 仓库和普通路径白名单；
- 实现 `status` 和手动 `run`；
- 默认不删除目标端文件；
- 完成一次临时目录恢复测试。

### 阶段 2：历史版本与校验

- 加入覆盖前归档和保留策略；
- 加入 bundle 校验、文件校验和 manifest；
- 验证 U 盘空间不足和意外拔盘时不会破坏上一个有效备份。

### 阶段 3：systemd 定时运行

- 添加 user service 和 timer；
- 设置低 I/O 优先级和任务锁；
- 验证 U 盘未插入时安静退出；
- 验证不影响现有 rsync、大文件复制和系统关机。

### 阶段 4：Windows Zen 中转

- 编写 PowerShell push/pull 脚本；
- 使用共享硬盘、SMB 或将来的 Syncthing 中转目录；
- 中转目录与活动 Profile 分离；
- 验证 Windows 到 Linux、Linux 到 Windows 的恢复和回滚。

## 验收标准

- 主机不可启动时，U 盘可在另一台机器上直接读取 `current`；
- 任一 U 盘单独存在即可恢复关键数据；
- `.gitignore` 内容不会进入工程工作区镜像，但已跟踪文件不会被遗漏；
- 未推送 Git 引用可通过 bundle 恢复；
- 未提交且未被忽略的文件可恢复；
- Zen 运行时不会复制可能被退出写回覆盖的会话文件；
- 源文件误删或覆盖后，至少能从历史目录恢复一个旧版本；
- U 盘缺失、只读、空间不足或同步中被拔出时，不破坏上一次有效备份；
- 所有清理操作都只能作用于经过 UUID 验证的明确目标目录。

## 暂不包含

- 自动同步完整 Zen Profile；
- 两台机器同时修改后的 Zen Spaces 自动合并；
- 把两个 U 盘组成 RAID；
- 大型可重新下载媒体库；
- 未经白名单确认的整个 Home 目录镜像；
- 将 U 盘副本视为唯一备份。
