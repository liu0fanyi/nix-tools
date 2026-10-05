# 本地视频字幕 OCR

入口为 `scripts/subtitle-ocr`。使用本机 CPU 从画面烧录字幕生成 SRT，不上传视频、音频或识别结果。脚本沿用 flake.lock 的 Nix Python 3.12、FFmpeg、uv 和动态库；Python 依赖与随包中文 PP-OCRv4 模型固定在 `scripts/subtitle-ocr-requirements.txt`。首次运行安装到 `~/.cache/nix-tools/subtitle-ocr/`，后续复用。无需系统 switch；不更新 flake.lock，不改 Home Manager。

## 使用

```bash
# 只列出目标视频，不做 OCR。
/home/liou/nix-tools/scripts/subtitle-ocr "/视频目录" --list

# 处理现有全部视频，自动探测字幕位置。
/home/liou/nix-tools/scripts/subtitle-ocr "/视频目录"

# 每120秒检查一次新下载完成的视频，文件至少稳定30秒才处理。
/home/liou/nix-tools/scripts/subtitle-ocr "/视频目录" --watch

# 同风格烹饪视频的固定底部区域（按分辨率缩放）。
/home/liou/nix-tools/scripts/subtitle-ocr "/视频目录" --profile cooking

# 字幕位置不适合自动探测时，指定归一化 x,y,width,height。
/home/liou/nix-tools/scripts/subtitle-ocr "/视频目录" --crop 0.1,0.78,0.8,0.16

# 前90秒试稿；建议把试稿视频复制到单独目录，避免与完整输出冲突。
/home/liou/nix-tools/scripts/subtitle-ocr "/试稿视频.mkv" --duration 90
```

`--fps` 默认4，即切换时间约0.25秒分辨率；`--threads` 默认4。提高采样率会增加计算量；短于采样间隔的字幕可能漏过。脚本当前识别每张抽样图，不声称已实现仅在字幕变化时调用OCR。下一步可用变化检测减少重复调用，必须单独验证漏字和时间边界。

自动定位在视频六个时间点检测文本，选择位置稳定且文字内容变化的候选行；它不是全视频逐帧位置跟踪。探测失败时使用底部备用区域，报告 `region-not-confirmed`，需要检查或指定 `--crop`。动态漂移字幕、复杂花字、很小的字幕、旋转视频和字幕区域改变都可能需要不同参数。数字及中文数字变化不做模糊合并，避免把“盐2克”和“盐3克”合成一句；只桥接前后文字完全相同的单帧识别闪烁。

## 输出与续跑

每个视频旁输出：

- `<视频名>.ocr.zh-CN.srt`：UTF-8字幕。
- `<视频名>.ocr.json`：来源签名、识别参数、区域、切换时间精度、待检查条目、拒绝的短片段和SRT摘要。
- 目录 `.subtitle-ocr/index.json`：批次状态索引。
- `.subtitle-ocr/work/`：每60秒一块的识别检查点和区域探测记录。

字幕文件不覆盖原视频、已有英文或中文字幕。来源及参数相同、输出摘要一致则跳过；更改参数或源文件后默认报告冲突。`--replace-owned` 仅允许替换本工具生成且未被外部编辑的输出；手工修改的字幕继续保留。中断后重新运行同一命令，复用已完成的60秒检查点，当前未完成块重做。

状态 `done` 表示自动处理完成，不表示人工校对；`review` 表示字幕位置或条目需要检查；`no_subtitles` 表示在识别区域内未识别到可用字幕，不能证明整段视频无字幕；`error` 表示处理失败；`output-conflict` 表示保留既有输出。原始结果保留在检查点，不通过语言猜测自动改写菜名或用量。可提供 `--corrections 字典.json`，只替换完全匹配的整条文字，并留下标记。

磁盘可用空间低于5 GiB时暂停该视频；监测模式10分钟后重试错误。处理同一目录使用独占锁；默认忽略隐藏目录、`OCR样稿`、符号链接和非最终视频扩展名，`.part` 不会处理。SIGINT中断保留检查点，不执行清理或删除视频。

## 当前 Bilibili 批次

对象目录是 `/home/liou/Downloads/Bilibili/老东北美食 [514273130]`。视频下载与OCR是两个独立用户临时服务，均不随聊天关闭而停止；重启后需重新启动，不承诺永久自启。

```bash
systemctl --user status bilibili-514273130-download.service
systemctl --user status bilibili-514273130-ocr.service
systemctl --user stop bilibili-514273130-ocr.service
```

OCR日志在目标目录 `ocr.log`。重新启动OCR可直接运行以上 `--watch` 命令；当前临时服务仍加载时也可用 `systemctl --user start bilibili-514273130-ocr.service`。下载服务先收集/穿插下载视频，OCR只处理落盘稳定的视频，不请求B站接口，不读取浏览器Cookie。

## 验证与限制

检查短管道读取、RGB裁剪尺寸、数值变化、单帧闪烁、符号链接和未稳定文件；用真实视频片段、移动到顶部的字幕及无字幕视频验证自动定位与状态；检查续跑跳过和外部编辑保护。用户认可的前90秒样稿包含人工校正，批量自动输出不会冒称达到相同人工校对程度。

上游：[RapidOCR](https://github.com/RapidAI/RapidOCR)、[FFmpeg 滤镜文档](https://ffmpeg.org/ffmpeg-filters.html)。Python包属于正常包管理依赖，未引入外部Git参考仓库或原始文档。
