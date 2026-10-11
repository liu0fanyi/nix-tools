# 跨仓统一清单（权威计数为tag-all027）

- [x] E1 冻结实际入口/信任/路由及产品契约，完成基础设施职责核对。
- [x] E2 产品完成Rust应用入口，本仓不复制业务。
- [x] E3 本仓完成PC/NUC候选、外部入口适配与更新/回退预演。
- [ ] E4 真实最终组合及来源/认证/只读/新状态回退通过。
- [ ] E5 受控发布验收、结果与两仓规格提交镜像收尾。

此前阶段记录（当前以文末E3.d与E4清单为准）：当前2/5完成、剩余E3/E4/E5三项，下一步E3.d；沿用产品编号，不相加重复计数。

## E3内部清单（产品027权威）

| 项目 | 状态 |
| --- | --- |
| E3.a 应用启动包装 | 已验收；产品027/entry-package-results.json |
| E3.b PC候选 | 已验收；产品027/entry-pc-candidate-results.json |
| E3.c NUC候选 | 已验收；产品027/entry-nuc-candidate-results.json |
| E3.d 更新及回退预演 | 已验收；产品027/entry-update-results.json |

此前阶段记录（当前以文末E3.d与E4清单为准）：E3内部3/4、剩余d一项；模块新增默认停用的应用候选，生产入口未变。

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

此前阶段记录（当前以文末E3.d与E4清单为准）：E3内部3/4，剩余1项E3.d：固定候选库存、运行期600配置/700父目录与应用绑定目标、
完整Compose及HAProxy合并预演、更新/回退保持最新DB和身份；本项不激活服务。
此前阶段记录（当前以文末E3.d与E4清单为准）：整体2/5，剩余E3/E4/E5。E4保留真实认证/TLS/OPTIONS、只读命名空间/终端/独立应用验证。
产品027/entry-nuc-candidate-results.json为跨仓固定证据；生产服务、配置和数据未改变。

## E3.d 收尾：更新与回退预演已验收

产品固定证据为 `tag-all/specs/027-application-entry-boundary/entry-update-results.json`。
`nix-tools` 执行 `just check-application-update /data/project/tag-all`：只读核对NUC固定9个容器的
归属、完整镜像ID、运行/重启状态；丢弃inspect中的环境及命令，不读取生产DB或凭据。
同一E2二进制的PC完整系统/HM候选已刷新，与NUC包一致；源码摘要、7个NUC单元、
入口模板、现用PC系统及025已验收NUC回退候选固定在证据中。

8项隔离门槛及6组辅助负例通过：私有700父目录/600配置、完整Compose实际provider合并与
再次解析、启动控制摘要重绑定、PC/NUC主区/只读区串行旧CLI→应用入口→旧CLI回退→再次更新。
同一DB inode及新标签保留、删除标签未复活；合成metadata、CA及身份哨兵文件保持。
未恢复旧DB/metadata/CA，没有双writer；真实证书链及安装权限不以哨兵检查代替。
完整Compose只保留Caddy/Authelia/只读网关/DDNS，移除旧业务依赖及管理员环境加载/秘密挂载；
Caddy不再发布5006，原PKI挂载、Authelia/DDNS配置、网络及5008双协议传输保持。
原5个业务容器仅核对已停止且restart=no，本轮没有删除或重建容器。

生成配置与Compose摘要仅对应自有合成路径，不是已安装生产配置。
更新/回退辅助函数只生成受控计划，不执行停服/激活；E5仍须重新渲染实际配置、核对摘要、
确认编辑已保存并按原边界执行。PC系统switch仍由用户操作，NUC不执行NixOS switch。
本轮未替换生产入口、未访问生产DB/CA/身份；临时进程及目录已清理。

当前E3内部4/4、剩余0；整体3/5完成，剩余E4、E5两项。下一步E4.a。

## E4 固定结束清单

以下三项展开既有E4，不新增总体阶段；按未完成项计数，不把整个E4报告成一步。

| 项目 | 结束条件 | 状态 |
| --- | --- | --- |
| E4.a | 真实入口与信任链：最终候选组合验证PC直连、NUC主/只读入口、Caddy/Authelia、HAProxy双协议、TLS/来源/伪造头及OPTIONS兼容。 | 未完成 |
| E4.b | 安装能力与隔离：同一候选验证真实只读命名空间、前端阅读/处理、独立应用、终端及既有设备/节点能力；保持各产品发布白名单。 | 未完成 |
| E4.c | 固定最终组合与恢复：复核源码/制品/配置一致，真实组合故障与新数据/身份保持回退，固定证据并提交镜像后完成E4。 | 未完成 |

E4当前0/3、剩余3项；E5正式切换在三项通过后开始，实际公网二次验证另留用户确认。
