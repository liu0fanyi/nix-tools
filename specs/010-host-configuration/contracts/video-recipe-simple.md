# 精简菜谱与原网页键盘浏览契约

新入口 recipe-simple，独立 ROOT，唯一处理链：平台 ai-zh 字幕与原视频封面 → 单次 AI 材料/用量/制作过程提取 → HTML/JSON/食材目录。不下载视频/音频、不 OCR、不切片、不抽图、不执行独立文本/视觉复审，不包含视频释放或人工认证门槛。旧流程和旧档案不自动迁移；已有原视频仅按用户明确清理授权处理。缺中文 AI 字幕 skipped；风控/网络/登录/封面错误 failed 可 retry；每条检查点可续跑，单写者。

AI 返回 title、ingredients[{name,amount:null|string,optional:boolean}]、steps[{text,cue_ids}]、notes。用量不明用 null，误识别保留 notes，不为凑材料或过程猜数字；替代食材 optional=true 并在过程/notes注明替代条件。Schema 见 video-recipe-simple.schema.json，控制器验证引用真实、非空、时间顺序，按引用脚本生成每步原视频时间范围。不再生成事实图谱、逐项 review 记录或 frame 候选。菜谱统一标“AI 字幕整理”，不冒称已独立或人工核验。

AI 输入包 task_id/input_sha256/source/transcript/prompt/result_schema；结果信封仅 task_id/input_sha256/processor/model/result。来源和字幕、封面 SHA 绑定；重复导入幂等，过期/修改输入拒绝。SQLite 仅保存进度，静态目录使用 JSON/现有食材词典，保留原名/未知/可选标记；本轮不新增强制 AI 词典全库复审。平台元数据在新 ROOT 裁为获取封面和字幕所需字段，不保存视频格式/CDN播放URL。

只读本地预览仅允许 library 的普通文件，不暴露 Cookie/SQLite/平台元数据/任务包。目录展示视频原封面，菜谱为材料和步骤，每步链接 B 站原视频相应时间，保持材料检索。封面是原封面，不声称画面选图。播放器增强不把原视频流代理或复制到菜谱服务。

## 用户确认的键盘浏览语义

逐帧模式默认暂停；单按 ←/→ 上一帧/下一帧，按住空格播放、松开停，+/− 或倍速选择控制按住时速度，S 暂停并保存截图；失焦、隐藏、keyup 必须停，编辑输入时不抢键。模式可退出恢复平台原操作，原页导航/更换 video 元素须重新绑定。截图不上传、不调用 AI。跨域 canvas 限制须明确报告截图失败，不能声称已保存。

邻帧定位 MUST 以实际流的帧时间表为依据，不用 1/25 或 1/30 秒假冒帧间隔。当前实现通过 document-start/page 用户脚本，观察主页面 MediaSource/SourceBuffer 已有 appendBuffer 的分片 MP4 moov/moof 元数据，不发起媒体请求，不保存/转发 mdat 内容。解析 video 轨道、timescale、trex/tfhd 样本时长、tfdt 解码起点、trun 组合偏移和单项 rate=1 的编辑表，叠加 timestampOffset，以实际 PTS 排序邻帧。只合并解码时间连续的分片，重传替换、初始化/轨道变化清空旧索引；每条来源最多保留120000帧，最多关联8个媒体URL，单元数据box限2MiB，未知/截断/超大/不安全时间值拒绝。

操作目标为真实相邻帧呈现区间内部，必须在已缓冲范围，等待 seeked 与画面呈现回调，验证位置仍在目标帧区间，再报告完成；超时/来源或索引变化拒绝。requestVideoFrameCallback 在此用作画面呈现信号，不把其暂停跳转时的 mediaTime 作为真实源帧 PTS（隔离 Zen 实测该值可能直接等于请求时间）。变帧率和 B 帧按解析的实际时间处理；负速率不作为连续倒放保证。按住播放后松键先立即pause，再定位到缓冲时间表中邻近的真实帧区间并等待呈现，建立明确的暂停帧，避免 Zen 自然暂停的屏幕画面与 currentTime 可能差一帧。每次只运行一个逐帧操作，重复键不累积无界队列；失焦、隐藏、更换 video、退出模式取消操作并暂停，模式退出后不由旧异步操作重新暂停原播放器。

## 实现范围与验证结论

0.2.0 的单轨道分片 MP4 邻帧及按住播放/调速/截图已实现。要求用户安装后刷新原页、以page上下文足够早运行；未捕获初始化、Worker缓冲、非MP4、sequence模式、裁剪窗口、复杂编辑表、缺失相邻分片/未缓冲帧，均报告不可用，不猜帧或静默跳秒。公开规格/测试不保存真实字幕、封面、Cookie或原视频。真实 B 站安装后确认独立于本机合成媒体程序验证。


## 全量源采集

`collect --max-pending 10 --interval 60`在pending上限退出；增加`--watch`则等待AI输出导入后继续采集。仅queued可自动准备，waiting_extract检查点与published不重取；缺字幕skipped，其他错误failed并停止。独立`.collector.lock`防重复采集，普通写锁每条结束后释放；导入与采集冲突时等待，不绕过锁。`ROOT/collect.stop`存在时在当前请求结束的检查点退出；移除停止标记再执行collect可续跑。后台不运行模型或下载视频，全量完成必须按实际菜谱发布及失败/跳过对账判断。
