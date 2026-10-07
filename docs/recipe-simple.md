# 精简菜谱：AI 字幕、材料、做法与原封面

推荐入口是 `scripts/recipe-simple`。它使用独立数据目录，先取 B 站 `ai-zh` 字幕和原封面，仅做一次 AI 文本整理，再生成 HTML、JSON 与食材搜索目录。不下载视频、不 OCR、不生成步骤片段，不做独立文本或视觉复审。旧 `recipe-flow` 仍可使用；精简入口不原地迁移或自动删除旧数据。已有原视频可按用户明确指令单独清理。要求与验收见[精简契约](../specs/010-host-configuration/contracts/video-recipe-simple.md)。

## 一次处理与续跑

```bash
SIMPLE=/home/liou/nix-tools/scripts/recipe-simple
RECIPE_ROOT=/home/liou/Downloads/菜谱精简流程
"$SIMPLE" --root "$RECIPE_ROOT" init --browser 'firefox:/实际/Zen/profile'
"$SIMPLE" --root "$RECIPE_ROOT" add /实际/待处理清单.json
"$SIMPLE" --root "$RECIPE_ROOT" next
"$SIMPLE" --root "$RECIPE_ROOT" status
```

清单为非空数组，每项仅 `id/title/author`；也可使用已有平面播放列表的 `entries`。不接受视频路径、外部字幕或旧菜谱种子。

```json
[{"id":"BV13beA6SEh9","title":"肉末蛏子盖饭","author":"老东北美食"}]
```

`next` 最多准备一项，缺中文 AI 字幕记为 `skipped`；登录、风控、网络或封面错误记为 `failed`，使用 `retry --job BV号` 后再次 `next`。等待 AI 时状态为 `waiting_extract`，状态输出给出完整任务包位置。重新执行复用字幕/封面和绑定输入，不重复下载。网络请求保留既有低频设置；本入口没有批量下载的视频名额限制。

让当前 Codex 会话完整读取任务包，按其中 prompt/schema 做一次文本整理，返回五字段信封：`task_id/input_sha256/processor/model/result`，保存为私有 JSON，再导入：

```bash
"$SIMPLE" --root "$RECIPE_ROOT" import /实际/整理回复.json
"$SIMPLE" --root "$RECIPE_ROOT" next
```

程序验证 Schema、真实字幕编号、时间顺序、字幕/封面摘要及输入绑定，不再让另一个 AI 复审。时间范围由程序根据引用的字幕计算。用量不明确时 `null`，识别不清保留 notes；页面标记“AI 字幕整理”，不是人工核验。当前仍需要会话执行 AI 整理，不宣称无人值守模型服务已接通，也不代表已经处理四千条。

`simple.sqlite3` 仅记录进度。断开会话、重启进程后仍可用 `status/next` 继续；单写者锁保护重复进程。材料原名与可选项入索引，沿用现有食材别名词典。网页搜索使用 JSON，SQLite 不对浏览器暴露。

## 查看页面

```bash
"$SIMPLE" --root "$RECIPE_ROOT" serve --port 8765
# 丢失网页时重新生成；不下载视频，也不重新调用 AI：
"$SIMPLE" --root "$RECIPE_ROOT" rebuild
```

在浏览器打开 `http://127.0.0.1:8765/index.html`。页面仅有材料、制作步骤、原视频封面和链接。步骤时间是原视频位置，不是做菜时长。本地服务只提供 `library/`，不提供 Cookie、数据库、原始平台信息或 AI 任务包。

## 原视频按住播放实验脚本

目录里的“原视频键盘浏览脚本”和“使用方法”提供 `scripts/bilibili-recipe-controls.user.js` 与安装说明。在 Zen 中由用户选择用户脚本管理器并安装，Agent 不修改真实浏览器 profile。脚本仅作用于 B 站原视频页，不代理视频流。

默认暂停，按住空格按所选速度播放，松开停止；失焦、切换标签页也停。−/+ 与选择框支持 0.25×–4×；S 暂停后请求下载 PNG，输入框内不抢键。截图受 canvas 跨域限制时明确提示失败，可以使用系统截图。

