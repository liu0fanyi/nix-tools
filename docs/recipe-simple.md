# 精简菜谱：AI 字幕、材料、做法与原封面

推荐入口是 `scripts/recipe-simple`。它使用独立数据目录，先取 B 站 `ai-zh` 字幕和原封面，仅做一次 AI 文本整理，再生成 HTML、JSON 与食材搜索目录。不下载视频、不 OCR、不生成步骤片段，不做独立文本或视觉复审。旧 `recipe-flow` 和旧视频保持可用，不原地迁移。要求与验收见[精简契约](../specs/010-host-configuration/contracts/video-recipe-simple.md)。

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
