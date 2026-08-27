# dufs-plus 媒体路径身份

## 当前两块硬盘

| 逻辑路径 | 当前宿主挂载点 | 文件系统 | UUID |
| --- | --- | --- | --- |
| `media/Art` | `/media/liou/Art` | exFAT | `5F82-B190` |
| `media/project` | `/media/liou/project` | ext4 | `8bce6197-7281-40a0-84ec-e31c3d313877` |

容器将 `/home/liou/dufs-lan` 挂载为 `/workspace`，并将宿主的
`/media/liou` 覆盖挂载为 `/workspace/media`。持久关系应保存工作区相对路径，
例如 `media/Art/book/a.pdf`，不能保存 `/media/liou/...` 或 `/workspace/...`。

## 2026-08-24 审计结果

* `tag_all.db` 的 2795 条 `items.path` 中没有宿主绝对路径、容器绝对路径或
  前导 `/`。其中 2383 条属于 `media/Art/...`，24 条属于
  `media/My Passport/...`。这 24 条是格式化前的历史路径；新盘路径为
  `media/project/...`。
* 标签和笔记最终都关联 `items.id`。dufs-plus 内部移动会在同一事务中改写
  整个路径子树，并保留标签和笔记关系。
* 文件旁边的 `.tag`、阅读进度和 PDF/EPUB 分析目录不保存宿主挂载前缀；
  它们跟着源文件一起移动时不受硬盘卷标影响。
* 漫画 manifest 保存工作区相对 `source_path`，路径变化后属于可重新生成的
  缓存，不是唯一数据。
* `dufs-media-progress.json` 仍包含旧版 `/media/Art/...` 键，但当前代码已经不再
  读取该文件；它是历史数据，不作为现行关系来源。
* 浏览器最近目录、阅读缓存等可能以 URL 路径为键。挂载路径变化后它们会成为
  无害的旧缓存，但不能用于恢复服务器关系。
* Bevy Sketch 画板中的外部图片、视频和绘画来源使用 Web 根相对路径，例如
  `/media/Art/...`。这不是宿主绝对路径，但硬盘挂载目录改名仍会使引用失效。

## 结论与操作边界

硬盘自身的稳定身份是 UUID，不应让可修改的 exFAT 卷标决定应用路径。
运行 `scripts/install-dufs-media-mounts.sh` 后，系统通过 UUID 将两块盘固定到现有
目录；以后修改卷标不会改变 dufs-plus 中的逻辑路径，也无需批量重写数据库或
画板文件。

脚本只原子更新 `/etc/fstab`，不会卸载或重挂载正在使用的磁盘。应先完成或停止
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