新版 0.2.0 已实现 ← 上一帧、→ 下一帧。安装或更新后必须刷新原视频页，再等面板出现“真实邻帧 · 已索引 N 帧”。脚本使用 `document-start` 和 `page` 注入，需在播放器创建媒体缓冲前运行；推荐使用 [Violentmonkey 官方 Firefox 入口](https://violentmonkey.github.io/get-it/)，不要将脚本改为 content 注入。[官方注入说明](https://violentmonkey.github.io/api/metadata-block/#inject-into)解释了早期运行的条件和限制。其他管理器须确认页面上下文和足够早的执行时机，尚未逐一验证。

帧位置来自播放器正常追加到 MediaSource/SourceBuffer 的分片 MP4 时间表，按照实际呈现顺序处理 B 帧和变帧率，定位到相邻帧的呈现区间并等待 seeked/画面呈现后完成。不会用 1/25 或 1/30 秒猜帧，也不额外发起媒体请求。分片中的视频内容被跳过，只在内存保留有限帧时间元数据；实际视频下载/缓冲仍由原站播放器完成。容器结构依据 [W3C ISO BMFF 字节流说明](https://www.w3.org/TR/mse-byte-stream-format-isobmff/)。

支持主页面中可捕获的单视频轨道分片 MP4，包含可变样本时长、B 帧的带符号组合偏移、timestampOffset 和单项 rate=1 的编辑时间表。仅在完整索引及实际缓冲范围内提供邻帧操作；不跨缺失分片猜邻帧。元数据错误、解码超时、定位被平台改写时明确报错，通常保留／恢复暂停位置。失焦、切换视频或退出模式时取消正在进行的逐帧操作。松开播放键先立即暂停，再将位置稳定到时间表中邻近的真实帧并等待呈现，避免 Zen 停住画面与播放时间差一帧；稳定期间不排队执行新操作。

Worker 中的媒体缓冲、非 MP4/直接文件播放、sequence 时间轴、裁剪缓冲窗口和复杂编辑表暂不支持精确逐帧，按住播放与调速仍可用。截图受站点跨域策略限制时提示失败，不会报告保存成功。真实 B 站页面和用户脚本管理器的组合仍需安装后试用；合成媒体程序验证不冒称真实站点兼容确认。

## 可重复验证

在入口建立的 Python 环境中运行：

```bash
python -m unittest discover -s scripts/tests -p test_recipe_simple.py -v
node scripts/tests/test_recipe_ingredient_search.cjs
node --test scripts/tests/test_recipe_frame_index.cjs
python scripts/tests/check_recipe_player_zen.py --output /tmp/recipe-player-check
python scripts/tests/check_recipe_frame_zen.py --output /tmp/recipe-frame-check
```

两个浏览器检查只打开临时 Zen profile、使用本地合成视频，输出 report.json、截图和日志到指定目录；不读取真实 profile 或 Cookie。要求本机已有 Zen、Node、ffmpeg，以及入口环境的 Pillow。输出目录每次用新路径，避免旧截图误判。按住检查覆盖默认暂停、松键/失焦暂停、0.25× 慢放、输入不抢键、无索引拒绝伪逐帧、截图落盘、跨域失败及恢复原控制。帧检查对恒定/变帧率、时间偏移和带符号 B 帧偏移的流，逐一用浏览器显示图片匹配独立 ffmpeg 解码帧，核验前后单帧及按住播放后暂停的衔接；不能仅验证 currentTime 改变。


## 十道精简样稿

2026-10-07 的十道样稿数据在 `/home/liou/Downloads/菜谱精简试验-10道-20261007`，本任务本地预览为 `http://127.0.0.1:8765/index.html`。目录提供食材搜索、同名食材别名及可选食材筛选，菜谱只有原封面、材料、步骤和原视频时间链接。字幕未明确用量显示“未明确”，疑点保留在说明中。该轮十份均来自平台AI字幕重新整理，未下载视频或复用旧OCR菜谱。

查看进度：

```bash
/home/liou/nix-tools/scripts/recipe-simple --root /home/liou/Downloads/菜谱精简试验-10道-20261007 status
```

本地服务退出后重启：

```bash
/home/liou/nix-tools/scripts/recipe-simple --root /home/liou/Downloads/菜谱精简试验-10道-20261007 serve --port 8765
```

原视频删除仅针对这轮用户明确授权的账号原下载和四份试验输入副本，逐文件审计留样稿ROOT；既有字幕和旧菜谱保留。试验结果及验收计数以[阶段T任务](../specs/010-host-configuration/tasks.md)为准，完整模型服务无人值守及全库执行不包含在这轮十道验收。


## 全量库与低频采集

全量ROOT为`/home/liou/Downloads/菜谱精简库-老东北美食`，已有清单4159条，继承已完成十道，预览仍为`http://127.0.0.1:8765/index.html`。

```bash
/home/liou/nix-tools/scripts/recipe-simple --root /home/liou/Downloads/菜谱精简库-老东北美食 status
tail -f /home/liou/Downloads/菜谱精简库-老东北美食/采集.log
```

状态分别显示published菜谱、waiting_extract待AI整理、queued待采集、skipped无字幕、failed错误。后台只采集字幕/封面，最多准备十份待AI字幕，每个视频之间再等一分钟；当前会话导入AI结果后才腾出槽继续取下一条。退出会话后，采集达到上限会等待，不会自行生成四千道菜谱。

停止采集（当前请求结束后退出）：

```bash
touch /home/liou/Downloads/菜谱精简库-老东北美食/collect.stop
```

续跑（先确认旧采集已退出；重复运行会被锁拒绝）：

```bash
rm -f /home/liou/Downloads/菜谱精简库-老东北美食/collect.stop
/home/liou/nix-tools/scripts/recipe-simple --root /home/liou/Downloads/菜谱精简库-老东北美食 collect --max-pending 10 --interval 60 --watch
```

采集遇错记failed并退出，不自动重复请求。查明网络/登录/风控问题后可对对应BV ID执行已有retry命令，再继续collect；缺字幕不会进入AI阶段。sources_finished只是所有排队来源已处理，不代表全部菜谱发布。


## 网页进度条

打开 `http://127.0.0.1:8765/progress.html`，或点击菜谱目录的“处理进度”。页面每5秒自动更新，也可手动刷新。

- “已生成菜谱”只计published。
- “来源处理进度”计已生成、待AI整理和无字幕跳过；失败仍需处理。
- 五个状态卡显示已生成、待AI、待采集、跳过、失败。
- 采集器达到十份待AI上限时显示“等待AI整理”；菜谱发布释放容量后继续采集。

页面读取实际SQLite汇总，采集运行状态由真实文件锁确认；连接失败显示上次数据与提示，不显示虚假完成。全量AI整理仍需活动会话，进度页不触发模型或下载。

若已生成数量不动且待AI为10，先看采集状态：`waiting_for_ai` 表示来源缓存已满，采集器正常等待。当前没有后台AI消费者；仅保持会话窗口或网页打开不会触发整理，必须由会话实际产生并导入结果。不得将后台采集运行当作全流程持续运行。
