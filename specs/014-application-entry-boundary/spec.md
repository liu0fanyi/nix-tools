# 应用入口/Caddy边界配套装配

产品权威：`/data/project/tag-all/specs/027-application-entry-boundary/`。
本仓只负责现用路由/TLS/认证来源库存、候选与服务装配、保留外部入口/独立应用和可预演更新回退；不复制Rust应用业务。
跨仓计数沿用产品E1–E5，共5步；E1/E2已验收；E3.a启动包装及E3.b PC候选已验收，NUC候选也已验收，更新/回退预演仍待完成。

## 现状与保持项

PC5006为原生Caddy应用分流，私人5009同进程提供TLS；目标移除普通网页的必要Caddy依赖，私人TLS辅助保持。
NUC5006主区Basic、5008只读Basic、5009同时私人节点/公网源站、5443外部只读；
5009按Host/来源/路径分流，不能整站改免认证上游。原5008/5443凭据复用不在本项静默改变。
Caddy外部站点保留Authelia二次验证、TLS/CA/续期、EdgeOne可信代理、真实来源过滤、ttyd与其他站点。
Bevy、quick-note等独立构建/发布白名单不变；核心/文件Unix上游不得公开，原生DB/身份/CA与新写入回退保持。

## 配套实施边界

E2由产品实现同进程应用入口；E3本仓生成本地TCP/受信web与peer Unix装配，简化Caddy业务重写。
每受信Unix入口私有目录700/限定listener角色，不接受普通客户端伪造forwarded/管理员/设备头。
独立应用/终端保留外部委托，上游安装时固定，不允许用户提供任意URL；避免代理回同一入口形成循环。
E4用自有端口/配置/身份验证真实组合，E5实际更新按已保存编辑/任务安全及固定入口预演。
PC系统激活仍由用户执行，NUC不NixOS switch；不触碰Aliyun、其他站点、模型或秘密发行。

产品027的E3内部清单统一为a启动包装、b PC候选、c NUC候选、d更新/回退预演。
当前E3内部3/4、剩余d一项；整体2/5，下一步NUC候选。生产未变。

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
