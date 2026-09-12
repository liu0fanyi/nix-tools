# dufs-plus 媒体路径身份

## 当前两块硬盘

| 逻辑路径 | 当前宿主挂载点 | 文件系统 | UUID |
| --- | --- | --- | --- |
| `media/Art` | `/media/liou/Art` | exFAT | `5F82-B190` |
| `media/project` | `/media/liou/project` | ext4 | `8bce6197-7281-40a0-84ec-e31c3d313877` |

容器将 `/home/liou/dufs-lan` 挂载为 `/workspace`，并将宿主的
`/media/liou` 覆盖挂载为 `/workspace/media`。持久关系应保存工作区相对路径，
例如 `media/Art/book/a.pdf`，不能保存 `/media/liou/...` 或 `/workspace/...`。

## 结论与操作边界

硬盘自身的稳定身份是 UUID，不应让可修改的 exFAT 卷标决定应用路径。
非 NixOS 主机运行 `scripts/install-dufs-media-mounts.sh` 后，系统通过 UUID 将两块盘固定到现有
目录；以后修改卷标不会改变 dufs-plus 中的逻辑路径，也无需批量重写数据库或
画板文件。

NUC NixOS 通过声明式 UUID 挂载，不再用此脚本修改 fstab。其他适用主机上，脚本只原子更新 `/etc/fstab`，不会卸载或重挂载正在使用的磁盘。应先完成或停止
视频转换、移动等长任务，再重启系统使配置生效：

```bash
./scripts/install-dufs-media-mounts.sh --dry-run
sudo ./scripts/install-dufs-media-mounts.sh
```

固定挂载解决的是“硬盘改名”。文件或目录本身的位置变化仍遵循以下规则：

* 优先使用 dufs-plus 的移动功能；数据库标签和笔记路径会同步迁移。
* 在系统文件管理器中移动文件时，必须把同名隐藏 `.tag` 和阅读/分析目录一起
  移动。标签可通过旁路文件重新扫描，但笔记 item 关系和画板外部资源引用目前
  不保证自动迁移。
* 缩略图和漫画 manifest 都是可再生缓存，路径变化后允许重新生成，不应为它们
  设计数据迁移。
