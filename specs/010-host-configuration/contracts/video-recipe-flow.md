# 视频菜谱串行生命周期契约 v1.0

归属010工具；阶段执行、Schema与独立审阅仍遵守[批处理契约](video-recipe-batch.md)。操作入口见[生命周期手册](../../../docs/recipe-flow.md)。recipe-flow不修改既有控制器缓存身份、不直接调用模型；AI结果来自当前会话的实际执行者或另行配置的模型。

## 清单与串行推进

清单为非空JSON数组，每项必须含稳定BV id、title、author，可选video/subtitles/subtitle_origin/seed；也接受yt-dlp flat playlist的entries数组并抽取元数据。链接按BV生成固定B站地址，不能接受任意shell命令或外部站点。清单全体先验证后事务登记，重复相同项幂等，改变同ID初始元数据拒绝；大清单登记不下载。网页检索仍为JSON，SQLite仅管理持久执行状态，单写者且FULL同步，status只读。

next只推进最早未归档且非failed的一项。未提供video时下载到声明media_root/BV/source.mkv，固定单并发、15秒请求间隔、30–60秒下载等待、2MiB/s限速及有限重试；Zen登录可经用户已授权的Firefox Cookie选择器读取，不复制Cookie入日志/响应。未提供字幕时调用全片本地OCR，已有清单字幕不改写。日志在工作流logs下。失败暂停该项并保留，retry不覆盖素材或审计；已开始失败项持续占容量，默认至多3个未释放、root与media_root均须至少5GiB。容量只限制新开项，不阻止已开始任务继续。等待AI时不继续预下载，export/import沿用当前阶段的不可变信封校验。

## 会话任务交换

