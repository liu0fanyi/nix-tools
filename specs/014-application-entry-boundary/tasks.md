# 跨仓统一清单（权威计数为tag-all027）

- [x] E1 冻结实际入口/信任/路由及产品契约，完成基础设施职责核对。
- [x] E2 产品完成Rust应用入口，本仓不复制业务。
- [ ] E3 本仓完成PC/NUC候选、外部入口适配与更新/回退预演。
- [ ] E4 真实最终组合及来源/认证/只读/新状态回退通过。
- [ ] E5 受控发布验收、结果与两仓规格提交镜像收尾。

当前2/5完成、剩余E3/E4/E5三项，下一步E3.d；沿用产品编号，不相加重复计数。

## E3内部清单（产品027权威）

| 项目 | 状态 |
| --- | --- |
| E3.a 应用启动包装 | 已验收；产品027/entry-package-results.json |
| E3.b PC候选 | 已验收；产品027/entry-pc-candidate-results.json |
| E3.c NUC候选 | 已验收；产品027/entry-nuc-candidate-results.json |
| E3.d 更新及回退预演 | 未完成 |

E3内部3/4、剩余d一项；模块新增默认停用的应用候选，生产入口未变。

## E3.c候选与当前结束位置

`just check-application-nuc /data/project/tag-all /data/project/dufs-plus <固定Whisper包>`
构建应用/旧默认候选，校验7/8单元及私有/只读依赖、凭据/模型/应用隔离；
10项生成拒绝测试和6项实际Caddy代理检查通过。代理使用合成认证/Unix后端及临时HTTP，
不代替E4真实Authelia/TLS/Tagall组合。Caddy adapt对照保留TLS、可信代理策略及非本项站点。
双栈实际应用包装、API默认及入口HM生成在产品仓复验通过；Rust未改、复用E2完整tester二进制。

5006由主区应用接管；5008原有HTTP/HTTPS共端口必须保留HAProxy：
HTTP指向固定host.containers.internal:18182认证只读应用，TLS仍指向Caddy5443受信readonly-web。
候选profile替换输入（不叠加ports），删除Caddy发布5006，保留只读5008与私人5009；
HAProxy固定host-gateway解析，应用18182只允许原容器/loopback来源及客户端5008 Host。
5009保留Authelia、设备/peer及真实来源限制，只委托固定私有socket；不复制业务路由。
身份头在显式route中先清理后认证；只读认证身份不再同时被header_up删除。
独立应用仍由各自dist发布，通过只读绑定到工作区外固定根，不改发布归属。

E3内部3/4，剩余1项E3.d：固定候选库存、运行期600配置/700父目录与应用绑定目标、
完整Compose及HAProxy合并预演、更新/回退保持最新DB和身份；本项不激活服务。
整体2/5，剩余E3/E4/E5。E4保留真实认证/TLS/OPTIONS、只读命名空间/终端/独立应用验证。
产品027/entry-nuc-candidate-results.json为跨仓固定证据；生产服务、配置和数据未改变。
