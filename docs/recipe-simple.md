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

**精确相邻帧仍待实现。** 当前 Zen 的隔离测试中 `seekToNextFrame` 是 undefined。脚本不采用固定秒跳转伪装逐帧，← 不可用，→ 仅在浏览器确实提供原生接口时调用该接口。默认浏览器的真实逐帧需求仍记录在阶段 S 的 S3 中；按住播放原型不算这一项完成。真实 B 站页面兼容性也需实际试用，不能用合成媒体测试代替。

## 可重复验证

在入口建立的 Python 环境中运行：

```bash
python -m unittest discover -s scripts/tests -p test_recipe_simple.py -v
node scripts/tests/test_recipe_ingredient_search.cjs
python scripts/tests/check_recipe_player_zen.py --output /tmp/recipe-player-check
```

最后一个检查只打开临时 Zen profile、使用本地合成视频，输出 report.json、截图和日志到指定目录；不读取真实 profile 或 Cookie。要求本机已有 Zen 和 ffmpeg。输出目录每次用新的路径，避免上次截图误判本次结果。测试验证默认暂停、按住播放、松键暂停、0.25× 慢放、失焦暂停、输入框不抢键、无伪逐帧、截图实际落盘及关闭模式后恢复原播放控制。
