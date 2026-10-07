# 精简菜谱与原网页键盘浏览契约

新入口 recipe-simple，独立 ROOT，唯一处理链：平台 ai-zh 字幕与原视频封面 → 单次 AI 材料/用量/制作过程提取 → HTML/JSON/食材目录。不下载视频/音频、不 OCR、不切片、不抽图、不执行独立文本/视觉复审，不包含视频释放或人工认证门槛。旧流程、旧档案及原视频保留。缺中文 AI 字幕 skipped；风控/网络/登录/封面错误 failed 可 retry；每条检查点可续跑，单写者。

AI 返回 title、ingredients[{name,amount:null|string,optional:boolean}]、steps[{text,cue_ids}]、notes。用量不明用 null，误识别保留 notes，不为凑材料或过程猜数字；替代食材 optional=true 并在过程/notes注明替代条件。Schema 见 video-recipe-simple.schema.json，控制器验证引用真实、非空、时间顺序，按引用脚本生成每步原视频时间范围。不再生成事实图谱、逐项 review 记录或 frame 候选。菜谱统一标“AI 字幕整理”，不冒称已独立或人工核验。

AI 输入包 task_id/input_sha256/source/transcript/prompt/result_schema；结果信封仅 task_id/input_sha256/processor/model/result。来源和字幕、封面 SHA 绑定；重复导入幂等，过期/修改输入拒绝。SQLite 仅保存进度，静态目录使用 JSON/现有食材词典，保留原名/未知/可选标记；本轮不新增强制 AI 词典全库复审。平台元数据在新 ROOT 裁为获取封面和字幕所需字段，不保存视频格式/CDN播放URL。

只读本地预览仅允许 library 的普通文件，不暴露 Cookie/SQLite/平台元数据/任务包。目录展示视频原封面，菜谱为材料和步骤，每步链接 B 站原视频相应时间，保持材料检索。封面是原封面，不声称画面选图。播放器增强不把原视频流代理或复制到菜谱服务。

## 用户确认的键盘浏览语义

逐帧模式默认暂停；单按 ←/→ 上一帧/下一帧，按住空格播放、松开停，+/− 或倍速选择控制按住时速度，S 暂停并保存截图；失焦、隐藏、keyup 必须停，编辑输入时不抢键。模式可退出恢复平台原操作，原页导航/更换 video 元素须重新绑定。截图不上传、不调用 AI。跨域 canvas 限制须明确报告截图失败，不能声称已保存。

真正下一帧使用浏览器 seekToNextFrame 与 requestVideoFrameCallback；上一帧按实际呈现时间戳定位，必要时向前重新逐帧解码找邻帧，不用 1/25 或 1/30 秒假冒帧间隔，不宣称固定秒跳转等于逐帧。不支持 API、无法取得实际时间戳、解码/缓冲超时应拒绝准确逐帧并解释；按住播放仍可用。变帧率按实际 PTS 处理，浏览器原生负速率不作为连续倒放保证。此版是用户脚本原型，真实 B 站安装后确认独立于本机合成媒体功能验证。

## 本轮实现范围与验证结论

精简流程及按住播放/截图原型已实现。隔离 Zen 实测没有 seekToNextFrame，requestVideoFrameCallback 可用；不能据此保证相邻帧定位。当前脚本在无 API 时明确拒绝 →，← 始终提示尚未实现；没有固定跳秒回退。真实相邻帧仍为 S3 未完成项。后续需研究原视频帧时间索引／解码能力，不宣称可用旧原生 API 已解决 Zen 的逐帧需求。
