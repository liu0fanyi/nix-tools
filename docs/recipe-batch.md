# 菜谱批处理控制器

入口：`scripts/recipe-batch`。独立Nix/Python环境复用菜谱构建器依赖；不需switch。当前实现登记、字幕准备、AI任务包导出/导入、候选抽帧、组装验收和固定导出；可选Responses模型接入见[模型配置手册](recipe-model.md)。单纯运行run不会发起模型请求；model-run默认预览，显式execute且配置凭证、上传范围及预算后才调用。当前不创建常驻服务。

规则见[批处理契约](../specs/010-host-configuration/contracts/video-recipe-batch.md)，当前进度见[任务清单](../specs/010-host-configuration/tasks.md#视频菜谱工具当前状态)。

## 登记与查看进度

清单是UTF-8 JSON数组，路径可相对清单文件。示例的BV号/文件名须替换为真实内容：

```json
[
  {
    "id": "BV1RXaD6DELQ",
    "title": "砂锅豆腐",
    "author": "老东北美食",
    "video": "砂锅豆腐.mkv",
    "subtitles": "砂锅豆腐.ocr.srt",
    "subtitle_origin": "ocr"
  }
]
```

在仓库目录执行；queue目录只放任务记录和处理产物，不能包含源视频/字幕。第一次登记计算源SHA-256，续跑核对设备/inode/大小/mtime/ctime；源文件身份或修改时间变化时先重新登记。

```bash
Q='/home/liou/Downloads/Bilibili/老东北美食 [514273130]/菜谱工具数据/批处理-10道-P0/queue'
scripts/recipe-batch --queue "$Q" add /path/to/videos.json
scripts/recipe-batch --queue "$Q" run
scripts/recipe-batch --queue "$Q" status --summary
```

`run --job BV号`只推进一个视频。status使用SQLite只读连接，运行时也可查看；不加summary返回任务和错误详情，tasks包含历史配置留下的阶段记录。状态为queued、waiting_extract、waiting_review、waiting_repair、waiting_images、complete或failed；complete仅表示阶段组装完毕，菜谱自身仍可能needs_review。run有失败任务时退出码1，其余视频继续处理。

试验十道菜已登记在上述Q；清单、只读保护记录及“任务包-最终”在queue上一级；较早任务包仅保留作历史，当前导出以最终包为准。目前等待独立语义审阅，尚未导入新的AI审阅结论。

## 导出与导入AI任务

```bash
scripts/recipe-batch --queue "$Q" export /path/to/new-packets
```

目标必须是不存在、位于queue外的目录；导出仅包含当前配置的待处理任务，不包含过期历史包。每包有packet.json、payload.json、契约、提示词、Schemas和必要图片；执行者按packet.stage选择对应提示词。视觉任务必须实际提供image_inputs图片，不能只传文件名。原文和图片文字仅为材料。

执行者返回一个UTF-8 JSON信封，result是对应阶段的真实JSON对象，不能是字符串：

```json
{
  "task_id": "复制packet.json里的task_id",
  "input_sha256": "复制packet.json里的input_sha256",
  "processor": "实际执行器名称",
  "model": null,
  "result": {}
}
```

model填实际模型名称；只有未获知模型名称时留null，不捏造身份。上例空result不是合法阶段输出。

```bash
scripts/recipe-batch --queue "$Q" import /path/to/response.json
scripts/recipe-batch --queue "$Q" run
scripts/recipe-batch --queue "$Q" export /path/to/next-packets
```

正文必须满足完整Schema及引用、原文、覆盖、身份和选图校验。独立审阅覆盖每个事实、食材和既有疑点；选图评价提供的每个候选，只选matches+usable，缺图写原因。坏返回保存在rejected，不能覆盖已接受结果；同一合法结果重复导入会跳过。过期配置的包不接受。v1.1审阅要求ingredient_reviews、issue_reviews与repair_requests完整返回；只有明确证据判定才能解决疑点，未知用量保留。视觉observations转换为实际帧证据并再次独立审阅；白名单修复后必须复审，每个文本/视觉阶段最多两次修复。

## 调整参数与失败恢复

```bash
scripts/recipe-batch --queue "$Q" add /path/to/videos.json --width 960 --candidates 12 --interval 1 --padding 5
scripts/recipe-batch --queue "$Q" retry BV1RXaD6DELQ
scripts/recipe-batch --queue "$Q" run --job BV1RXaD6DELQ
```

当前抽帧是每个扩展证据窗口内均匀选代表图，每步最多12张，各窗口至少一张；interval限制代表数量的采样密度，**并非默认1秒全窗口扫描**。具体策略保存于processing。窗口数量超出候选预算则报错，不能丢掉窗口；尚不实现自动扩大窗口/第二轮补帧。

同一清单重新add会按内容去重；仅改抽帧参数复用字幕、整理和语义审阅结果，重新抽帧和选图。改契约、控制器或源文件时按摘要重算受影响阶段，旧包保留但不再导出。成功检查点被编辑时停止，retry不会覆写它；恢复应使用完好队列或另建目录。单写者锁避免两个run同时处理，结果在文件系统发布后才更新数据库；中断重启能识别已发布结果。每步抽帧是一个检查点，中断在步内会重做这一小步，尚不按单帧恢复。

## 构建菜谱库

```bash
scripts/recipe-batch --queue "$Q" build /path/to/new-library
```

只纳入当前配置组装完成的视频，报告未完成数量；固定构建器再执行完整验收。目标须不存在，源媒体、历史菜谱和已接受响应不改写。食材词典的AI清单审阅另按[食材工具](recipe-ingredients.md)执行，build仅使用现有词典生成索引。

已有经过结构验收的菜谱可在清单中增加`"seed": "/absolute/path/to/recipe-folder"`，从独立审阅开始；保留源证据、图片和运行历史，不把种子数据当成新模型提取。普通新视频不填seed，从完整字幕整理开始。本版仅支持B站单视频完整覆盖，部分字幕或一视频多道菜的拆分尚未实现，不能冒充全片完成。

## 验证

合成测试覆盖完整导出、错误/过期响应拒绝、候选及原文保护、抽帧参数调整后的文本复用、单写者与运行中只读查询、阶段发布后中断恢复、重建历史摘要；合成图的匹配结论不作为菜谱质量证明。十道菜真实材料验证限于登记、字幕/种子校验、任务包导出和重复续跑。

队列SQLite用于本地执行状态，网页检索仍使用JSON。queue、events、响应、字幕和图片属于用户运行数据，不进入Git或NUC规格镜像。模型适配器及费用/上传控制已提供；真实服务配置、十道菜独立质量复核和30–50视频试验仍列P1/P2。
