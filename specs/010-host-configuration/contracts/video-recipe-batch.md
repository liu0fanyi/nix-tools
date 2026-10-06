# 视频菜谱批处理契约 v1.1

版本1.1.0；归属010工具。支持任务包交换和可选Responses模型调用；run本身不请求模型，model-run默认预览。字段及事实约束仍遵守[菜谱契约](video-recipe.md)、[内部Schema](video-recipe.schema.json)与[阶段Schema](video-recipe-stage.schema.json)。操作入口见[批处理手册](../../../docs/recipe-batch.md)。

## 登记与阶段

清单是非空JSON数组，字段仅允许id/title/author/video/subtitles/subtitle_origin及可选seed。id为稳定BV号，同批不得重复；字幕来源为ocr/platform/asr。相对路径相对清单文件解析，视频与字幕为普通文件、位于queue之外。登记计算SHA-256并记录文件身份、大小、mtime/ctime，哈希前后身份变化拒绝；续跑身份变化拒绝，重新登记新修订。seed仅接受已经通过完整构建器校验的内部菜谱目录，保留真实源及图片，不改写原库。

阶段：prepare → extract（或seed）→ review/限次repair与复审 → 每步frames/select_images → 观察证据与复审 → assemble → build。prepare用ffprobe读取真实时长，SRT必须为UTF-8、稳定唯一编号、合法时间、非空且按时间排序，cue不得超出视频；正文原文保留。当前只接受单视频全片覆盖，partial/拆分视频不得按full导出。

SQLite保存job当前修订、状态、错误及历史task；本版只允许一个写进程，status为只读查询。任务身份绑定job、stage、控制器版本/代码摘要及阶段输入；抽帧配置不进入文本阶段身份。契约与提示词摘要进入AI阶段身份，构建器摘要进入assemble身份。

## 任务包与结果

包包含packet.json、payload.json、契约及Schemas；视觉包还包含编号相同的真实image_inputs。packet固定version/task_id/job_id/stage/input_sha256/image_inputs/output_envelope/note；payload完整保留该阶段来源、字幕、草稿或步骤、候选信息。图片路径/摘要由脚本产生；模型不得更改来源、字幕、图片登记、runs或human_reviewed。

响应字段仅允许且必须包含task_id/input_sha256/processor/model/result。task_id及输入摘要须与当前有效包一致；processor登记真实执行器，model为真实名称或未知时null；result为阶段Schema的对象。正文、Schema、证据引用/原文/范围、用量模式、覆盖、依赖及事实/图片评审完整性校验后才接受。文本整理不得创建帧或运行记录，status只能draft，覆盖必须全片。审阅检查每个事实、食材及既有疑点恰一次；新控制器强制ingredient_reviews/issue_reviews/repair_requests。疑点仅按独立审阅的理由与证据判定解决，不能覆盖删除；选图检查本包每张候选恰一次，仅允许实际提供的matches+usable帧，空图需理由。

包不可变，结果保存在单独不可变results任务目录，带文件摘要清单。结果发布先于数据库状态写入，中断后从完整已发布目录恢复。相同返回重复导入跳过；不同返回不能覆盖已接受结果；坏正文留rejected及日志。正在使用的检查点文件被改动则停止，retry不授权覆盖。旧配置包保留作审计，但不得导出或接受为当前任务。

## 抽帧、状态与产物

当前策略为每个±padding扩展窗口内均匀分配代表帧，每步候选上限1–12，宽度16–3840、interval>0、padding范围0–60；所有输入数值必须有限。必须保留每个原窗口至少一张，窗口多于预算则失败。此策略偏离菜谱契约默认1秒扫描，实际参数及限制必须在processing登记；本版未实现自动扩窗/补帧。每步缓存完整候选目录，步内中断可重做，完成步不重复抽帧。

job状态queued/waiting_extract/waiting_review/waiting_repair/waiting_images/complete/failed。complete仅表示阶段执行完成；组装由程序计算菜谱status，存在open issue即needs_review，human_reviewed始终false。食材由独立ingredient_reviews判定，未知用量保持未知，不因步骤事实通过自动认证其用量。视觉observations转换为实际帧证据和待核对疑点，需独立复审，不直接替换事实。白名单修复后再次审阅，文本/视觉各最多两次，超限保留疑点。原有open issue不自动清除；缺图新增missing_image并显示原因。

组装保存source.srt、transcript、recipe.internal、semantic-review、image-selection、candidates、processing和输入历史。runs由控制器添加，输入摘要与快照核验；历史候选输入按candidates-input-<SHA>.json保留。build只读取当前组装完成记录，调用固定构建器输出新菜谱库并报告未完成数，已有目标拒绝覆盖。食材词典审阅仍单独运行，全库索引只使用当前权威词典。

## 当前限制与验收

配置与调用详见[模型手册](../../../docs/recipe-model.md)。默认不上传、不付费；只有显式execute且预算、上传范围与凭证配置齐备才调用模型。记录usage估算费用，每请求先持久预留；超时未知结果不盲目重试。无需聊天进程，但不创建常驻服务，本控制器不清理媒体；串行验收归档与显式视频释放见[生命周期契约](video-recipe-flow.md)。实际服务配置未完成；十道菜会话子代理独立复核已完成，未解决来源与结构化覆盖缺口仍保留。P0验收至少覆盖恢复、过期/坏返回隔离、已有输出保护、配置变更复用、运行中只读进度及真实输入登记/导出；独立菜谱语义质量另验收。运行数据库与素材只留用户目录，远端镜像仅按specs/docs白名单。

## 种子重组装兼容性

历史recipe-input.json在组装阶段按内容摘要另存，当前输入保持唯一名称。同ID且全部字段相同的帧允许复用一次；同ID内容不同须失败，不覆盖。config/recipe/cache-compatibility.json仅固定已核验的组装修复对应controller和review-helper完整SHA256，非assemble阶段可沿用指定旧controller摘要；assemble总使用当前源码。任一源码摘要不匹配即停用兼容映射，输入/契约/模型绑定的校验不受此映射影响。
