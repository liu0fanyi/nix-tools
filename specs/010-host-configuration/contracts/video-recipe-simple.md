# 精简菜谱与原网页键盘浏览契约

新入口 recipe-simple，独立 ROOT，唯一处理链：平台 ai-zh 字幕与原视频封面 → 单次 AI 材料/用量/制作过程提取 → HTML/JSON/食材目录。不下载视频/音频、不 OCR、不切片、不抽图、不执行独立文本/视觉复审，不包含视频释放或人工认证门槛。旧流程和旧档案不自动迁移；已有原视频仅按用户明确清理授权处理。缺中文 AI 字幕 skipped；风控/网络/登录/封面错误 failed 可 retry；每条检查点可续跑，单写者。

AI 返回 title、ingredients[{name,amount:null|string,optional:boolean}]、steps[{text,cue_ids}]、notes。用量不明用 null，误识别保留 notes，不为凑材料或过程猜数字；替代食材 optional=true 并在过程/notes注明替代条件。Schema 见 video-recipe-simple.schema.json，控制器验证引用真实、非空、时间顺序，按引用脚本生成每步原视频时间范围。不再生成事实图谱、逐项 review 记录或 frame 候选。菜谱统一标“AI 字幕整理”，不冒称已独立或人工核验。

AI 输入包 task_id/input_sha256/source/transcript/prompt/result_schema；结果信封仅 task_id/input_sha256/processor/model/result。来源和字幕、封面 SHA 绑定；重复导入幂等，过期/修改输入拒绝。SQLite 仅保存进度，静态目录使用 JSON/现有食材词典，保留原名/未知/可选标记；本轮不新增强制 AI 词典全库复审。平台元数据在新 ROOT 裁为获取封面和字幕所需字段，不保存视频格式/CDN播放URL。

只读本地预览允许 library 的普通文件及下述汇总进度接口，不暴露 Cookie/SQLite/平台元数据/任务包。目录展示视频原封面，菜谱为材料和步骤，每步链接 B 站原视频相应时间，保持材料检索。封面是原封面，不声称画面选图。播放器增强不把原视频流代理或复制到菜谱服务。

## 用户确认的键盘浏览语义

逐帧模式默认暂停；单按 ←/→ 上一帧/下一帧，按住空格播放、松开停，+/− 或倍速选择控制按住时速度，S 暂停并保存截图；失焦、隐藏、keyup 必须停，编辑输入时不抢键。模式可退出恢复平台原操作，原页导航/更换 video 元素须重新绑定。截图不上传、不调用 AI。跨域 canvas 限制须明确报告截图失败，不能声称已保存。

邻帧定位 MUST 以实际流的帧时间表为依据，不用 1/25 或 1/30 秒假冒帧间隔。当前实现通过 document-start/page 用户脚本，观察主页面 MediaSource/SourceBuffer 已有 appendBuffer 的分片 MP4 moov/moof 元数据，不发起媒体请求，不保存/转发 mdat 内容。解析 video 轨道、timescale、trex/tfhd 样本时长、tfdt 解码起点、trun 组合偏移和单项 rate=1 的编辑表，叠加 timestampOffset，以实际 PTS 排序邻帧。只合并解码时间连续的分片，重传替换、初始化/轨道变化清空旧索引；每条来源最多保留120000帧，最多关联8个媒体URL，单元数据box限2MiB，未知/截断/超大/不安全时间值拒绝。

操作目标为真实相邻帧呈现区间内部，必须在已缓冲范围，等待 seeked 与画面呈现回调，验证位置仍在目标帧区间，再报告完成；超时/来源或索引变化拒绝。requestVideoFrameCallback 在此用作画面呈现信号，不把其暂停跳转时的 mediaTime 作为真实源帧 PTS（隔离 Zen 实测该值可能直接等于请求时间）。变帧率和 B 帧按解析的实际时间处理；负速率不作为连续倒放保证。按住播放后松键先立即pause，再定位到缓冲时间表中邻近的真实帧区间并等待呈现，建立明确的暂停帧，避免 Zen 自然暂停的屏幕画面与 currentTime 可能差一帧。每次只运行一个逐帧操作，重复键不累积无界队列；失焦、隐藏、更换 video、退出模式取消操作并暂停，模式退出后不由旧异步操作重新暂停原播放器。

## 实现范围与验证结论

0.2.0 的单轨道分片 MP4 邻帧及按住播放/调速/截图已实现。要求用户安装后刷新原页、以page上下文足够早运行；未捕获初始化、Worker缓冲、非MP4、sequence模式、裁剪窗口、复杂编辑表、缺失相邻分片/未缓冲帧，均报告不可用，不猜帧或静默跳秒。公开规格/测试不保存真实字幕、封面、Cookie或原视频。真实 B 站安装后确认独立于本机合成媒体程序验证。


## 全量源采集

`collect --max-pending 10 --interval 60`在pending上限退出；增加`--watch`则等待AI输出导入后继续采集。仅queued可自动准备，waiting_extract检查点与published不重取；缺字幕skipped，其他错误failed并停止。独立`.collector.lock`防重复采集，普通写锁每条结束后释放；导入与采集冲突时等待，不绕过锁。`ROOT/collect.stop`存在时在当前请求结束的检查点退出；移除停止标记再执行collect可续跑。后台不运行模型或下载视频，全量完成必须按实际菜谱发布及失败/跳过对账判断。


## 只读实时进度

本地GET `/api/progress`提供总数、五类计数、已结束（published+skipped）、来源处理（published+skipped+waiting_extract）、剩余数及采集器汇总状态；不提供ROOT、任务路径、Cookie、原始元数据或错误正文。SQLite聚合只读统计，不请求字幕或调用模型；采集器是否运行以已有采集锁实际占用为准，不单凭PID或陈旧心跳。失败不计入完成，来源已处理不等同于菜谱已生成，零总数不除零。

GET `/progress.html`显示已生成菜谱与来源处理两条进度条、published/waiting_extract/queued/skipped/failed数，每5秒刷新。连接失败保留上次数据并标明失效，单次请求超时6秒，不重叠轮询。接口和页面no-store，沿用127.0.0.1监听及Host校验，其他私有文件仍404。目录提供“处理进度”链接。


### Codex CLI自动消费者

另行获得模型目的地的数据传输授权后，可用既有CLI登录进行非交互式单次全文提取。消费者独占`.ai-worker.lock`，每条任务新上下文、只读沙盒、stdin输入和Schema输出，不持有数据库写锁等待推理；导入阶段使用原输入/输出绑定与cue校验。已有完整响应复用，未完成尝试拒绝默默重推；错误停止，详细日志仅本地，停止标记在任务边界生效。原进度API增添ai.active/state/model/current_id白名单，按实际锁判断活性，不输出提示词、Cookie、日志或私有路径。真实模型准入未通过不能标自动流程实测完成。

发送Schema允许移除服务端不支持的uniqueItems；本地原始Schema及真实cue校验不得放宽。发布步骤按真实字幕起点稳定排序，原始答案须保留，不改材料或步骤文本，不添加复审模型调用。


### 进度事件白名单

progress新增events（至多80项）：stage、phase、video_id、time和受控message，旧记录时间可null；每阶段日志读取量≤64KiB，不直接暴露日志路径或全文。health为state/reason/last_progress_at；采集停止且仍有来源排队即blocked，即使AI进程活着。collector/ai的last_activity_at是状态报告时间，不得当作菜谱推进时间。错误正文仍只留本地，页面只显示固定类别，日志文本禁止按HTML插入。
