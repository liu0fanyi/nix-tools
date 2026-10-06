# 视频菜谱规范的使用

规范版本为1.0.0。当前提供规则与模型接口，不是已经可运行的自动菜谱流水线；现有可执行工具仍是[字幕OCR](subtitle-ocr.md)。

## 入口

- [处理与验收契约](../specs/010-host-configuration/contracts/video-recipe.md)：事实依据、替代关系、选图及最终输出要求。
- [内部菜谱JSON Schema](../specs/010-host-configuration/contracts/video-recipe.schema.json)：唯一事实源的数据结构。
- [阶段JSON Schema](../specs/010-host-configuration/contracts/video-recipe-stage.schema.json)：核对、选图和修复响应。
- [模型任务模板](../specs/010-host-configuration/contracts/video-recipe-prompts.md)：文本整理、独立审阅、视觉选图、修复。
- [局部真实示例](../specs/010-host-configuration/contracts/video-recipe.example.json)与[原字幕摘录](../specs/010-host-configuration/contracts/transcript.example.json)：砂锅豆腐“开锅后6分钟”，不是完整菜谱。

使用时将契约、对应任务模板、数据结构和实际字幕/图片一起提供给模型。文本整理先输出draft；随后程序核验引用和数值，独立模型核对语义，脚本抽帧、视觉模型选图，最后程序决定状态并套模板。没有提供图片就不能执行视觉核对。云端或本地模型及费用限制另行配置，不因本规范制定而发起调用。

局部示例中的原始字幕与图片位于用户Downloads的“Bilibili/老东北美食 [514273130]/菜谱样稿/砂锅豆腐/”，图片只引用而不复制进Git。原来左文右图HTML保持原样，未将其当作新契约的完整验收实例。

## 实现时的固定顺序

1. 登记输入、哈希、字幕来源及实际覆盖范围；保留原字幕。
2. AI读取全片或分块合并，输出带证据的内部菜谱draft。
3. 程序检查Schema/引用；独立语义核对数字、食材替代、顺序和遗漏。
4. 按步骤区间抽候选帧，视觉核对与选图；疑点保留，必要时限次修复。
5. 程序汇总ready/needs_review，固定模板生成HTML与Recipe JSON及review、manifest。
6. 对10个不同菜式作真实验收，再评估批量处理。规范阶段不自动删除视频，不重启已停下载。

## 如何查看与修改

字段/提示词/选图策略改变时更新规范版本，记录影响，重新核验示例并与对应任务保持一致。内部Schema与语义规则都要通过，单独JSON合法不能证明菜谱正确；ready不表示人工校对。阅读版把“未明确”和疑点直接呈现，开发参数放manifest。

## 不依赖聊天持续运行

完成实现后，独立控制器遇到AI阶段才调用本地模型服务或云端API，结果落盘后继续，关闭聊天不会中断控制器。它需要的是独立的模型访问配置，不是当前对话的上下文。需要接入的配置包括文本/视觉后端、凭证、预算及上传范围；规范里已经定义适配器、检查点、拒绝/超时/限额处理。目前没有创建菜谱后台服务或开始模型付费调用。