run --watch持有单写者锁，机械执行next并导出task-packages/current.json指向当前阶段的不可变任务包；等待AI时不下载下一条，不重复运行阶段或重写未变任务指针。会话子代理查看文字/图片并将既有Schema信封先写临时文件、再原子重命名为responses/*.json。脚本按内容摘要接收、验证、推进并保留原始回复到responses/accepted，不调用模型API或自行上传。坏回复暂停且保留；修正后的不同内容摘要允许再次验收。已接受回复的归档错误不能降级为rejected，错误单独记录，重启重试归档后继续推进。普通重复投递不重复执行AI。status只读可并行查看；运行watch时其他写入命令必须先停止它。关闭会话后机械脚本可以等待，AI任务仍需会话执行者或另行配置的服务。

## 验收归档与发布

阶段complete后重新验证当前装配检查点、源摘要及完整内部结构，复制字幕、全部登记帧、菜谱、完整输入历史、复核/选图/处理审计到accepted不可变归档，并保留OCR报告（若有）。acceptance保存源视频完整SHA256、dev/inode/size/mtime/ctime及装配摘要、释放门槛和政策版本；checksums覆盖所有归档文件。逐文件及新建目录层级fsync、原子发布、父目录fsync完成后提交SQLite接受状态。

单视频固定构建和发布为独立页面目录；publication意图含归档摘要、页面全文件摘要、目录记录及本次不可变词典快照摘要，先完整原子持久发布，再重命名页面目录、同步父目录、提交记录。恢复可重建同一页面并逐文件比对；词典更新后仍使用该publication快照恢复，源渲染器变化导致不一致时停止，不能覆盖旧版。每次目录HTML内嵌完整食材索引，JSON/HTML分别原子更新，中断可恢复一致；输入及产物摘要未变时不重复重写。build/rebuild从接受归档读取，原视频删除或原阶段控制器升级不影响来源保留与页面重建。

## 视频释放

release默认预演，只有release --execute或next/resume/run --delete-videos明确启用实际释放。eligible要求全片、ready、所有步骤已有对应选图、无开放issue；OCR来源还要求有效video-subtitle-ocr报告与当前媒体signature（size/mtime_ns）、SRT SHA、source一致，完整处理duration未截断、status done且无flags。缺报告、过期/错误报告、缺图或needs_review均保留。human_reviewed=false不由程序或AI提升，不要求伪造人工核验。

删除前核验不可变归档、页面全文件、索引当前记录及HTML内嵌一致；只有声明媒体根内的登记普通视频可释放，拒绝任意层级符号链接及硬链接，身份与SHA再次一致。政策版本未知不能删除，须保留视频并重新复核。完整删除意图原子持久写入、SQLite release_pending提交先于移动。仅将该准确文件名移动到原视频父目录下.recipe-release/<workflow-root摘要>/，所有新增祖先持久化后进行；同盘、无glob或递归。隔离后复核dev/inode/size/mtime及SHA，ctime因rename变化不作误报；核验通过才unlink并fsync隔离目录、提交deleted。任一不一致不unlink，不删除字幕、OCR、帧、菜谱、其他视频或sidecar。

已有持久意图属于已提交操作，后续resume/next不需要再次传删除开关即可完成：意图后尚未移动、已移动未unlink、已unlink未提交deleted分别恢复。源与隔离同时出现、身份变化或完成后源重新出现则报错保留，不能删新文件。deleted项不重新进入下载/OCR/AI控制器，也不在每次next反复执行删除。失败项和未解决疑点持续可见，不宣称全库质量通过。

## 修订与食材词典

rework仅允许视频仍保留且无提交删除意图的归档项；源身份及摘要仍须一致。默认以现有归档seed，也可指定经验证且同视频/字幕来源的新seed。新revision使用独立queue/archive/page/意图文件，不覆盖旧版；复审期间previous_archive支持重建和食材清单，旧页面及目录继续可读。新版本完成后更新当前记录，旧审计永久保留。rework后禁止adopt旧complete队列绕过新复核；已删除项可rebuild网页但不能伪称重新查看视频。

prepare-revision接收完整结构提案并输出新seed，必须保持来源/覆盖/human、旧ID、旧证据/问题/帧/图片审阅/运行历史；允许添加有合法字幕证据的食材和独立事实、纠正材料关联及变式替代关系、收窄图窗。旧事实不移到其他步骤；变更/新增事实食材强制needs_review并补待审问题，不接受自认证。当前图窗不再包含旧选帧时由程序清空选择并新增缺图问题。保留旧阶段摘要快照，提案及源归档摘要/实际执行者写入新的持久审计；semantic准备回执仅保留未变项的旧状态，变更项待审，不冒称独立判断。输出须是受保护数据之外的新目录，校验完整seed后原子发布；随后rework建立新revision并进行正式独立审阅。

inventory收集全库当前/previous已归档清单并保留所有不同名称及证据；apply-vocabulary核验当前完整inventory和词典摘要，逐名覆盖、证据来源及别名/父类约束后保存不可变提案审计、更新工作流词典与目录。过期或漏审提案拒绝。此命令不自动改写仓库权威词典；主代理按同一已核验结果统一同步，运行材料不进入Git或NUC镜像。

## 验收边界

合成专用媒体验收真实unlink及各中断点，不作为菜谱语义质量证明。真实十道已完成复核结果只迁入/归档/发布与释放预演，全部needs_review、视频保留。4200项清单仅证明持久登记及串行状态能力，不证明线上目录完整、真实新下载/全量OCR或4000道内容通过；真实扩容仍先30–50道及已规定质量门槛。

recipe-session提供绑定原task_id/input_sha256的独立视图，不修改原AI契约或验收。文字视图保留全文语义及cue；视觉视图限步骤窗口±5秒及两条邻句，所有候选图片原摘要仍核验；使用新会话执行阶段，并保留原信封绑定。usage登记明确stage/agent_path/task_ids，按本地真实thread_id及response_id去重汇总请求，缓存输入/推理输出分别是输入/输出子集；缺记录或计数冲突拒绝作为完整实测。开发调度不混入视频AI阶段，完成状态与用量快照分开验证。


## 步骤片段与手选媒体

新建CLI流程`init --media-mode clips`为默认；`images`及历史缺字段配置保留旧视觉流程。clips队列仅请求extract/review/必要repair，随后执行机械step_clips/assemble，无select_images/review_visual。`processing.json.media_mode=clips`声明新增媒体分支，`step-clips.json`按[片段Schema](video-recipe-clips.schema.json)及语义校验要求覆盖每步每个扩展窗口，sha绑定来源与普通MP4，校验H.264/AAC、尺寸、时长与文件摘要。图片可为空，不创建虚假的图片评价；来源事实和文字复审契约不变。

`scripts/recipe-flow --root ROOT serve --port 8765`只监听127.0.0.1，静态服务ROOT/library。`GET/PUT /api/recipes/<recipe-key>/media`返回/保存`{version,recipe_sha256,clips_sha256,steps:{step-id:{mode:video|images|both,frames:[{clip_id,time}]}}}`，time为片段内秒数、有限且在片段/窗口内，每步最多32帧。绑定过期、跨步骤片段、未知字段/步骤、越界、重复帧和仅图片但为空拒绝。写入要求同Host/Origin，拒绝跨站请求，正文最多1MiB；用户JSON不能指定文件路径或上传图像。脚本从已校验片段生成JPEG，状态原子写入ROOT/user-media/<recipe-key>/，图片只允许读取当前状态引用的SHA文件。GET/HEAD路径拒绝符号链接/越界，不提供Cookie或任意目录访问。

Overlay不修改recipe.internal、accepted、library内容，不提升human_reviewed；导出/导入选择JSON可在同摘要菜谱恢复，图片可由片段重建。归档/重建包含片段和清单。视频释放仍需OCR done无flags、无开放事实疑点与来源/归档/发布/媒体一致；只将每步AI图片必选条件替换为经校验的完整片段，不能按“浏览页面可播放”直接删除。

片段时间范围同时覆盖步骤evidence_windows和该步骤全部事实引用的字幕区间，前后扩展后合并重叠窗口，不连续区间分别保存；不能仅沿用旧选图的窄窗口截断步骤说明。手选时间精度为毫秒，超出精度或范围的导入拒绝。HTTP编辑入口只在响应内挂载当前控件和选图状态，不修改归档HTML。

## AI-only 字幕准入

CLI init 默认 subtitle_policy=bilibili-ai-only（旧设置缺字段或显式 legacy 保持历史处理），固定配置不原地改写。该策略 add 仅接受 id/title/author 和可选已有 video；subtitles/subtitle_origin/seed 拒绝，adopt 拒绝外部结果。先在 ROOT/platform-subtitles/<BV>/ 保存平台 info 和 source.ai-zh.srt；--ignore-config 防止用户全局下载/字幕设置意外扩大范围。字幕探测成功、无登录/字幕请求警告且无 ai-zh 才保存 {id,status:skipped,reason:no_ai_zh_subtitles}；控制器设置 state=skipped、started=0，next 和 watch 完结查询排除 skipped、retain_count 排除 skipped。已有视频和 sidecar 不删除。

有轨道则 SRT 完整解析、时长/ID/摘要校验；result.json 保存 {id,status:available,language:ai-zh,origin:platform,generation:ai,duration,cue_count,sha256}。该结果先于视频下载持久化，恢复复用并重新验证字幕 SHA。网络/风控/登录失效/缺文件/坏字幕为 failed，可 retry，不能永久跳过。每个 next 至多探测一条；run --watch 在无 AI 任务时继续下一条，全部 skipped 时终止。

通过准入后 subtitle_origin=platform，继续全文 AI 整理、独立文本审阅/修复、clips 及归档/目录。验收归档 source-platform-subtitles.json 复制已验证回执并绑定实际字幕摘要；字幕为平台 AI 输出，不是人工校验。既有事实、独立复审、疑点、媒体身份及完整片段门槛保持；新流程不存在 OCR 任务或 OCR 门槛，实际语义问题仍须保留。

中文专用 yt-dlp 提取插件只在字幕探测时显式加载，在读取平台轨道元数据后仅下载 ai-zh 正文，不请求人工/英文/其他语言字幕或弹幕正文。确认插件生效标记后才判断缺字幕；API 非零码、登录要求、无效轨道元数据及空正文属于失败。探测进程最长 600 秒，超时保留可重试失败，不永久跳过。插件实现由本工程维护，使用[官方插件扩展接口](https://github.com/yt-dlp/yt-dlp#developing-plugins)，无需安装新平台 SDK。
