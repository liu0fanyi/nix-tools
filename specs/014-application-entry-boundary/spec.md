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
此前阶段记录（当前以文末E3.d与E4清单为准）：当前E3内部3/4、剩余d一项；整体2/5，下一步NUC候选。生产未变。

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

当前E3内部4/4、剩余0；整体3/5完成，剩余E4、E5两项。下一步E4.c/C1。

## E4 固定结束清单

以下三项展开既有E4，不新增总体阶段；按未完成项计数，不把整个E4报告成一步。

| 项目 | 结束条件 | 状态 |
| --- | --- | --- |
| E4.a | 真实入口与信任链：最终候选组合验证PC直连、NUC主/只读入口、Caddy/Authelia、HAProxy双协议、TLS/来源/伪造头及OPTIONS兼容。 | 已验收 |
| E4.b | 安装能力与隔离：同一候选验证真实只读命名空间、前端阅读/处理、独立应用、终端及既有设备/节点能力；保持各产品发布白名单。 | 已验收 |
| E4.c | 固定最终组合与恢复：复核源码/制品/配置一致，真实组合故障与新数据/身份保持回退，固定证据并提交镜像后完成E4。 | 未完成 |

E4当前2/3、剩余E4.c；E5正式切换在三项通过后开始，实际公网二次验证另留用户确认。


## E4.a 真实入口与信任链已验收

产品027的 固定证据 `tag-all/specs/027-application-entry-boundary/entry-trust-results.json` 记录本项；基础设施实现为
`just check-application-trust /data/project/tag-all`。命令由随机自有临时用户单元执行，
在真实子UID/GID映射下使用独立Podman VFS，只读导出已有固定网关镜像，精确清理本轮资源。
不修改默认Podman存储、不迁移容器、不激活生产服务、不读取现网DB/凭据/CA或用户profile。

8组真实组合通过：主/只读应用Basic与Host拒绝；Caddy内部临时CA的可信/不可信TLS；
Authelia密码加TOTP（二次验证前拒绝）；真实admins身份管理成功、users伪造管理头被拒绝；
现用完整ID的HAProxy镜像在同一端口分流HTTP/HTTPS，两条链均认证且写操作405；
私人peer白名单；四种已认证同源OPTIONS返回200、跨站Origin拒绝；Caddy及应用来源限制拒绝伪造转发头。
PC相同最终包的7项直连/私人TLS门槛及6组候选渲染拒绝回归再次通过。
Rust二进制未变，继续使用E2完整tester产物。

实测修复仅在opt-in候选渲染器：公网网页OPTIONS经过Authelia认证，确保应用外部socket收到
可信身份；未登录请求仍拒绝、跨站Origin仍拒绝，peer/device原有独立路径保持。
旧配置跳过OPTIONS认证会使已登录预检401，修复后200。基础设施默认生产渲染未改变。
这里验证的是已有管理接口权限；普通已认证用户的标签操作不另增管理员限制。

Authelia使用产品锁中的原生4.39.20，与固定现用镜像版本核对一致；HAProxy使用现用固定镜像，
Caddy使用固定2.11.4原生测试程序；只有listener/路径/合成秘密与临时CA替换。
完整安装命名空间与最终固定容器组合在E4.b/c复验，现网登录、CA与公网二次验证仍归E5。
E3.d库存证据保持历史来源；本轮候选认证渲染摘要单独记录，E4.c统一冻结最终源码/配置。

E4.a结束时1/3；当前以文末E4.b验收及E4.c三组门槛为准。
整体仍3/5，E4全部通过后进入E5受控切换。

## E4.b 安装能力与隔离已验收

`tag-all/specs/027-application-entry-boundary/entry-installed-results.json` 固定同一E2完整tester的二进制、7个实际NUC候选单元、
测试源码及浏览器/前端资产摘要。产品仓 `just check-application-installed` 使用随机临时单元和自有双区状态；
保持实际依赖、PrivateUsers、BindPaths/BindReadOnlyPaths、ReadOnlyPaths和凭据检查，
仅替换测试路径、端口/Host及单元名。PC入口/私人TLS继续使用E4.a同包证据，完整恢复归E4.c。

9组通过：真实7单元及两个独立工具运行时；核心单元ExecStartPost在同样挂载策略的命名空间中直接写入，
只读源和七个独立应用均以EROFS拒绝；主区可写/只读405；双区PDF/EPUB处理及主区解压；
独立应用受认证读取、不可写且只读区不暴露；真实ttyd固定Unix委托及只读拒绝；
设备令牌和非法Bearer拒绝、真实PCM worker加Whisper/公开模型处理合成语音；
真实视频转码、原文件保持及Range/206；安装实例通过真实peer socket完成双边批准、
私有CA签名同步、重放拒绝、远端文本/流；实际前端PDF可检索文本/控件、EPUB文本、视频解码和ttyd WebSocket。

浏览器使用独立测试profile、独立文件页面并阻止外站请求；不以此声称同页面PDF→EPUB切换已验收。
独立应用使用自有内容夹具，验证真实绑定/路由和系统只读权限，不代替七个独立产品的功能测试；
没有复制、移动、重建或发布Bevy/quick-note资产。全部测试单元、worker存储与夹具已核对清理。
Rust与生产前后端/代理/DB/CA/身份未改变；本轮新增的是可复用安装验收门槛，不是正式切换。

E4.b完成、剩余0；E4当前2/3，剩余E4.c。整体仍3/5，E4全部完成后进入E5受控发布。

### E4.c 的固定三组门槛

下列三组只展开原E4.c，不新增能力或扩大生产授权；后续逐组汇报，避免把长阶段反复称为一步。

1. **C1 未完成**：冻结最终PC/NUC源码、制品、实际配置输入及保留容器完整ID，核对一致性与回退库存。
2. **C2 未完成**：用固定最终组合完成故障/依赖恢复，包含保留代理容器与安装单元，核对认证/只读边界。
3. **C3 未完成**：同一新DB/metadata/CA/身份下更新→回退→再次更新，保留新增/删除结果，固定证据、提交镜像。

E4.c当前0/3，剩余3组；下一步C1。实际生产切换/公网二次验证仍属于E5。
