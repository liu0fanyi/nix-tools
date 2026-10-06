# 菜谱模型配置与执行

入口为 `scripts/recipe-batch ... model-run`；使用 Responses 协议，不依赖聊天进程。推荐十道菜先共用一个支持图片的多模态模型，分别执行 extract（完整字幕整理）、review（独立食材/事实/疑点审阅）、vision（候选画面选图）和 repair（受限修复）。OCR继续本地运行，不需要额外OCR模型。

[配置样例](../config/recipe/model.example.json)使用 `gpt-6.1-sol`；模型和价格需在实际启用时核对[官方模型说明](https://developers.openai.com/api/docs/models)。样例允许的上传范围为false，预算为0，不会自动付费。当前真实服务尚未配置，十道菜独立复核仍待执行。模拟服务测试仅证明请求、状态、恢复与校验流程，不证明菜谱语义质量。

## 配置

将样例复制到用户运行目录的 model.json。填写 endpoint、四阶段 models、已验证支持图片的 vision_models；保留实际使用的协议responses。支持HTTPS，或本机回环HTTP服务；本地服务也必须实现 Responses 与严格JSON Schema输出，其他接口尚未适配。不同阶段共用模型即可。review的调用只使用本次材料与提示词，没有整理调用的聊天历史。

凭证通过 api_key_env 指定的环境变量读取，例如 RECIPE_API_KEY。不要写进配置或Git。api_key_env=null用于确实无需认证的本地接口。云端执行需明确启用 allow_text/allow_images，分别允许发送完整字幕/来源/菜谱材料与候选图片；没有图片上传权限会在视觉阶段暂停。运行记录及响应留在queue，不镜像到NUC。

max_total_usd和max_video_usd分别是批次与单视频的记账额度。input_usd_per_million、output_usd_per_million填实际提供商费率；多模型共用配置时填各模型最高单价，以保守估算。示例费率为2026-10-06官方Sol输入2美元/百万token、输出10美元/百万token。费用按返回usage估算，缓存优惠不计入，不能代替账单或服务商消费上限。每个请求先按max_input_tokens与max_output_tokens预留额度；预算必须能容纳整笔预留。已发请求保留当时费率与token上限，改配置不会追溯重算旧请求。

文本token上限按UTF-8字节数保守计算，图片使用每张image_token_ceiling估算；这不是提供商tokenizer。超出上限会暂停，不截断完整字幕。若实际usage超过预留或配置上限，则记录用量并暂停；严格账单上限需在服务商账户设置。费用未知时保留预留额度。

## 预览与运行

在仓库目录执行，替换Q和配置路径：

```bash
Q='/absolute/path/to/private/queue'
CFG='/absolute/path/to/private/model.json'
scripts/recipe-batch --queue "$Q" model-run --config "$CFG"
scripts/recipe-batch --queue "$Q" model-run --config "$CFG" --execute --max-calls 1
scripts/recipe-batch --queue "$Q" status --summary
```

默认仅预览，不读密钥、不发送请求；会推进本地阶段并绑定模型配置，改变接口/模型或适配器代码会使受影响的AI阶段重算。预览列出模型、图片数、输入估算和每次预留额度。execute必须显式给出；max-calls限制本次新增请求数量，含重试，不代表视频数量。先单次核验，再调大限额。该命令前台执行；用户可放入自己的终端后台管理，当前不创建常驻服务。

成功响应先保存不可变响应目录与摘要，后登记usage并导入本地完整Schema/证据校验；中断后能恢复已落盘响应，不重复调用。429/5xx和不合格结果最多3次尝试并退避；每次均记账。超时或连接失败的请求可能已被服务端接收，因此保留预留并暂停，不自动重复。认证、拒绝、缺usage、超出额度等也暂停；需核对提供商请求结果或配置后处理，retry仅重试本地job，不能清除未知付费请求。没有自动账单对账/强制重发命令。

## 内容审阅与修复

新审阅必须完整覆盖每个事实、每个食材和既有疑点；明确未给用量仍保持未知。修复只能修改已请求目标的白名单字段，不能修改来源、字幕、图片登记、运行记录或人工校对标志。每次修复必须再次独立审阅，文本/视觉各最多两次；仍需修复则保留疑点。

视觉观察由程序转换为实际候选帧的时间证据与待核对疑点，再独立审阅；观察不会直接覆盖原事实。缺图不能在没有实际选中图片时被宣布解决。最终status由程序根据未解决问题计算，human_reviewed保持false。旧v1审阅示例仍可读取，但不能作为新控制器的完整食材审阅。
