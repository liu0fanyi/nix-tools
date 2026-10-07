# 串行生成菜谱与释放视频

现在仅需要材料、做法与原封面时，使用[精简菜谱入口](recipe-simple.md)。本文是保留视频／片段与复审的原流程说明，不是精简流程。

`scripts/recipe-flow` 把大清单登记、单视频准备、AI任务包、归档、网页目录及视频释放接成可续跑流程。状态使用本地SQLite；网页检索使用内嵌JSON，可直接打开离线目录。字段与验收规则以[010规格](../specs/010-host-configuration/spec.md#串行处理与视频释放)、[菜谱契约](../specs/010-host-configuration/contracts/video-recipe.md)和[食材契约](../specs/010-host-configuration/contracts/video-recipe-ingredients.md)为准。

## 当前默认：只获取 B 站中文 AI 字幕

先获取 `ai-zh` 字幕，成功后才下载视频并处理。没有中文 AI 字幕的标记 `skipped`，不下载视频、不运行 OCR、不生成菜谱任务；已有视频保留。登录/风控/网络错误和损坏的字幕标记 `failed`，用 `retry --job BV号` 重试，避免误跳过。有人工字幕、英文字幕或弹幕也不替代中文 AI 轨道。

新 ROOT 的 CLI 默认 `--subtitle-policy bilibili-ai-only --media-mode clips`。旧流程配置固定，应新建目录切换；旧目录仍能查看和续跑，独立 OCR 工具保留。新入口不加载 OCR 运行环境或模型。AI 字幕仍可能误识别食材和数字，全文文字复审及疑点处理保留，字幕不会自动认证菜谱。

```bash
FLOW=/home/liou/nix-tools/scripts/recipe-flow
FLOW_ROOT='/home/liou/Downloads/菜谱AI字幕流程'
"$FLOW" --root "$FLOW_ROOT" init --subtitle-policy bilibili-ai-only \
  --media-mode clips --browser 'firefox:/实际/Zen/profile'
"$FLOW" --root "$FLOW_ROOT" add /实际/待处理清单.json
"$FLOW" --root "$FLOW_ROOT" run --watch
# 另一终端只读查看：
"$FLOW" --root "$FLOW_ROOT" status --summary
```

清单仅写 `id/title/author`，可加 `video` 复用已有视频；新策略不接受外部字幕、seed 或旧队列 adopt，以免绕过平台 AI 字幕检查。例：

```json
[{"id":"BV13beA6SEh9","title":"肉末蛏子盖饭","author":"老东北美食"}]
```

`ROOT/platform-subtitles/<BV>/result.json` 记录有没有字幕、AI 来源与字幕摘要；字幕和原始平台元数据只保存在私有 ROOT。结果可续跑复用；无字幕条目不会占保留视频名额，也不会在重启后重复探测。正文、独立文字复审 → 步骤 MP4 → HTML/JSON/食材索引 → 手动选图 → 达到原有质量门槛后释放视频。每个 `next` 最多处理一个视频，`run --watch` 自动跨过缺字幕项。

下面旧字幕输入/OCR/adopt 的说明适用于历史目录或显式 legacy，不适用于当前默认 AI-only 新流程。

## 新流程：步骤片段与手动选图

新建CLI流程默认`clips`，保留文字整理、全文复审/修复和食材复核，随后脚本裁剪片段并生成网页，不调用视觉选图或图后复审。每步按证据窗口前后各5秒截取，多个窗口分别生成MP4；时间标签是视频位置，不代表实际烹饪时长。右侧默认视频，图片可选。既有配置不能原地切换；旧图片流程继续使用原目录，新片段流程应新建ROOT。`init --media-mode images`显式创建旧图片模式。

选图保存需启动本地服务：

```bash
"$FLOW" --root "$FLOW_ROOT" serve --port 8765
```

打开`http://127.0.0.1:8765/index.html`。在步骤视频播放/暂停或拖动后点击“选取当前画面”，可选多张、移除、切换视频/图片/两者。重新打开仍保留；“导出选图记录”保存JSON，“导入选图记录”恢复同一菜谱/片段摘要下的选择。截图由本机ffmpeg完成，不调用AI。选择与JPEG保存在ROOT/user-media，不修改验收归档或菜谱文件；迁移整个流程时一并保留该目录。只备份JSON也可由独立片段重新导入生成图片。静态HTML直接打开可以播放，但不能保存选图。

文字/OCR疑点仍保留，选图不算逐项人工烹饪核验。clips允许无图片，释放前必须验证完整独立片段以及原有事实/OCR/文件身份门槛。下面的视觉任务说明和旧实测表适用于images模式，不能当作新片段流程的固定费用。

## 历史兼容：外部字幕与 OCR 清单

在本机终端设置入口和私有数据路径。`FLOW_ROOT` 使用新的流程目录；`BASE` 指向已有视频所在目录，清单中显式填写各视频路径。

```bash
FLOW=/home/liou/nix-tools/scripts/recipe-flow
BASE='/home/liou/Downloads/Bilibili/老东北美食 [514273130]'
FLOW_ROOT="$BASE/菜谱串行流程"
"$FLOW" --root "$FLOW_ROOT" init --subtitle-policy legacy --media-mode clips --media-root "$BASE"
"$FLOW" --root "$FLOW_ROOT" add "$BASE/待处理清单.json"
```

`--media-root` 声明视频所在及允许释放的范围，不自动扫描这个目录。清单没有`video`时才会下载该条视频；未传`--media-root`则新下载使用`FLOW_ROOT/media`。已有视频若未填`video`，流程会重新走下载入口。已提供`subtitles`时不运行OCR；只提供`video`时本地OCR生成全片字幕。初始化配置固定，再次初始化只能使用相同参数。

清单支持非空JSON数组。每条必填`id`、`title`、`author`，可填`video`、`subtitles`、`subtitle_origin`（`ocr`、`platform`或`asr`，默认`ocr`）。字幕路径必须同时有视频路径；相对路径以清单所在目录为基准。同一清单不能重复ID，已经登记的元数据不能静默改写。

```json
[
  {
    "id": "BV17wYF6mE22",
    "title": "红烧牛窝骨",
    "author": "老东北美食",
    "video": "/实际已有视频目录/红烧牛窝骨.mkv",
    "subtitles": "/实际已有视频目录/红烧牛窝骨.ocr.zh-CN.srt",
    "subtitle_origin": "ocr"
  }
]
```

也可传入`yt-dlp --flat-playlist --dump-single-json`生成的播放列表JSON；程序取每条`id/title/uploader`，作者为空时用列表的`uploader`，缺必填元数据会拒绝。4000多条清单只是登记，不触发全量下载。清单枚举本身单独完成，`add`不访问账号空间。

需登录下载且已获Cookie授权时，可在初始化追加以下选项，替换成真实Zen配置目录。Zen使用Firefox的Cookie读取方式，配置只保存浏览器选择器，不记录Cookie值。

```bash
"$FLOW" --root "$FLOW_ROOT" init --subtitle-policy legacy --media-root "$BASE" \
  --browser 'firefox:/实际/Zen/profile'
```

两种初始化示例选其一。新下载是单视频、低频请求及单片段并发，限速2M，文件写入`media-root/<BV号>/`；日志写入`FLOW_ROOT/logs/`。无需读取Cookie的本地处理可省略`--browser`。

## 逐阶段推进

```bash
"$FLOW" --root "$FLOW_ROOT" next
"$FLOW" --root "$FLOW_ROOT" status
"$FLOW" --root "$FLOW_ROOT" export "$FLOW_ROOT/任务包-001"
```

一次`next`至多准备一个视频，并推进它的固定处理阶段；遇到文本整理、独立语义审阅、修复或视觉选图时停在`waiting_*`。`export`把当前待AI任务复制到一个尚不存在的目录，包含不可变`packet.json`、`payload.json`及候选图片。让当前会话的AI子代理按包内stage和契约处理：全文整理保留原文来源；独立审阅逐事实、食材和问题核对；视觉阶段实际查看每张候选图，不靠时间点猜图。

每份AI返回文件必须是五字段信封，任务ID和输入摘要复制当前包，`result`符合对应阶段Schema。`processor`填实际执行者，未知模型标识用`null`。

```json
{
  "task_id": "复制packet中的task_id",
  "input_sha256": "复制packet中的input_sha256",
  "processor": "实际AI执行者",
  "model": null,
  "result": {}
}
```

上例是信封示意，空`result`不可导入。每份完成后顺序导入，再推进下一阶段；一个视觉阶段若导出多包，应完成并逐份导入。

```bash
"$FLOW" --root "$FLOW_ROOT" import /实际/AI返回文件.json
"$FLOW" --root "$FLOW_ROOT" next
"$FLOW" --root "$FLOW_ROOT" export "$FLOW_ROOT/任务包-002"
```

按`next → export → AI → import → next`重复。输入摘要不匹配、任务过期或字段不合约会拒绝导入。当前会话子代理需要会话继续推进；脚本不会在聊天关闭后自行调用AI。完成的阶段输出持久保存，不需再次调用AI。若要独立后台模型，另按模型适配器配置与授权范围接入。

## 自动接收结果的串行broker

需要脚本自动接收会话AI的结果并推进时，可选`run`。单次`run`执行一轮收件和推进；`run --watch`持续等待，默认每10秒检查一次：

```bash
"$FLOW" --root "$FLOW_ROOT" run --watch
"$FLOW" --root "$FLOW_ROOT" status --summary
```

第二条在另一终端只读查看状态摘要。默认任务入口为`FLOW_ROOT/task-packages/current.json`，其中`tasks`给出当前各stage子包的实际目录、任务ID及候选图数量，`response_directory`给出结果收件目录。AI子代理按每个子包的stage独立执行，全文审阅和逐张看图要求仍适用；不能把broker的自动推进当成AI已经完成判断。

AI只向收件目录写返回信封。先在同一目录写不以`.json`结尾的临时文件，完整写完并关闭后，原子rename为`responses/<task_id>.json`，避免脚本读到半份结果。`run --watch`自动导入、推进后续阶段、归档并发布；已接受的响应移入`responses/accepted/`并按内容摘要留审计，不需AI再手动导入。没有变化时静默等待，有新阶段再读取`current.json`。

```bash
"$FLOW" --root "$FLOW_ROOT" run --watch \
  --packets /实际/任务包目录 --responses /实际/结果收件目录 \
  --poll-seconds 10
```

自定义任务包和收件目录应彼此分离，不嵌套，也不进入验收归档、queue、媒体等受保护流程目录。`--poll-seconds`至少1秒。未显式启用`--delete-videos`时不提交新的删除意图；已经承诺的持久释放意图仍按恢复规则继续执行。需要删除时仅在已确认范围内给`run`加该选项。

坏响应会暂停并保留错误：按当前包修正为新的完整内容，或把坏文件移出收件根目录，再运行相同命令；内容不变的已拒绝响应不会反复导入。已合法导入但响应归档失败时，接受状态保留，错误单独记录；处理存储问题后重跑可继续归档和推进。中断后重新执行同一条`run`即可接续持久状态和任务包。

broker运行时持有单写者锁，不要另开CLI执行`import`、`next`或其他写入操作抢锁，AI只写inbox；`status --summary`可并行只读查看。也可继续使用上一节的手动`next/export/import`方案，使用前先停止broker，两种推进方式不要同时运行。broker只做机械收件和阶段推进，不调用AI，仍需要当前会话或另行配置的模型服务执行判断，不意味着云端无人值守。

## 暂停、失败与恢复

```bash
"$FLOW" --root "$FLOW_ROOT" status
"$FLOW" --root "$FLOW_ROOT" resume
"$FLOW" --root "$FLOW_ROOT" retry --job BV17wYF6mE22
"$FLOW" --root "$FLOW_ROOT" next
```

`status`只读显示各项状态、等待任务和错误；下载/OCR详细日志在`logs/`。`resume`修复已验收项的发布、目录及已提交释放意图，不准备新视频，也不自动回答AI任务；继续待办使用`next`，导入仍可使用同一份持久任务包。`retry`仅接受`failed`项，先读错误并处理原因，再恢复该项。未开始的其他条目不会替失败项消除问题。

默认最多保留3个已开始且未释放的视频、至少5GiB可用空间。限制可在首次`init`用`--max-retained`和`--min-free-gib`指定。已开始的失败项也占保留名额；视频仍有开放疑点而不能释放时，达到上限就暂停新项。已开始项可继续推进，但空间不足仍暂停。不要为腾名额删除状态库、审计文件或待回看视频。

已有`recipe-batch`队列中当前版本已完成的菜谱可导入生命周期，不重新跑AI：

```bash
"$FLOW" --root "$FLOW_ROOT" adopt \
  --queue /实际/已完成队列目录 --job BV17wYF6mE22
```

只接受队列状态`complete`及当前装配结果；原视频身份会再次核对，采用后归档并发布。若以后需要释放，原视频路径须位于初始化声明的`media-root`内。

## 修订已归档的待核对菜谱

需要新增食材、独立数字事实或纠正变式关系时，先让AI在完整`recipe.internal.json`副本中制作提案，保留来源、旧ID、旧证据/问题、帧与运行历史。不要直接编辑不可变归档。把实际执行者写入`--processor`，由准备入口转换为待审seed：

```bash
"$FLOW" --root "$FLOW_ROOT" prepare-revision --job BV17wYF6mE22 \
  --proposal /实际/修订提案/recipe.internal.json \
  --output "$FLOW_ROOT/修订seed-新目录" --processor 实际提案执行者
"$FLOW" --root "$FLOW_ROOT" rework --job BV17wYF6mE22 \
  --seed "$FLOW_ROOT/修订seed-新目录"
"$FLOW" --root "$FLOW_ROOT" run --watch
```

准备入口校验所有字幕原文及引用，禁止修改来源、删除旧ID、改写旧证据/问题、伪造帧/运行历史或提升人工状态；新增和内容变更的食材、事实强制`needs_review`，不会采信提案的自认证。 新待审问题使用版本ID，旧问题的状态和解决说明保留；即使提案未改内容也必须独立复审。源、提案摘要与实际执行者进入不可变审计，准备回执明确不代表AI审阅。提案可以收窄步骤`evidence_windows`以围绕`image_goal`抽图；若旧选帧落到新窗外，则取消当前选择并保留待重选缺图问题。真实阶段仍需另一执行者独立全文复审及逐张视觉选图，旧版继续可读。未知量保留未知，不能为消除问题发明数字。

保留原视频的已归档菜谱可通过`rework`建立新revision，重新进行独立语义复审及视觉选图。默认以当前验收归档为起点，也可传入已按相同视频、相同字幕来源准备的修订seed目录：

```bash
"$FLOW" --root "$FLOW_ROOT" rework --job BV17wYF6mE22
"$FLOW" --root "$FLOW_ROOT" next
# 已有修订材料时，以上rework改用：
"$FLOW" --root "$FLOW_ROOT" rework --job BV17wYF6mE22 --seed /实际/修订seed目录
```

两种`rework`示例选其一，之后仍按`export → AI → import → next`推进。新revision使用独立queue、archive和页面路径，不覆盖旧版；复审过程中旧目录记录及旧页面仍可浏览，待新版本完成再更新目录。原视频必须存在且身份、摘要与验收记录一致；已删除视频或已持久提交release intent的条目不能`rework`。`retry`用于失败恢复，`rework`用于已有验收版本的新修订，两者不互相代替。

## 归档、目录与释放

AI阶段完成后，流程把经过校验的装配产物保存到独立的`accepted/<版本键>/`，保留字幕、候选/所选截图、内部JSON、来源证据、审阅结果、OCR报告（适用时）及摘要。发布菜谱页至`library/recipes/<版本键>/`，目录为`library/index.html`，同步生成`search-index.json`和食材词典副本。恢复发布不依赖重做AI。

发布成功不等于视频可以删除。仅`status=ready`、全片覆盖、每步有图、没有开放问题，且OCR来源具备匹配当前媒体与字幕的全片`done`报告、无未处理flags时可释放。OCR报告须有正确`tool`、当前视频`signature`（大小与修改时间）、来源路径及字幕摘要，且不限制处理时长；缺报告、旧报告或绑定不一致均保留视频。`human_reviewed=false`独立记录人工状态：符合上述AI及来源验收后不必等待人工烹饪核验，但不能宣称已人工核验。

```bash
"$FLOW" --root "$FLOW_ROOT" release --job BV17wYF6mE22
```

`release`默认只预演，返回是否符合条件、目标文件及摘要。明确决定删除时才加`--execute`：

```bash
"$FLOW" --root "$FLOW_ROOT" release --job BV17wYF6mE22 --execute
```

`next --delete-videos`或`resume --delete-videos`会对当前所有符合条件的已发布项启用释放，应在已确认范围内使用。释放前校验归档、页面、目录及原视频身份，先持久保存删除意图，再将登记的单个普通视频移动到`video.parent/.recipe-release/<workflow-root摘要前16位>/`专用隔离位置，确保与原视频同盘；每一级新建目录持久fsync，复核身份后删除。隔离位置仍须位于声明的媒体根内。它不删除同名字幕、截图、OCR文件或其他sidecar，也不使用通配/递归删除。

若执行中断，已有持久删除意图会在后续`resume`或`next`中继续完成，即使这次没有再传删除选项；这属于恢复先前明确提交的操作。身份不一致、文件重现或产物被改动时保留文件并报错，不扩大删除范围。

## 无视频重建与全库食材审阅

```bash
"$FLOW" --root "$FLOW_ROOT" rebuild "$BASE/菜谱库-重建新目录"
"$FLOW" --root "$FLOW_ROOT" inventory "$FLOW_ROOT/食材审阅-新批次"
```

`rebuild`从验收归档生成新菜谱库，不需要原视频；输出必须是新目录，不能覆盖旧库。`inventory`从全部验收菜谱生成`inventory.json`、`packet.json`和`dictionary.json`到新目录，覆盖全部不同食材名称供AI复核，不只看未映射项。食材审阅提案需覆盖全名，绑定当前清单及词典摘要，保留真实歧义、原名及稳定ID。AI生成`review.json`后使用专用入口：

```bash
"$FLOW" --root "$FLOW_ROOT" apply-vocabulary \
  --packet "$FLOW_ROOT/食材审阅-新批次" --review /实际/review.json
```

`--packet`传`inventory`生成的目录，不能传其中单独的`packet.json`。程序重建当前全库inventory，与输入清单及摘要/当前词典绑定核对；菜谱或词典已变化的过期提案会拒绝，需重新生成审阅包。校验通过后保存审计记录，更新本workflow的`dictionary.json`、目录JSON及HTML内嵌食材索引。普通`import`只接受菜谱阶段信封，不能导入词典提案。仓库权威`config/recipe/ingredients.json`需由主代理另行统一核验并同步，此命令不会修改它。

清单、原媒体、Cookie相关本地配置和AI私有材料保留在Downloads，不进入Git或文档镜像。仓库只维护工具源码、规范与操作手册；源码提交及文档同步由主代理统一完成。


## 紧凑会话与单视频用量

单视频实测和后续会话执行用`scripts/recipe-session`准备当前阶段视图，再使用不继承旧聊天的执行者（`fork_turns=none`）。文字整理和全文复审保留全部cue、事实、食材及疑点；复审视图去掉运行历史和未引用候选登记，选图只带当前步骤窗口附近cue及前后两条邻句。原包/摘要、原始图片和全部验收仍是权威，不直接编辑它们，也不把视图当新来源。每步最多12张实际候选，不为省token跳过独立复审或逐图查看。语义/修复阶段分别用新执行者；视觉可按步骤用新执行者，避免前面图片持续带入上下文。

```bash
SESSION=/home/liou/nix-tools/scripts/recipe-session
"$FLOW" --root "$FLOW_ROOT" export "$FLOW_ROOT/原任务-新目录"
"$SESSION" --root "$FLOW_ROOT" prepare \
  --packets "$FLOW_ROOT/原任务-新目录" --output "$FLOW_ROOT/会话任务-新目录"
"$SESSION" --root "$FLOW_ROOT" register --stage extract \
  --agent /root/本次新执行者 --task-id 实际任务ID
```

执行者只读对应任务的`instructions.txt/task.json/schema.json`和列出的实际图片，输出原信封到responses；先执行`recipe-session validate --task 任务目录 --response 回复文件`进行不改队列的预检，再由原flow导入/校验后继续。Schema之外的数量模式、字幕原句、覆盖及图像全量评价检查也适用，不能只做jsonschema后直接递送。阶段执行者不能读其他视频、旧菜谱或聊天日志，不能运行队列，也不能直接改词典/发布。修复失败请求也保留并计量，不能通过重开会话掩盖重试消耗。

菜谱发布后先用flow的`inventory`导出全库清单，再`recipe-session prepare-vocabulary --packet 清单目录 --output 新任务目录`，由新执行者逐名审阅，按原`apply-vocabulary`校验并更新索引。单视频成本实测用独立库，不能拿十道或全库词典盘点费用当单视频固定成本。

```bash
"$SESSION" --root "$FLOW_ROOT" register --stage ingredients \
  --agent /root/本次食材执行者 --task-id 实际清单任务ID
"$SESSION" --root "$FLOW_ROOT" usage --output "$FLOW_ROOT/token实测-新文件.json"
```

usage只读本机会话日志的实际`token_usage_record.usage`，按唯一response_id去重，限制登记执行者的真实thread_id；排除继承父线程计数、其他视频、自动审批及开发调度会话。不累计相加`total_token_usage`，不把字符数当真实token；缓存输入包含于输入，reasoning包含于输出。缺阶段记录标`incomplete`；每次请求含失败/重试都计入。报告是用量快照，完成状态另由flow归档/发布核验，最终报告需等待全部登记执行者完成。开发和根代理调度开销须另列，不能以菜谱worker数字冒称整个聊天账单。

已有后台OCR监视器时，新下载或测试副本的media目录放在它的监视范围之外（例如`/home/liou/Downloads/菜谱串行流程/media`）。不要同时让监视器和flow生成同一字幕；即使同内容被重写，也会触发文件身份保护。提供已有字幕时必须保持视频/字幕不被其他任务写入；发生冲突应保留审计并在隔离目录重新登记，不能放宽身份检查。

本次实测用一个6分04秒的既有视频重新做全片本地OCR，得到153条字幕，完整执行整理、独立文字复审、14步选图（168张实际候选）、独立图后复审、22个食材名称复核、归档及HTML/JSON/搜索目录。没有采用旧菜谱seed或旧AI结果；整理数量模式的一次失败及重试也计入。

| AI阶段 | 实际请求数 | 总token（含缓存输入） |
| --- | ---: | ---: |
| 整理及重试 | 9 | 314,354 |
| 全文文字复审 | 6 | 246,462 |
| 14步视觉选图 | 104 | 3,463,449 |
| 独立图后复审 | 13 | 699,182 |
| 食材名称/别名复核 | 5 | 185,977 |
| 合计 | 137 | 4,909,424 |

合计包含缓存输入4,430,208、非缓存输入433,566、输出45,650；reasoning是输出子集，不另加。非缓存输入加输出为479,216，但缓存也属于真实请求用量，不能称作免费或直接据此推算费用。本地下载/OCR/抽帧/验证/渲染/索引没有模型调用。根代理本轮开发、测试和调度截至报告快照另计12,905,697（其中缓存12,676,608），不在上表，也不代表未来每个视频必然消耗这些。

此为当前Codex子代理执行方式的一个样本，含执行环境说明、工具响应和重复上下文；不能当作纯提示词或未来API请求的固定成本。长度、步骤数、候选图、修复轮次和词典全库规模会改变成本。食材全库复核是批次费用，本次为独立单视频库；大库不应每完成一道菜就重复盘点全部菜谱。

实测发布状态为needs_review，保留8项用量/OCR疑点和OCR来源pending，视频未删除；“全流程跑通”指形成可浏览、可检索、可从归档重建的菜谱，并不等于所有疑点已消除。后续消疑或来源验收若再调用AI，须追加到实测报告，不能以当前数字保证零疑点终稿的成本。原310份媒体/字幕文件身份未变。任务、原图、OCR和原始usage只保留在Downloads的独立实测目录，不进入Git或NUC文档镜像。

片段时间范围同时覆盖步骤evidence_windows和该步骤全部事实引用的字幕区间，前后扩展后合并重叠窗口，不连续区间分别保存；不能仅沿用旧选图的窄窗口截断步骤说明。手选时间精度为毫秒，超出精度或范围的导入拒绝。HTTP编辑入口只在响应内挂载当前控件和选图状态，不修改归档HTML。

真实演示目录为Downloads/菜谱步骤视频试验-20261007-完整步骤；14个片段约70MiB，保存完整步骤上下文可能比原视频大，不保证节省磁盘。演示保留文字/OCR疑点和原视频；未执行全库。旧运行队列若因工具/契约升级出现旧任务摘要失效，应重新导出当前任务，不改摘要或旧回复绕过验证；已经验收的图片模式归档仍可查看/重建。修订步骤窗口时，只在新修订临时目录重生成片段，原归档和用户选择保留，旧选择绑定不同摘要时拒绝自动套用。

中文专用 yt-dlp 提取插件只在字幕探测时显式加载，在读取平台轨道元数据后仅下载 ai-zh 正文，不请求人工/英文/其他语言字幕或弹幕正文。确认插件生效标记后才判断缺字幕；API 非零码、登录要求、无效轨道元数据及空正文属于失败。探测进程最长 600 秒，超时保留可重试失败，不永久跳过。插件实现由本工程维护，使用[官方插件扩展接口](https://github.com/yt-dlp/yt-dlp#developing-plugins)，无需安装新平台 SDK。

AI-only 真实样稿位于 `/home/liou/Downloads/菜谱AI字幕流程试验-20261007`：肉末蛏子盖饭使用121条新平台字幕，14步/23食材/15片段，15待核对问题保留，原视频未删除。用 `scripts/recipe-flow --root '/home/liou/Downloads/菜谱AI字幕流程试验-20261007' serve` 打开本地目录并选图；另外两条已缓存字幕但未生成菜谱。不读取原视频的重建及食材检索通过；117项回归通过。毫秒时间按整数秒加毫秒统一解析，保持真实时间轴改动拒绝，不使用浮点容差放过来源变化。
