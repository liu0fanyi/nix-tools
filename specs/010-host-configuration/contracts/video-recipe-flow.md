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

inventory收集全库当前/previous已归档清单并保留所有不同名称及证据；apply-vocabulary核验当前完整inventory和词典摘要，逐名覆盖、证据来源及别名/父类约束后保存不可变提案审计、更新工作流词典与目录。过期或漏审提案拒绝。此命令不自动改写仓库权威词典；主代理按同一已核验结果统一同步，运行材料不进入Git或NUC镜像。

## 验收边界

合成专用媒体验收真实unlink及各中断点，不作为菜谱语义质量证明。真实十道已完成复核结果只迁入/归档/发布与释放预演，全部needs_review、视频保留。4200项清单仅证明持久登记及串行状态能力，不证明线上目录完整、真实新下载/全量OCR或4000道内容通过；真实扩容仍先30–50道及已规定质量门槛。
