# 跨仓统一清单（权威计数为tag-all027）

- [x] E1 冻结实际入口/信任/路由及产品契约，完成基础设施职责核对。
- [x] E2 产品完成Rust应用入口，本仓不复制业务。
- [x] E3 本仓完成PC/NUC候选、外部入口适配与更新/回退预演。
- [x] E4 真实最终组合及来源/认证/只读/新状态回退通过。
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

E3内部4/4、剩余0；当前整体4/5，剩余E5。下一步E5/P1。

## E4 固定结束清单

以下三项展开既有E4，不新增总体阶段；按未完成项计数，不把整个E4报告成一步。

| 项目 | 结束条件 | 状态 |
| --- | --- | --- |
| E4.a | 真实入口与信任链：最终候选组合验证PC直连、NUC主/只读入口、Caddy/Authelia、HAProxy双协议、TLS/来源/伪造头及OPTIONS兼容。 | 已验收 |
| E4.b | 安装能力与隔离：同一候选验证真实只读命名空间、前端阅读/处理、独立应用、终端及既有设备/节点能力；保持各产品发布白名单。 | 已验收 |
| E4.c | 固定最终组合与恢复：复核源码/制品/配置一致，真实组合故障与新数据/身份保持回退，固定证据并提交镜像后完成E4。 | 已验收 |

E4当前3/3、剩余0；正式切换进入E5，实际公网二次验证另留用户确认。


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

E4.b完成、剩余0；当前E4状态见文末C3收尾，下一步E5/P1。

### E4.c 的固定三组门槛

下列三组只展开原E4.c，不新增能力或扩大生产授权；后续逐组汇报，避免把长阶段反复称为一步。

1. **C1 已验收**：冻结最终PC/NUC源码、制品、实际配置输入及保留容器完整ID，核对一致性与回退库存。
2. **C2 已验收**：用固定最终组合完成故障/依赖恢复，包含保留代理容器与安装单元，核对认证/只读边界。
3. **C3 已验收**：同一新DB/metadata/CA/身份下更新→回退→再次更新，保留新增/删除结果，固定证据、提交镜像。

E4.c当前3/3、剩余0；E4完成，下一步E5/P1。实际生产切换/公网二次验证仍属于E5。


## E4.c/C1 最终库存已冻结

权威证据为产品027的 `entry-inventory-results.json`；执行入口为产品 `python3 scripts/check-application-inventory.py`。
重新核对8个store候选/回退/前端闭包存在、包装文件、PC的6个相关单元及NUC的7个单元/入口模板、
工具归档与前端资产SHA；当前PC系统与E3.d回退系统一致。九个固定NUC容器只返回完整ID、镜像、归属、
运行及重启字段，四个保留代理运行，五个旧业务容器停止且restart=no，没有访问生产数据或认证内容。

固定PC以E3.d刷新候选为准；OPTIONS渲染修正以E4.a验收摘要为准，早期摘要保留来源记录。
除此之外运行/构建源文件均匹配原证据；无关桌面锁/配置变更不用于重建或替换本轮候选。
运行期秘密未读；E5必须针对实际配置重新绑定摘要，不能把合成配置摘要当作生产安装凭证。
本轮没有stop/start/restart、系统switch或生产写入；新完整代理执行/依赖故障恢复仍属C2。

C1完成、剩余0；当前剩余清单以下述C2收尾为准。


## E4.c/C2 最终组合故障恢复已验收

权威证据为产品027的 `entry-recovery-results.json`；产品 `python3 scripts/check-application-recovery.py`
绑定C1库存，运行实际保留Caddy/Authelia/HAProxy完整镜像和7个随机候选单元。
独立VFS、合成用户/密码/TOTP/CA/端口，代理仅挂所需自有配置、认证状态和socket，不挂DB/工作区。
候选保持实际PrivateUsers、挂载、依赖和target；不访问现网认证/CA/数据或用户profile。

11组通过：主/只读基本权限；实际二次认证、admins管理/users伪造头拒绝、HTTP/TLS同端口只读；
三个代理分别SIGKILL后显式重开；双区core/files/tools六个单元分别SIGKILL后原target恢复。
每次检查同一DB inode、新增标签、节点身份、认证/只读边界，CA字节保持；
tools故障明确等待BindsTo核心新PID，双区实际选定PDF worker再次完成信息读取和JPEG渲染。
容许有界暂时断连，但须等待整条认证/双协议链就绪；Authelia内存会话重启后重新完成密码/TOTP登录。

合成镜像根为只读；Authelia启动所需健康文件单独自有可写挂载，Caddy执行所需NET_BIND_SERVICE保留。
独立VFS关闭镜像健康调度，以实际HTTP检查，不关闭Authelia其他启动检查；未改变生产安全配置。
早期夹具失败不计通过，未启动容器残留已按完整ID/日志精确清理，最终自有单元/容器/存储均已清理。
DDNS仅沿C1保留，不执行会写外部DNS的测试；PC入口/TLS分离沿用E4.a同冻结制品证明。
没有生产部署、stop/start/restart、系统switch；真实LAN/公网与生产登录仍留E5。

C2完成、剩余0；当前E4状态见下述C3收尾。


## E4.c/C3 真实状态更新与回退已验收

权威证据为产品027的 `entry-handover-results.json`；产品 `python3 scripts/check-application-handover.py`
绑定原完整tester的应用/旧025二进制、C1库存、C2恢复和本轮源码。
5组通过：PC/NUC主区/只读区旧CLI→应用→回退→再次更新；实际7个NUC候选单元双区状态
交给旧CLI后重开同一target；真实CA证书/私钥不变、同一DB inode及各次SQLite integrity检查。

PC/主区实际双方TLS批准，先同步待删标签，再删除；更新/回退后真实签名同步及重放拒绝通过，
新增和回退新增保留、双方删除不复活，真实私钥/指纹/paired-peers与设备凭据有效性保持。
只读新入口保持同步关闭、配对403与写405，不为了验收开放权限；已有状态保留。
安装主区真实身份、设备凭据、新增/删除与回退新增保留；安装只读区原来没有身份，保持缺省。
旧CLI状态兼容和最终安装target重开分别实测；不声称实际旧OS代全部单元已激活。
保留代理恢复/权限继续绑定C2证据，DDNS不在夹具执行。

只使用自有随机状态、临时CA/密钥/凭据/端口/单元和私有VFS；所有自有进程/单元/存储已核对清理。
Podman退出后的空锁目录按固定白名单清理，早期夹具失败不计通过。
没有改Rust、生产配置/DB/CA/身份/容器/默认存储，不执行系统switch或覆盖独立产品dist。

C3完成、剩余0；E4.c三组3/3、E4三项3/3，E4完成、剩余0。总体4/5，剩余E5受控发布。
下一步E5/P1准备真实运行期配置、备份/回退与发布预演；停服仍须重新确认编辑已保存。


## E5 固定发布结束清单

这三项展开原E5，不新增功能或扩大切换授权，跨两仓只计同一套编号。

| 项目 | 结束条件 | 状态 |
| --- | --- | --- |
| P1 发布准备 | 重新核对现网库存及实际配置摘要；固定候选/回退、私有凭据与应用挂载；生成备份、传输及切换预演，确认不会恢复旧DB。 | 已完成 |
| P2 受控切入口 | 编辑保存/任务停止重新确认后，按单writer顺序备份与激活；保留当前DB/metadata/CA/身份。PC系统switch由用户执行，NUC不执行NixOS switch。 | PC/NUC均已实际切换，见文末证据 |
| P3 真实验收收尾 | 核验PC/LAN、NUC主/只读、私人TLS/配对及公网Authelia/现有路径；记录未自动验证部分，完成两仓提交与限定镜像。 | 待做 |

E5当前2/3，剩余P3真实验收收尾一项；已确认且执行的本次切换不重复要求确认。


## E5/P1 发布准备完成

权威证据：产品027的 `entry-preparation-results.json` 和 `entry-pc-preparation-results.json`。
本轮核对实际运行期输入摘要和九个固定NUC容器；四个保留代理运行，五个旧业务容器停止且restart=no。
已把固定应用候选200个闭包路径传到NUC，远端narHash/narSize逐路径一致并建立候选GC根；没有远端构建。
在独立700私有发布目录暂存600入口配置、现有bcrypt格式、完整四服务Compose、Caddy/HAProxy及重绑定启动控制。
私有发布目录和文件摘要已复核，实际NUC Compose provider重新解析模型一致；现用控制/配置没有替换。
新Compose保留Authelia/DDNS原配置和PKI挂载，只调整Caddy/只读网关及应用socket委托，移除旧业务依赖及管理令牌加载。

PC当前原生服务活动、运行期node/管理员文件权限及摘要已核对；当前系统仍是固定回退代。
依据已验收候选生成peer socket/authority入口TOML，只暂存于产品.devenv私有目录，不安装到现用config。
PC候选/HM及NUC候选继续使用E4固定制品，不从其他未提交桌面配置重建。
三个负例测试组通过：运行目录内相对挂载解析、越界/命名卷/未知挂载策略拒绝、异常发布端口拒绝。
现网相对haproxy挂载按固定RUNTIME解析，既有绝对绑定保持；没有扩大挂载白名单。

发布准备入口为基础设施 `python3 scripts/prepare-application-entry.py`（只读预演），
显式 `--prepare` 才导入已固定闭包并写全新私有发布目录；它没有stop/start/activate/数据库恢复功能。
产品证据只保存脱敏库存、摘要、制品和暂存位置，凭据不进入源码或Nix store。
P2切换前必须重新核对这些摘要及库存，现网如有变化则拒绝沿用旧预演。

离线备份与切换计划绑定当前双区state、现有Caddy PKI和运行期配置/单元；备份必须在P2停writer后进行。
更新及回退始终使用当前DB/metadata/CA/身份，禁止恢复旧数据库或重新启用旧数据卷。
P2须停用旧bridge，检查被替换端口、配置和单元，以文件/工具先于core启动；
仅需要重建Caddy/只读网关，不主动重建Authelia/DDNS。PC系统switch仍由用户执行，NUC不执行系统switch。
本轮没有读取DB、备份在线数据库、停止服务或改生产入口，P1完成不等于P2获准停服。

P1已完成；E5当前状态与下一步以文末实际切换结果为准。
下一步P2：落实上述具体切换/回退控制，再以可核对结果请求本次编辑保存确认，历史确认不复用。


## E5/P2 控制脚本就绪，等待实际切换

权威证据：产品027 `entry-switch-preflight-results.json`。基础设施新增两个显式激活入口和
配置事务模块；默认只读，不执行stop/apply、不读取生产DB。PC/NUC现网只读预演均通过。
实际变更只暂存了NUC独立700控制器目录（代码644），没有替换现用配置或服务单元。

入口回归28项通过，其中新事务7项、新控制器6项。事务测试使用真实临时SQLite/WAL、
配置、metadata/身份和CA文件；控制器测试中的服务状态和Compose转换为模拟，
不能把这些测试当作已完成现网切换或真实系统激活。此前E4真实安装/恢复门槛继续有效，
本轮没有Rust或冻结候选改动，不重新构建消费者或工具镜像。

NUC控制器重新核对准备目录摘要、原九容器ID/镜像/模式、旧八单元注册、当前控制摘要、
Basic凭据、只读HAProxy转换及处理任务为空；漂移或任务未完成则拒绝。既有非敏感HAProxy
输入为644，只有这个精确无秘密路由兼容600/644，拒绝组可写及符号链接；现用路由例外见文末。
启动锁与独立操作锁不替换inode；持启动排他锁再核对一次输入后才设屏障；先停target再停全部成员/旧bridge和两个冲突入口。
检查单writer锁、单元/容器停止和5006/5008/5009/18182释放后才备份当前双区DB及metadata、
Caddy双PKI目录；配置/单元在切换前单独保存。SQLite以mode=ro读取WAL并检查备份完整性，不使用immutable。
配置事务按精确白名单记录原文件/单元；安装新入口配置、四服务Compose、重绑定控制和七单元，
保留现有启动守卫与peer-network覆盖；文件/工具先于core，随后仅重建Caddy/只读网关。
Authelia/DDNS不主动重建，五个旧业务容器不重新启用、不删除；独立应用只建立只读挂载目标，
不复制、重建或覆盖其产物。

失败保持transition与服务停止，须显式回退。入口重建导致Caddy/网关不存在时可明确识别缺失，
不把任意inspect失败当不存在；旧业务容器缺失仍拒绝。回退仅恢复入口/单元/控制，
继续使用最新DB/metadata/CA/身份。测试已覆盖部分配置安装失败及新writer提交后网关失败的回退。
备份永不自动恢复到现用状态，禁止再次从旧数据卷迁移。

PC控制器仅由用户普通终端执行实际apply/rollback。核对冻结系统代、profile、配置摘要、
入口暂存文件和任务为空；临时移走ready形成启动屏障，停五个作用域单元，离线备份当前
data及peer-caddy。安装入口配置后切到固定已验收系统代，不从未提交桌面改动重建；
失败保留ready屏障和最新数据，不自动重启/回退。切换成功后恢复ready并启动target。
PC部分失败回退只允许固定的新/旧系统代，继续使用相同data；Agent不得执行系统switch。

P2控制脚本及只读预演已完成；实际切换状态以文末“E5/P2 当前状态”及固定现网证据为准。

## E5/P2 当前状态：PC/NUC 已切换

权威证据为产品027 `entry-nuc-activation-results.json`。NUC已经按本次“已保存关闭，可以切换”授权执行；
当前七个原生单元 active、旧 bridge 停用，主区5006由应用入口接管。五个旧业务容器仍停止且restart=no；
Caddy/HAProxy保持外部代理与双协议传输，Authelia/DDNS容器ID、镜像及运行状态不变。
离线备份完整性与摘要通过，两个当前DB inode未变，已有peer身份与四个CA文件字节保持；
没有恢复旧DB/metadata/CA，没有再次迁移旧卷，没有重建消费者、工具镜像或独立应用。

实际切换修正了TIME_WAIT端口误判、失败阶段安全resume、缺失网关/退役bridge恢复、
控制单元退出误杀conmon以及现用Compose对extra_hosts映射的解析差异。resume保留原journal与离线备份，
重启当前状态，不删除记录绕过拒绝；控制器以KillMode=process运行，避免退出时杀死容器监控进程。
原P1配置与manifest仍保存，兼容修复分别记录独立事务。

`workcdn`短暂故障来自HAProxy非root用户无法读取被安装为600的非敏感路由文件；
仅固定无秘密TCP路由允许644，凭据、入口配置、控制文件及私有父目录仍为600/700。
独立启动包装只接受已审核的新/旧路由字节；其他文件仍使用原权限检查和摘要校验。
七份native-startup drop-in及runtime/native-nuc-control仅替换守卫脚本路径，保存逐文件原件；
历史守卫源码与冻结制品未改，保留环境检查、单writer与原guard的完整调度/库存检查。
rootless host-gateway实测来源为NUC本机192.168.1.12，故只读来源列表只增加该IP的/32，
没有开放整个LAN或关闭认证；启动摘要随入口配置重绑定，并分别保存source/permission/startup事务。

NUC本机5006/5008的首页及API均返回401 Basic挑战；PC直连5008亦通过；
公网workcdn返回401挑战、nas返回登录跳转且用户确认正常。只读核心真实重启后仍通过检查。
控制器现在必须验证5006/5008的HTTP认证就绪，不能仅凭容器running判成功；44项回归通过。
单元测试中的服务转换是模拟，现网检查独立记录；公网实际登录/TOTP及业务读写仍归P3。


### PC 切换及开机恢复已验证

PC用户已在普通终端完成固定系统代切换；当前系统和profile一致，事务为activated-awaiting-P3。
`entry-pc-activation-results.json`记录五个原生单元active、实际标签API200、离线备份完整性、
当前DB inode不变、peer身份与四个CA文件字节保持、五个旧容器仍停止。
实际开机暴露了Podman API服务PATH缺少newuidmap和专用工具run/libpod/xdg残留旧boot ID两项；
前者补入/run/wrappers，后者保留旧临时目录副本后恢复。storage、镜像、任务记录和用户文件未删除，
没有migrate/reset/prune，没有重新迁移或恢复数据库。

当前PC已安装两个自有用户服务drop-in：Podman运行PATH修复、工具ExecStartPre的boot守卫。
守卫读取内核boot ID、持原runtime.lock独占锁；同boot不改变目录，跨boot只归档三个明确临时目录，
不触碰storage及执行器/数据库。符号链接、错误权限及运行时占锁拒绝；四项回归通过。
原生栈真实停止/重启后依赖与API均正常，44项既有控制器回归通过。
Nix候选生成的Podman PATH和工具ExecStartPre也已只读求值验证；已安装drop-in使当前系统生效，
不要求用户再运行切换命令。PC控制器成功条件补为服务与实际API同时就绪，避免仅以瞬时active判定。

| 固定剩余项 | 状态与下一步 |
| --- | --- |
| P3：真实验收与收尾 | 核验PC/NUC实际文件阅读编辑和处理、标签同步、公网登录/二次验证、主只读权限及既有独立应用，记录结果后关闭E5。 |

P2完成、剩余0；总体4/5，E5当前2/3，剩余1项P3真实验收与收尾。
下一步可打开Tag Browser试用PC/NUC工作区；不用重复切换脚本。完整阶段在P3验收后关闭。

## PC普通系统更新后的原生服务恢复修复

本故障修复固定3步，不重新打开模块重构清单，不代替原P3人工功能验收。

- [x] H1：定位Home Manager成功更新移除候选原生单元并停栈；旧容器模式守卫保持有效。
- [x] H2：从已验应用入口generation恢复既有归属的持久单元链接，保留版本覆盖/原数据，复验五服务和API。
- [ ] H3：普通liu-bigpc配置声明稳定应用单元及默认启动链接，完整系统构建/边界核验；用户切换后验证激活与恢复。

原因：一次性候选加入了原生HM单元，而普通flake没有它们；早期.local/share持久注册又仍指向应用入口迁移前的网关模板。只检查浏览器系统输出不足以证明HM激活及后台服务恢复。本次明确保留ks216rpf09kfckjx4g06s7xhzpqxvc5m固定应用入口模板、当前80-tag-version/boot守卫及配置数据；不重新迁移、不启用旧容器、不由Agent执行系统switch。

H2已验证：五单元active，位置与标签API200。仅替换原注册收据绑定的.local/share单元链接，旧映射另存，现有80-tag-version覆盖保留；无数据库迁移、备份恢复或旧容器启动。H3剩余1步，完成完整普通系统构建后由用户切换并核验。

H3候选已验证：普通系统完整构建通过，五个原生单元与已验应用入口模板逐字节一致，默认启动链接存在，恢复钩子在reloadSystemd之后且受ready/container-mode保护。结果见pc-native-registration-results.json。当前故障修复剩余1步H3实际用户切换与确认；Agent未执行系统switch，当前五服务及API已恢复。

浏览器nix.33发行已批准并完成，实际PC系统候选与保留原生服务的HM注册共同核验通过；见[tag-browser-nix33-install-results.json](tag-browser-nix33-install-results.json)。仅浏览器输入锁定项进入本次提交，其他既有宿主改动保留。H3仍待用户普通终端switch后的运行核验，与浏览器018的W3人工收尾一并执行，不新增阶段计数。

浏览器nix.34发行已批准并完成，实际PC系统候选与保留原生服务的HM注册共同核验通过；见[tag-browser-nix34-install-results.json](tag-browser-nix34-install-results.json)。仅浏览器输入锁定项进入本次提交，其他既有宿主改动保留。H3仍待用户普通终端switch后的运行核验，与浏览器020的U4试用交付一并执行，不新增阶段计数。

浏览器nix.35发行已批准并完成，实际PC系统候选与保留原生服务的HM注册共同核验通过；见[tag-browser-nix35-install-results.json](tag-browser-nix35-install-results.json)。仅浏览器输入锁定项进入本次提交，其他既有宿主改动保留。H3仍待用户普通终端switch后的运行核验，与浏览器020的I3修正试用交付一并执行，不新增阶段计数。

浏览器nix.36发行已批准并完成，实际PC系统候选与保留原生服务的HM注册共同核验通过；见[tag-browser-nix36-install-results.json](tag-browser-nix36-install-results.json)。仅浏览器输入锁定项进入本次提交，其他既有宿主改动保留。H3仍待用户普通终端switch后的运行核验，与浏览器020的T3共用工具交付一并执行，不新增阶段计数。

浏览器nix.37发行已批准并完成，实际PC系统候选与保留原生服务的HM注册共同核验通过；见[tag-browser-nix37-install-results.json](tag-browser-nix37-install-results.json)。仅浏览器输入锁定项进入本次提交，其他既有宿主改动保留。H3仍待用户普通终端switch后的运行核验，与浏览器021/dufs-plus018的P4工具栏对齐交付一并执行，不新增阶段计数。

浏览器nix.38紧凑筛选栏补发已完成：私有Release/CI/Cachix、完整liu-bigpc候选、菜单版本与五个原生服务注册均核验通过；见[tag-browser-nix38-install-results.json](tag-browser-nix38-install-results.json)。此后端修复已在原生版本事务中完成，浏览器发行不重新切换PC/NUC服务。仅浏览器锁定节点与本条安装证据进入提交，原有用户修改/暂存均保留。对应产品020的CR1/CR2完成，剩1步CR3由用户普通终端rerun并重开确认，Agent未执行系统switch。

浏览器 nix.39 共享 Rust 滚动发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 候选、菜单版本与五个原生服务注册均核验通过；见 [tag-browser-nix39-install-results.json](tag-browser-nix39-install-results.json)。PC/NUC 前端已按本轮保存关闭确认经原生事务激活，后端保持现用版本。仅浏览器锁定节点与安装证据进入本次提交，既有用户修改/暂存均保留。跨仓交付以 dufs-client-rs/004 的 R1/R2 为准：用户普通终端 rerun 重开及三组试用尚未执行，不新增阶段计数。

浏览器 nix.40 操作控制器和共享 Rust 操作模型发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 候选、菜单版本与五个原生服务注册均核验通过；见 [tag-browser-nix40-install-results.json](tag-browser-nix40-install-results.json)。PC/NUC 前端已按本轮保存关闭确认经原生事务激活，后端保持现用版本。仅浏览器锁定节点与安装证据进入本次提交，既有用户修改/暂存均保留。跨仓发行计数以 dufs-client-rs/005 的 P1–P3 为准；用户普通终端 rerun 重开及试用另列，不新增开发项。

浏览器 nix.41 Web 收藏目录首版发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 候选、菜单版本与五个原生服务注册均核验通过；见 [tag-browser-nix41-install-results.json](tag-browser-nix41-install-results.json)。PC/NUC 后端程序已按本轮保存关闭确认经原生事务备份激活，前端和代理保持现用版本。仅浏览器锁定节点与安装证据进入本次提交，既有用户修改/暂存均保留。跨仓发行计数以 tag-browser/024 的 D1–D7/R1–R3 为准；用户普通终端 rerun 重开及试用另列，不新增开发项。

浏览器 nix.42 路径呈现补丁发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 候选、菜单版本与五个原生服务注册均核验通过；见 [tag-browser-nix42-install-results.json](tag-browser-nix42-install-results.json)。本轮仅为顶部共用收藏路径、去重入口与数量呈现的浏览器 UI 补丁；PC/NUC 后端、前端、工具、认证及代理均未停止或更新。仅浏览器锁定节点与安装证据进入本次提交，既有用户修改/暂存均保留。跨仓本轮发布计数以 tag-browser/024 的 P1–P3 为准，既有 R2/R3 仍待用户验收；用户普通终端 rerun 重开及试用另列，不新增开发项。

浏览器 nix.43 统一目录树发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 系统/HM 候选、菜单版本和五个原生服务注册均核验通过，见 [tag-browser-nix43-install-results.json](tag-browser-nix43-install-results.json)。工作区/Web/当前窗口页面共用树，提供全部收起；本次消费者变更仅浏览器锁定节点与安装证据，已有暂存和未暂存修改均保留。本轮 PC/NUC 前端通过既有原生事务独立更新，后端与认证代理不变；事务和实际资源证据在 dufs-plus/023。跨仓固定发布计数以 tag-browser/025 P1–P3 为准；实际系统切换和重开验收由用户执行。

浏览器 nix.44 统一搜索发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 系统/HM 候选、菜单版本和五个原生服务注册均核验通过，见 [tag-browser-nix44-install-results.json](tag-browser-nix44-install-results.json)。收藏、当前窗口和所属节点文件搜索共用固定Rust匹配，同时交付侧栏控件精简；本次消费者变更仅浏览器锁定节点与安装证据，已有暂存和未暂存修改均保留。本轮 PC/NUC 前后端通过既有原生事务更新，认证代理不变；事务和实际资源证据在 dufs-plus/024与tag-all/032。跨仓固定发布计数以 tag-browser/026 D1–D2 为准；实际系统切换和重开验收由用户执行。

浏览器 nix.45 目录展开响应发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 系统/HM 候选、菜单版本和五个原生服务注册均核验通过，见 [tag-browser-nix45-install-results.json](tag-browser-nix45-install-results.json)。目录返回即显示、标签独立补齐，普通收起复用有界窗口缓存，无关工作区不重投影；本次消费者变更仅浏览器锁定节点与安装证据，已有暂存和未暂存修改均保留。本轮 PC/NUC 前端通过既有原生事务更新，认证代理不变；事务和实际资源证据在 dufs-plus/023。跨仓固定发布计数以 tag-browser/025 RP1–RP3 为准；实际系统切换和重开验收由用户执行。

浏览器 nix.46 搜索范围精简与当前项定位发行已完成：私有 Release/CI/Cachix、完整 liu-bigpc 系统/HM 候选、菜单版本和五个原生服务注册均核验通过，见 [tag-browser-nix46-install-results.json](tag-browser-nix46-install-results.json)。仅保留已打开页面/全部，当前目录与搜索范围独立；折叠树保留当前项并提供明确定位；本次消费者变更仅浏览器锁定节点与安装证据，已有暂存和未暂存修改均保留。Todo配套前端已完成PC/NUC仅前端事务并核验备份/真实资源/公网认证，代理不变，证据在dufs-plus/025。联合交付计数以tag-browser/026的R1/R2为准；实际系统切换和重开验收由用户执行。

浏览器 nix.47 搜索覆盖原因提示补正已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix47-install-results.json](tag-browser-nix47-install-results.json)。本次仅更新tag-browser-src与本项安装证据，原有暂存/未暂存改动保持；不创建Pin，不执行系统switch。待办颜色与菜单外关闭已由dufs-plus025独立完成PC/NUC前端切换；浏览器系统安装和关闭旧窗口重开验收仍由用户执行。

浏览器 nix.48 侧栏精简与完整索引兼容补正已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix48-install-results.json](tag-browser-nix48-install-results.json)。本次仅更新tag-browser-src与本项安装证据，原有暂存/未暂存改动保持；不创建Pin，不执行系统switch。本轮不切换PC/NUC原生服务；浏览器系统安装和关闭旧窗口重开验收仍由用户执行。

浏览器 nix.49 跨工作区首次勾选修复已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix49-install-results.json](tag-browser-nix49-install-results.json)。本次仅更新tag-browser-src与本项安装证据，原有暂存/未暂存改动保持；不创建Pin，不执行系统switch。本轮不切换PC/NUC原生服务；浏览器系统安装和关闭旧窗口重开验收仍由用户执行。

浏览器 nix.50 收藏入口与当前项定位已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix50-install-results.json](tag-browser-nix50-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，不切换PC/NUC原生服务；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser027/P1–P3及026/R1。

浏览器 nix.51 PC/Web已打开页面切换性能补正已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix51-install-results.json](tag-browser-nix51-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，不切换PC/NUC原生服务；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser027/UP1–UP3及026/R1。

浏览器 nix.52 收藏内导航关联与更新入口补正已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix52-install-results.json](tag-browser-nix52-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，不切换PC/NUC原生服务；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser027/BP1–BP3及026/R1。

浏览器 nix.53 收藏网址更新响应补正已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix53-install-results.json](tag-browser-nix53-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，不切换PC/NUC原生服务；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser027/UR1–UR3及026/R1。

浏览器 nix.54 筛选/搜索结果当前项高亮补正已发行：私有Release/CI/Cachix精确输出、29份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix54-install-results.json](tag-browser-nix54-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，不切换PC/NUC原生服务；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser027/HR1–HR3及026/R1。

浏览器 nix.55 共享侧栏重构与零TODO验收补正已发行：私有Release/CI/Cachix精确输出、34份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix55-install-results.json](tag-browser-nix55-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，配套PC/NUC前端已由dufs-plus规格另记、现用后端保持；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser029/P1–P4。

浏览器 nix.56 共用 Lucide 工具栏、主动自动标签与本地会话恢复已发行：私有Release/CI/Cachix精确输出、43份正式资源、完整liu-bigpc系统/HM候选及五个原生服务注册均核验；见[tag-browser-nix56-install-results.json](tag-browser-nix56-install-results.json)。PC/NUC仅前端事务已由dufs-plus028记录，后端和认证保持；不创建Pin、不执行系统switch、不另装用户profile。唯一跨仓交付计数归tag-browser033/P1–P4，剩P4用户普通终端安装重开及试用；既有输入法/宿主修改逐文件保持。

浏览器 nix.57 后台页面自动休眠已发行：私有Release/CI/Cachix精确输出、46份正式资源、完整liu-bigpc系统/HM候选及五个原生服务注册均核验；见[tag-browser-nix57-install-results.json](tag-browser-nix57-install-results.json)。本轮仅浏览器，不切换PC/NUC服务；不创建Pin、不执行系统switch、不另装用户profile。唯一交付计数归tag-browser034/R1–R4，剩R4用户普通终端安装重开并检查休眠设置；既有输入法/宿主修改逐文件保持。

浏览器 nix.58 一键全字典自动标签已发行：私有Release/CI/Cachix精确输出、46份正式资源、完整liu-bigpc系统/HM候选及五个原生服务注册均核验；见[tag-browser-nix58-install-results.json](tag-browser-nix58-install-results.json)。本轮仅浏览器，不切换PC/NUC服务；不创建Pin、不执行系统switch、不另装用户profile。唯一交付计数归tag-browser032/P1–P4，剩P4用户普通终端安装重开并检查自动标签简化流程；既有输入法/宿主修改逐文件保持。

浏览器 nix.59 当前浏览统一选择与三列动作已发行：私有Release/CI/Cachix精确输出、46份正式资源、完整liu-bigpc系统/HM候选及五个原生服务注册均核验；见[tag-browser-nix59-install-results.json](tag-browser-nix59-install-results.json)。本轮仅浏览器，不切换PC/NUC服务；不创建Pin、不执行系统switch、不另装用户profile。唯一交付计数归tag-browser027/OP1–OP4，剩OP4用户普通终端安装重开并检查当前浏览选框与三列按钮布局；既有输入法/宿主修改逐文件保持。

浏览器 nix.60 松石绿侧栏与工具能力提示已发行：私有Release/CI/Cachix精确输出、46份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix60-install-results.json](tag-browser-nix60-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，配套PC/NUC前端已由dufs-plus规格另记、现用后端保持；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser007/DL1–DL2。

浏览器 nix.61 Gruvbox Light功能配色已发行：私有Release/CI/Cachix精确输出、46份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix61-install-results.json](tag-browser-nix61-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，本次仅浏览器发行，PC/NUC服务未切换；用户在普通终端安装并关闭旧窗口重开验收，唯一样式交付计数归tag-browser010/G3，用户安装确认归027/OP4。

浏览器 nix.62 关闭状态、前后退与顶部对比修复已发行：私有Release/CI/Cachix精确输出、46份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix62-install-results.json](tag-browser-nix62-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，PC/NUC配套前端按独立固定事务与本轮保存确认切换，保留后端；用户在普通终端安装并关闭旧窗口重开验收，唯一配套交付计数归tag-browser027/NH2，用户安装确认归027/OP4。

浏览器 nix.63 地址栏身份提示配色补正已发行：私有Release/CI/Cachix精确输出、46份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix63-install-results.json](tag-browser-nix63-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，本次仅浏览器发行，PC/NUC服务未切换；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser010/G6，用户安装确认归027/OP4。

默认浏览器修复 nix.64 已发行：启动器原生身份、HTTP/HTTPS/HTML/XHTML 桌面声明、五组隔离检测/设置/重启、CI/Cachix、完整 PC 系统/HM 与实际生成 MIME 均通过，见[tag-browser-nix64-install-results.json](tag-browser-nix64-install-results.json)。仅 liu-bigpc 覆盖默认浏览器，homebox 保持 Zen；五个原生单元及恢复顺序不变。MIME 同步保护接受用户选择的 Tag Browser，保留其他协议锚点。未执行 switch、修改用户 profile 或切换服务；跨仓唯一开发计数为 tag-browser007/DB1–DB2（已完成），用户安装与重开确认仍归027/OP4。

浏览器 nix.65 六处样式细节补正已发行：私有Release/CI/Cachix精确输出、46份包内资源、完整liu-bigpc系统/HM候选、菜单版本与五个原生服务注册均核验，见[tag-browser-nix65-install-results.json](tag-browser-nix65-install-results.json)。本次仅更新tag-browser-src与本项安装证据，不创建Pin、不执行系统switch，本次仅浏览器发行，PC/NUC服务未切换；用户在普通终端安装并关闭旧窗口重开验收，唯一交付计数归tag-browser010/G8，用户安装确认归027/OP4。

浏览器 nix.66 共享组件配色已发行，CI/Cachix精确输出、47份包内资源、完整liu-bigpc系统/HM候选、菜单版本、四项默认浏览器关联与五个原生服务注册核验通过，见[tag-browser-nix66-install-results.json](tag-browser-nix66-install-results.json)。本轮只更新tag-browser-src及本项证据；原有输入法和010任务改动保留并包含在构建候选中，未纳入本轮提交。Agent不执行系统switch；服务程序/前端切换与用户安装进度唯一归tag-browser036。

浏览器nix.67收藏网址冲突补正已发行：297项Node、七组Firefox1842项断言、47份正式资源、CI/Cachix精确输出、完整liu-bigpc系统/HM候选、五个原生模板/恢复顺序与四项默认浏览器关联通过，见[tag-browser-nix67-install-results.json](tag-browser-nix67-install-results.json)。本轮只更新tag-browser-src及本项证据，原有输入法与010任务改动保留且包含在候选中、不纳入本轮提交；不执行系统switch、不切换PC/NUC服务，036配套服务待确认状态不变。发行唯一计数归tag-browser027/UCP1–UCP3，用户安装/重开归027/OP4。

配色配套程序与前端已在用户本轮“可以切换”后通过固定原生事务激活PC/NUC双区，实际程序/前端、离线备份完整性/inode、原认证与公网入口、配色API/schema17核验通过，见[运行验收](account-appearance-activation-results.json)。仅替换程序与前端，未system switch、未恢复旧DB、未修改用户配色或读取凭据/profile。唯一计数归Tag Browser036/R3（已完成），真实窗口确认归036/U1。

nix.68页面样式修正已发行：47份正式资源、297项Node、七组Firefox1842项断言、私有Release/CI/Cachix精确输出和完整liu-bigpc系统/HM候选通过，见[tag-browser-nix68-install-results.json](tag-browser-nix68-install-results.json)。PC/NUC前端按本轮保存确认完成固定事务激活，后端保持原包；实际入口/认证/备份/数据库inode及配色只读接口通过，见[前端激活](account-appearance-polish-activation-results.json)。只更新浏览器固定输入和本项证据，既有输入法/010改动保持并包含在候选、不纳入提交；Agent未system switch。唯一发行计数归Tag Browser036/SP1–SP4（剩余0），用户安装重开与视觉确认归027/OP4、036/U1。

nix.69组件样式与图标修正已发行：47份正式资源、297项Node、七组Firefox1848项断言、私有Release/CI/Cachix精确输出和完整liu-bigpc系统/HM候选通过，见[tag-browser-nix69-install-results.json](tag-browser-nix69-install-results.json)。PC/NUC前端按本轮保存确认完成固定事务激活，后端保持原包；实际入口/认证/备份/数据库inode及实际资源通过，见[前端激活](component-polish-activation-results.json)。只更新浏览器固定输入和本项证据，既有输入法/010改动保持并包含在候选、不纳入提交；Agent未system switch。唯一发行计数归Tag Browser036/CP1–CP4（剩余0），用户安装重开与视觉确认归027/OP4、036/U1。

nix.70顶部/连续背景发行已验证：七组Firefox1872项断言、47份包内资源、私有Release/CI/Cachix精确输出及完整liu-bigpc系统/HM候选通过，见[tag-browser-nix70-install-results.json](tag-browser-nix70-install-results.json)。PC/NUC仅前端经本轮保存确认激活，实际资源/进程、认证、备份与数据库inode核验通过，见[前端激活](chrome-band-activation-results.json)。既有输入法/010修改保持并包含在候选，不纳入提交；Agent未system switch。跨仓唯一发行计数归Tag Browser036/HR1–HR4（剩余0），用户重开/视觉确认归027/OP4、036/U1。

nix.71细粒度配色已发行：1875项七组Firefox断言、47份包内资源、私有Release/CI/Cachix精确输出、完整liu-bigpc系统/HM候选及五个原生服务注册通过，见[tag-browser-nix71-install-results.json](tag-browser-nix71-install-results.json)。PC/NUC程序和前端经本轮保存确认激活，实际资源/schema/认证/备份/DB inode核验通过，见[配套激活](granular-appearance-activation-results.json)。旧版回退限制经用户明确接受，不将旧配色兼容性标为通过。保留原有输入法/010修改并包含在候选，不纳入提交；Agent未system switch。唯一发行计数归Tag Browser036/ER1–ER5（剩余0），用户重开/视觉仍归027/OP4、036/U1。

nix.72统一顶部按钮及侧栏布局已发行，1903项七组Firefox断言/47份正式资产/CI/Cachix精确输出、完整PC系统/HM及五个原生模板通过，见[安装候选](tag-browser-nix72-install-results.json)。PC/NUC仅替换固定前端，经当轮保存确认与真实资源/认证/离线备份/DB inode核验，见[前端激活](unified-appearance-activation-results.json)。既有输入法/010改动保持且包含在候选，不纳入本次提交；Agent未system switch。唯一发行计数Tag Browser036/UR1–UR5剩余0，原有安装/视觉/真实验收观察项保持。

nix.73取色器与自适应顶栏已发行：正式包非无头Firefox原生取色器、1906项七组Firefox断言/47份正式资产、CI/Cachix精确输出及完整PC系统/HM和五个原生模板通过，见[安装候选](tag-browser-nix73-install-results.json)。PC/NUC仅替换固定前端，经当轮保存确认及实际资源/认证/备份/DB inode核验，见[前端激活](gtk-adaptive-activation-results.json)。既有输入法/010改动保持且包含在候选，不纳入本次提交；Agent未system switch。唯一发行计数Tag Browser036/KR1–KR5剩余0，原有用户安装/视觉/真实业务验收项保持。

nix.74预览/实际状态同源浏览器已发行：1946项七组Firefox、297项Node、47份包内资源、CI/Cachix精确输出与完整PC/HM候选、五个原生模板/恢复顺序和四类MIME关联通过，见[tag-browser-nix74-install-results.json](tag-browser-nix74-install-results.json)。仅更新tag-browser-src锁节点及本项证据；既有输入法与010任务修改保持且包含在候选，不纳入提交。未system switch；配套PC/NUC前端的保存确认/激活独立执行，唯一发行计数Tag Browser036/SSR1–SSR5。

预览/实际状态同源配套固定前端已获本轮保存关闭确认并在PC/NUC完成原生事务激活，实际入口/摘要、9份HTTP资源、配色只读接口、离线备份/DB inode和原认证/公网边界通过，见[前端激活](shared-state-frontend-activation-results.json)。后端、生产主题及独立应用保持，无DB恢复或系统switch；nix.74浏览器用户安装仍独立。唯一发行计数Tag Browser036/SSR1–SSR5剩余0。

nix.75原生配色读取修正已发行：298项Node、1957项七组Firefox、47份包内资源、私有Release/CI/Cachix精确输出及完整PC/HM候选、五个原生模板/恢复顺序和四类浏览器MIME通过。见[tag-browser-nix75-install-results.json](tag-browser-nix75-install-results.json)。仅更新tag-browser-src及本项证据，原有输入法/010修改保持且包含于候选、不纳入提交；未system switch，本轮不停止或切换PC/NUC服务、不改网页或生产主题。唯一发行计数Tag Browser036/XRR1–XRR4剩余0；用户正常安装重开和视觉观察保持。

nix.76 测试 profile 隔离补丁已发行：复用已核验 nix.75 原归档，47份运行资源不变；8项启动参数/隔离、4项缓存流程回归、真实中文/GTK/默认浏览器、CI/签名缓存/latest Pin和完整PC/HM候选通过，见[tag-browser-nix76-install-results.json](tag-browser-nix76-install-results.json)。仅更新 tag-browser-src 锁输入及本项证据；保留既有输入法/010修改，不执行系统switch或PC/NUC服务切换。唯一发行计数Tag Browser007/IR1–IR4剩余0。

nix.77及PC/NUC配套前端交付完成。47份资源、298项Node、七组Firefox1971项断言零失败/TODO；CI/签名Cachix/latest Pin保留1版、完整PC/HM候选和原生服务注册/菜单/MIME核验通过。本轮保存确认后仅前端激活，程序/资源/认证/备份/DB inode通过。未改后端/账号主题或用户profile，Agent未system switch；用户安装与视觉观察保持。唯一阶段FSR1–FSR5剩余0。 见[tag-browser-nix77-install-results.json](tag-browser-nix77-install-results.json)。仅更新tag-browser-src锁输入及本项证据；既有fcitx5/010修改保留。

nix.78及PC/NUC柔和悬停前端交付完成。47份资源、298项Node、七组Firefox1992项断言零失败/TODO；CI/签名Cachix/latest Pin保留1版、完整PC/HM候选与服务注册/菜单/MIME通过。本轮保存确认后仅前端激活，程序/资源/认证/备份/inode通过。账号主题未写入，一键配色由用户显式使用；后端/profile保持，Agent未system switch。唯一阶段HVR1–HVR5剩余0，用户安装/视觉确认保留。 见[tag-browser-nix78-install-results.json](tag-browser-nix78-install-results.json)。仅更新tag-browser-src及本项证据；既有fcitx5/010修改保留。

nix.79及PC／NUC侧栏配色前端交付完成。47份资源、298项Node、七组Firefox2028项断言零失败/TODO；CI/签名Cachix/latest Pin保留1版、完整PC/HM候选和服务注册/菜单/MIME通过。本轮保存确认后仅前端激活，实际程序/资源/认证/备份/DB inode通过。未写账号主题或用户profile，无后端替换/DB恢复/system switch。APR1–APR5剩余0，用户安装重开与视觉确认保留。 见[tag-browser-nix79-install-results.json](tag-browser-nix79-install-results.json)。仅更新tag-browser-src锁输入及本项证据，原有fcitx5/010修改保留且不纳入提交。

nix.80视频定位浏览器发行候选已通过：298项Node、2043项七组Firefox、47份包内资源、私有Release/CI/Cachix签名/latest Pin及完整PC/HM候选、五个原生模板/恢复顺序/四类浏览器MIME。见[tag-browser-nix80-install-results.json](tag-browser-nix80-install-results.json)。仅tag-browser-src锁输入与本项证据变动，既有fcitx5/010修改保留；Agent未system switch。PC/NUC前端仍待本轮保存关闭确认，唯一发行计数归Tag Browser027/VLR1–VLR3。

nix.81浏览器发行完成：298项Node、七组Firefox2051项断言零失败/TODO、47份正式资源、私有Release/CI/Cachix签名/latest Pin保留1版及完整PC/HM候选通过。PC／NUC新版固定前端已按本轮保存确认激活，实际程序/资源/认证/备份/DB inode核验通过；LSR1–LSR3发行剩余0。后端/账号主题/用户profile保持，无系统switch；用户安装重开与原视频试用待确认。 见[tag-browser-nix81-install-results.json](tag-browser-nix81-install-results.json)。消费者仅更新tag-browser-src锁输入及本项证据，既有fcitx5/010修改保留且不纳入本次提交。五个原生模板、default target链接、恢复钩子顺序及四类浏览器MIME核验通过。

nix.82侧栏多文件上传：消费者仅更新tag-browser-src锁到正式发行提交024e0d9；CI/Cachix精确输出与可信签名、仅保留最新版Pin、完整PC/HM候选、MIME及五个原生模板/恢复顺序通过。原有fcitx5与010改动保留且不纳入提交；未system switch。本轮保存关闭确认后PC/NUC配套前端已激活，实际进程/资源、离线备份、DB inode与认证核验通过，知识卡保留。用户仍需在普通终端安装并重开浏览器验收。唯一发行计数归Tag Browser012/UPR1–UPR5，5/5完成，剩余0项，见[tag-browser-nix82-install-results.json](tag-browser-nix82-install-results.json)。

nix.83新标签建议与文件工具修复：CI/签名Cachix/latest Pin保留1版、47份正式资源、七组2103断言与完整PC/HM候选核验通过；rerun.nu的五个桌面应用精确缓存均已验证和预取。消费者只更新tag-browser-src到d88d331，五个原生模板/默认target/恢复钩子/MIME通过；既有六项修改保留且不纳入提交，没有系统switch或服务重启。配套前端已在此前025/G2上线，本次不重复切换；用户安装重开待自行执行。见[tag-browser-nix83-install-results.json](tag-browser-nix83-install-results.json)，唯一发行计数Tag Browser037/P1–P4。

nix.84已发行并完成完整PC/HM候选检查：滚动桥跨导航重接/旧Document清理与原生上传焦点修复；47份资源、308项Node、七组2105项Firefox断言零失败/TODO、CI/签名缓存/latest Pin及五应用升级缓存通过。见[tag-browser-nix84-install-results.json](tag-browser-nix84-install-results.json)。仅更新tag-browser-src及本项证据；现有六项输入法/010/资料修改保留，Agent未system switch或服务切换。唯一发行计数Tag Browser037/Q1–Q4，用户安装/真实GTK弹窗试用独立。

2026-10-27用户修订常规发布授权：已确定范围的“上线”指令即包含当轮PC／NUC短暂停服切换，不再追加保存关闭问答；候选/预演/回退与实际验收门槛保留，CLI兼容参数由该轮指令授权。权威操作契约见[原生版本更新](contracts/native-version-update.md)，不改写历史确认事实，不扩大到系统switch或数据操作。本轮前端交付唯一计数仍归dufs-plus029/ITR1–ITR3。


nix.85配套音频入口发行已完成：47份正式资源、七组2110项Firefox断言、私有Release/CI精确输出、可信签名Cachix/latest Pin保留1版及五应用缓存预取通过。仅tag-browser-src锁更新到2f04cf3，完整PC/HM候选、菜单/版本、四类MIME、五个原生模板和恢复顺序通过；原有七项修改逐项保留且不纳入提交。见[tag-browser-nix85-install-results.json](tag-browser-nix85-install-results.json)。统一配套交付按一次“上线/发行”口令执行；网页已先行上线，本次不重复停服、不读取用户profile、不system switch。唯一发行计数Tag Browser004/AP1–AP4，4/4完成，剩0步；用户仍需手动安装重开和试用。

nix.86当前歌曲身份与标签切换配套交付完成：PC／NUC前端已按一次“上线”激活验收，后端和数据库保持；47份正式资源、七组2131项Firefox断言零TODO/失败、私有Release/CI精确输出、可信签名Cachix/latest Pin保留1版及五应用升级缓存通过。仅更新tag-browser-src到正式发行提交93e55ab，完整PC/HM候选、五个原生模板/默认target/恢复钩子、菜单版本及四类MIME通过，原有七项修改保持且不纳入提交。见[tag-browser-nix86-install-results.json](tag-browser-nix86-install-results.json)。唯一交付计数Tag Browser004/TP1–TP4为4/4完成、剩0；用户仍需手动系统更新、正常退出旧窗口重开与真实曲目试用，Agent未system switch或访问日常profile。

nix.87非模态打标配套交付完成：PC／NUC前端已按一次“上线”激活并验收，保留各端后端、知识卡资源和数据库；47份资源、七组2140项Firefox断言、私有Release/CI精确输出、签名Cachix/latest Pin保留1版、完整PC/HM候选及五应用缓存预取通过。仅更新tag-browser-src到dbcb065，五个原生模板/default target/恢复钩子、菜单版本及四类MIME核验通过，原有七项用户修改保持且不纳入提交。见[tag-browser-nix87-install-results.json](tag-browser-nix87-install-results.json)。唯一交付计数Tag Browser004/LR1–LR4为4/4完成、剩0；用户安装重开与实际体验确认独立，Agent未system switch或访问日常profile。

nix.88状态流配套交付已核验：PC／NUC仅替换前端且保留各端后端/数据库/知识卡资源，双端六项回退和真实资源/认证/备份通过；私有Release/CI精确输出、可信签名Cachix/latest Pin保留1版、完整PC/HM及五应用缓存通过。仅更新tag-browser-src到7b54fd8，五个原生模板/default target/恢复钩子、菜单版本及四类MIME核验通过；既有七项用户修改逐项保持。见[tag-browser-nix88-install-results.json](tag-browser-nix88-install-results.json)。唯一交付计数Tag Browser004/SR为4/4，用户系统安装和重开/实际体验另行确认；Agent未system switch或操作日常profile。

2026-10-28：nix.89标签徽章配套发行完成，唯一消费锁tag-browser-src更新到24a4148；完整PC/HM、五个原生模板/default target/恢复钩子、菜单版本/四类MIME及五应用精确缓存均核验。PC／NUC前端已切换；NUC音乐后端另通过完整tester、原生包装、双栈及六项回退上线，内网4首/2歌单/文件一致性通过。见[tag-browser-nix89-install-results.json](tag-browser-nix89-install-results.json)。既有八项用户修改保持，Agent未system switch；用户普通终端安装和重开/实际体验独立。

本轮配套发行nix.91：仅更新tag-browser-src锁节点，完整PC/HM候选及五应用缓存通过，PC／NUC固定前端已激活，各端现用后端及独立知识卡资源保持。见[安装和双端核验](sidebar-query-install-results.json)。八项既有修改原样保留；不system switch。

本轮条目状态浏览器发行nix.92已完成：完整PC/HM候选和五应用缓存通过，仅tag-browser-src锁节点更新；见[精确安装证据](row-state-install-results.json)。本轮无网页服务切换；Agent未system switch，既有及并发修改未被本轮覆盖。跨仓唯一发行计数为产品027/RSD1–RSD3。

2026-10-30：nix.93合并页面与标签栏配套发行完成，唯一锁节点tag-browser-src更新至6c8f903。完整PC/HM、五应用精确缓存、原生模板/恢复钩子、菜单版本与四类MIME通过；PC/NUC固定前端已激活，逐端后端/数据库/独立应用保持。见[安装证据](merged-pages-install-results.json)。本轮开始工作树干净；现有dsh等已提交配置原样保留并包含于系统候选，未代为system switch或读取日常profile。唯一跨仓发行计数Tag Browser027/PCR，用户普通终端安装重开与真实体验待确认。

2026-10-30：nix.94父标签/原生下载配套发行完成，仅tag-browser-src锁节点更新至670dfc7；完整PC/HM、五应用精确缓存、原生模板/恢复钩子、菜单版本与四类MIME通过。PC/NUC固定前端已激活，保留逐端后端/数据库/独立应用，034紧凑Markdown工具栏排除。见[安装证据](tag-browser-nix94-install-results.json)。本轮开始工作树干净，无用户修改被覆盖；Agent未system switch或读取日常profile。唯一跨仓交付计数Tag Browser010/UXR，用户手动安装与实际体验待确认。

2026-10-30：nix.95共用资源行/收藏标题浏览器发行完成，仅tag-browser-src输入锁更新；完整PC/HM、五应用精确缓存、原生模板/default target/恢复钩子、菜单版本与四类MIME核验通过，见[安装证据](tag-browser-nix95-install-results.json)。本轮开始工作树干净，无用户修改被覆盖；无网页/后端服务切换、数据写入、system switch或日常profile访问。唯一跨仓发行计数Tag Browser027/URR，实际安装重开仍待用户确认。

2026-10-30：nix.96统一多选浏览器发行完成，仅tag-browser-src输入锁更新；完整PC/HM、五应用精确缓存、原生模板/default target/恢复钩子、菜单版本与四类MIME通过，见[安装证据](tag-browser-nix96-install-results.json)。本轮开始工作树干净；构建时并发改动按证据记录且不覆盖。无网页/后端服务切换、生产数据写入、system switch或日常profile访问。唯一跨仓发行计数Tag Browser027/MSR，实际安装重开仍待用户确认。

2026-10-30：nix.97标签整理与URL排序浏览器发行完成，仅tag-browser-src输入锁更新；完整PC/HM、五应用精确缓存、原生模板/default target/恢复钩子、菜单版本与四类MIME通过，见[安装证据](tag-browser-nix97-install-results.json)。本轮开始工作树干净；并发外部改动按证据记录且不覆盖。无网页/后端服务切换、生产数据写入、system switch或日常profile访问。唯一跨仓发行计数Tag Browser001/TOR，实际安装重开仍待用户确认。

2026-10-30：nix.98收藏目录与层级主题配套发行完成；浏览器输入锁仅tag-browser-src更新，完整PC/HM与五应用缓存、注册模板/恢复钩子/MIME核验通过，见[安装证据](tag-browser-nix98-install-results.json)。原完整tester实际CLI、原生包装/双栈及两套六项回退通过后，按用户本轮“发行”直接串行NUC/PC切换程序与各自保留知识卡的前端；实际程序/HTTP/认证、离线备份/SQLite及inode和Upholds恢复通过，见[实际激活](tree-depth-native-activation-results.json)。无系统switch、日常profile访问、账号主题改写或数据库恢复。唯一跨仓DTR1–DTR3剩余0，用户浏览器安装重开另列。

2026-10-30：nix.99配套发行完成。仅tag-browser-src锁更新，CI/签名缓存/latest Pin保留1版、五应用缓存、完整PC/HM及原生注册/钩子/MIME通过，见[安装证据](tag-browser-nix99-install-results.json)。两端当前8h3y包及新前端各六项隔离回退通过后，按用户本轮“上线”授权只替换PC／NUC前端；workcdn对应只读core同时更新，实际程序/13项HTTP资源/鉴权/离线备份/inode/Upholds恢复通过，见[实际激活](readonly-depth-native-activation-results.json)。后端、账号主题和独立应用保持，无DB恢复、日常profile访问或system switch。唯一跨仓RAR1–RAR3剩余0；用户系统安装重开另列。

2026-10-31：首次批量网页打标nix.100发行消费核对完成。唯一跨仓发行计数在Tag Browser027/BTR；本仓仅更新tag-browser-src输入锁并记录完整PC/HM、五应用精确缓存、原生模板/恢复钩子/菜单及MIME核验。其他输入、应用、生产数据、网页/后端服务和系统当前代保持；实际安装/重开由用户执行。

nix.100：完整PC/HM、五应用精确缓存、可信签名与latest Pin保留1版、五模板/default target/恢复钩子/菜单版本及四类MIME均核验。仅tag-browser-src锁至a75246d，初始消费工作树干净，无其他输入或应用Pin变化；未激活网页/后端、system switch、迁移收藏或访问日常profile。见[安装证据](tag-browser-nix100-install-results.json)。唯一发行计数Tag Browser027/BTR全部完成，实际手动安装/重开与用户体验另列。

2026-10-31：统一顶部标签操作nix.101发行消费核对完成。唯一跨仓发行计数Tag Browser001/UAR；仅更新tag-browser-src锁，核对完整PC/HM、五应用精确缓存、原生模板/default target/恢复钩子/菜单/MIME。不激活服务、不访问日常profile、不执行system switch，实际安装和重开由用户完成。

nix.101：完整PC/HM、五应用精确缓存、CI可信签名/latest Pin保留1版、五模板/default target/恢复钩子/菜单版本及四类MIME均核验，仅tag-browser-src锁至8fc8ce3。初始消费工作树干净，其余输入和应用Pin未改；无网页/后端激活、生产数据写入、system switch或日常profile访问。见[安装证据](tag-browser-nix101-install-results.json)。唯一发行计数Tag Browser001/UAR全部完成，用户手动安装和实际重开体验独立。

nix.102：折叠收藏的当前/后台运行/休眠三态提示已发行。仅tag-browser-src至98c1fc2，CI可信签名/latest Pin保留1版、五应用精确缓存及完整PC/HM候选通过；五模板/default target/恢复顺序、菜单版本与四类MIME保持。见[安装证据](tag-browser-nix102-install-results.json)。唯一发行计数Tag Browser027/OHR已完成，用户手动系统安装与实际重开体验独立；未激活服务、修改生产数据或访问日常profile。

nix.103：休眠收藏提示恢复修复已发行，实际多页卸载/点击及完整七组2593项产品回归通过。仅tag-browser-src至6c556bf，CI可信签名/latest Pin保留1版、五应用缓存及完整PC/HM候选通过；五模板/default target/恢复顺序、菜单版本和四类MIME保持。见[安装证据](tag-browser-nix103-install-results.json)。唯一发行计数Tag Browser027/SHR已完成，用户手动安装与实际重开体验独立；未激活服务、修改生产数据或访问日常profile。

nix.104：工作区/收藏统一打开状态及异步滚动归属已发行。仅tag-browser-src至0cd7538，CI可信签名/latest Pin保留1版、五应用缓存及完整PC/HM候选通过；五模板/default target/恢复顺序、菜单版本和四类MIME保持。见[安装证据](tag-browser-nix104-install-results.json)。唯一发行计数Tag Browser027/OSUR已完成，用户手动安装与实际重开体验独立；未激活服务、修改生产数据或访问日常profile。

nix.105核验过程（最终已补正，见下）：制品、CI及完整PC/HM候选通过，PC/NUC配套已运行最终39步验证的程序，NUC私有17根已激活。PC Home在最终HEAD发现隐藏链接可读后停用（未读配置内容），当时共享路径解析和索引修复正在原完整门槛中，唯一发行计数Tag Browser038/P尚未收尾；下述最终验证与发行现已完成。

nix.105：正式浏览器及PC/NUC配套服务/网页、PC Home与NUC私有17根目录已验证；完整PC/HM候选、CI可信签名/五应用缓存通过。只变tag-browser-src输入，独立应用和只读目录映射保持；失败目录尝试已恢复配置。唯一发行计数Tag Browser038/P，见[安装/上线证据](tag-browser-nix105-install-results.json)。仍由用户手动switch及正常重开确认；无日常profile访问、DB恢复或NUC编译。

规范虚拟根开发：已有16项合成事务/程序版本守卫测试与原发行器3项回归通过，Nix候选模板解析通过；冻结产品driver与本机命令已接入，实际安装/双端迁移尚未执行。旧nix.105是当前现网；唯一新阶段为Tag Browser038/V，不新增平行发行计数。

PC会话记录发布时序：新增提交前不可见、提交前失败保持旧记录、提交后中断保持旧记录并按同计划向前补齐的合成验证；新写入不恢复为旧快照。通用配置事务默认行为保持，namespace只用显式延后文件端口；16项事务与原发行器3项通过；准备前要求已安装支持规范根的新核心程序，旧DB缺少namespace表也不放宽此检查。

nix.107最终候选：修正规范新根父节点展开恢复，七组2653项检查与隔离实际重启通过；仅浏览器锁至1b39d8e，缓存可信签名/latest Pin及完整PC/HM、五应用精确缓存通过，知识卡使用同物理库的dufs/cards候选。见[安装证据](tag-browser-nix107-install-results.json)。实际服务/命名空间切换仍待Tag Browser038/V6完整后端门槛；未执行系统switch或访问日常profile。

规范根实际交付完成：用户明确确认开启PC/NUC严格签名，地址/配对不变，后台签名同步校正旧副本。两端原14文件事务与新路径DB已激活，实际三根/跨节点Range、关系和inode/伴生字节核验通过。NUC提交后发现外层启动器漏字段，按原收据以同一CLI字节前向恢复，随后正常更新正式包装并移除临时只读绑定；后续能力守卫要求后端及启动器双标记，16项基础设施与原6项真实版本门槛通过。无密钥HAProxy配置按既有容器策略恢复0644，已安装开机守卫通过；不改凭据权限。浏览器107签名缓存/完整系统候选保持同一派生，用户自己switch和正常重开。见canonical-namespace-publication-results.json；唯一跨产品计数Tag Browser038/V5–V6完成。


037增量交付实际上线：原ff1h版本管理器以当前9maz候选完成独立6项更新/回退门槛，再预演/准备/切换PC与NUC私有、只读核心，保留xar前端与最新数据。三项服务真实Rust子进程及SHA、持久版本指针、两端strict=true核验通过；PC清单200/未签名同步401、三根与跨节点Range通过，NUC匿名401保持。原80-tag-version持久选择由管理器维护，普通HM注册保留该drop-in，无需改模板或执行系统switch。用户已登录NUC网页刷新待确认，不读日常profile或密码。完整证据见incremental-auth-publication-results.json。实际准备/切换累计34.329秒，原更新回退门槛57.116秒，从证明复核到两端激活100.321秒；包含补充读回核验232.067秒。复用已验候选而未重编译，不能当冷编译时间。


DUFS前端别名冲突修复：前次401只更新后端，用户现报错来自仍旧前端。复核DUFS035已验制品后由固定ff1h原管理器激活PC/NUC h1zy前端，保持9maz后端、strict=true及原知识卡112/学习规划10文件；6项实际更新/回退验收通过，PC实际HTML/WASM摘要与新制品一致，NUC服务参数及持久指针一致，匿名401保持。没有站点数据清空、DB恢复或系统switch，真实用户Storage不读取，刷新PDF结果待确认。证据namespace-alias-frontend-publication-results.json；单纯后台401成功不再作为前端迁移成功证明。


用户禁用缓存刷新后仍失败，随后仅提供键名并确认两份进度值相同：根因是前一前端只协调tree/scroll，漏了PATH_KEYS中的同目录偏好/进度尾斜杠别名。产品补齐按类型协调与不含值的定位诊断，283项应用/27项共享测试、private构建及11项实际WASM通过；原6项更新/回退门槛通过后，同一ff1h管理器将PC/NUC切到xv4p前端，9maz后端、strict=true和独立应用保持。PC实际HTTP制品摘要、双端实际参数/持久选择核验通过。未清缓存、读日常profile、存完整用户键名清单、恢复DB或系统switch。原页刷新仍待用户。证据namespace-path-alias-publication-results.json。

## 浏览器nix.108与配套前端交付

唯一发行计数沿用Tag Browser047/R1–R3，3项完成、剩余0。本轮只改tag-browser-src锁至d83979e；60份正式资源与七组2653项零失败/TODO、CI同一精确输出/可信签名/latest Pin保留1版及五应用缓存通过。完整liu-bigpc系统/HM、菜单/版本/四类MIME、五模板/default target/restore顺序通过。PC/NUC原固定管理器已激活nfar前端并保留9maz后端，12项实际组合、6项更新回退、PC资源摘要/NUC双区实际参数、严格签名和匿名401通过；知识卡112/学习规划10文件未变，原数据保持、无数据库恢复。见[交付证据](tag-browser-nix108-install-results.json)。Constitution Check：本机构建与固定私有发行，原签名缓存/组合门槛和回退保持，不碰日常profile、不执行system switch，不发布后续metadata writer源码；真实日常大目录性能仍归共享017/A1人工验收。用户普通终端执行nu rerun.nu liou --host liu-bigpc，并正常完整重开确认108。

## 语义配色nix.109配套交付

本轮依用户上线指令准备固定nix.109、严格签名缓存与完整PC/HM候选；唯一跨仓交付计数DUFS029/SCR，不重复计步。仅允许消费锁tag-browser-src更新，原服务模板/默认target/restore顺序及MIME和菜单入口核验保持；不系统switch、不覆盖外部改动。PC/NUC固定前端已切换，9maz后端和strict签名/鉴权、数据库inode及独立应用保留已核验。

SCR交付完成，剩余0步，见[109安装候选与上线证据](tag-browser-nix109-install-results.json)。仅tag-browser-src锁至e84e276，正式资源/2653项Firefox、CI同一精确输出/可信签名/latest Pin及五应用缓存、完整PC/HM/菜单/版本/MIME/原生注册均通过；PC/NUC前端am74保持9maz后端、严格签名/认证及原数据。未执行系统switch；用户普通终端执行nu rerun.nu liou --host liu-bigpc，完整重开确认109并显式应用新Helix映射。

## 自动入口及统一底栏nix.110配套交付

用户2026-11-03“上线”授权：仅tag-browser-src消费锁至4b849a8；实际Firefox七组2664项、私有Release、CI同一精确输出/可信签名/latest Pin保留1版及五应用缓存、完整PC/HM/菜单/版本/MIME/五原生模板/默认target/restore顺序通过。PC/NUC配套前端gz3已激活，9maz后端、严格签名/认证、数据库inode及独立应用保持。见[110安装候选与上线证据](tag-browser-nix110-install-results.json)。跨仓唯一计数Tag Browser027/NER；未执行系统switch，用户普通终端运行nu rerun.nu liou --host liu-bigpc并完整退出重开确认110。独立Android首版归产品048，不改本消费锁或声称包含在Linux包内。


## 标签页切换与PDF筛选nix.111配套交付

用户2026-11-03“上线”授权Tag Browser027/ATR与dufs-plus002/FR配套发布；跨仓唯一四步计数在产品027/ATR。本仓只在精确CI/签名缓存通过后更新`flake.lock:tag-browser-src`，保留其余运行配置，并验证五应用缓存、完整PC/HM候选、菜单/MIME及五模板/默认target/恢复顺序。服务前端通过已授权原生事务变更，现用后端、严格签名、数据及独立应用保持；不执行系统switch，不读取日常profile或改账号主题。符合本仓宪法、本机单向构建、组合门槛及工作区Spec/来源分层，无新依赖或参考资料。


该配套候选与服务交付已验证，见[tag-browser-nix111-install-results.json](tag-browser-nix111-install-results.json)：私有CI41667490580的实际输出skx3、Cachix可信签名/latest Pin保留1版、其他应用Pin不变、五应用缓存及完整PC/HM候选通过。仅tag-browser-src锁节点更新至3d15ae4；菜单/四类MIME、五模板/default target/恢复顺序不变。PC/NUC固定fwmb前端已上线，保留原9maz后端/严格签名/数据inode与独立应用。唯一跨仓计数Tag Browser027/ATR；未执行系统switch或操作日常profile。用户普通终端在本仓执行`nu rerun.nu liou --host liu-bigpc`，正常退出全部旧窗口并重开确认111，实际使用仍单列。

## 原生主题首屏与Markdown nix.112配套交付

用户本轮“上线”授权。nix.112原生62份资源与七组2686项、私有Release/CI41673716233精确ggpn包、可信签名/latest Pin保留1版、其他应用Pin及五应用精确缓存核验通过。仅更新tag-browser-src锁到e7a6329；完整PC/HM候选、菜单/四类MIME、五模板/default target及restore顺序通过，未system switch。PC/NUC网页cayb上线6.517/11.651秒，现用9maz后端、严格签名、备份完整性/inode/Upholds及独立应用保持。12项实际组合保留全部350份HTTP摘要、13项夹具单测及6项隔离回退通过。组合夹具缺reserved应用根导致404，审批拒绝缩减集合；改夹具按后端固定applications映射补齐，生产路由未改，失败记录保留。唯一交付计数Tag Browser036/NFR，见[完整安装核验](tag-browser-nix112-install-results.json)。用户普通终端应用liu-bigpc并正常完整重开确认112，真实日常体验仍另行验收。

2026-11-09知识卡010/C7配套：独立网页组合发布器仅追加固定共享Helix运行时及许可证的精确路径白名单，任意HTML/JSON/脚本和符号链接仍拒绝；使用已实际发行的ff1hjnr…原生更新器替代旧vb0…固定版本。两个制品边界单测通过，功能/发行唯一计数仍在knowledge-cards010/C1–C7，不增加基础设施切换或系统switch。

010/C7：独立知识卡固定候选xfwz…已通过旧入口prepare；350份非所属资源摘要不变，未apply。现行016组合准入的037后端证据与当前源码不一致，verify_incremental拒绝；该prepare不等同016放行，未启动后端编译/矩阵，未改系统包固定或执行switch。

010/C7追加核对：隔离恢复已验证版本后，037历史后端证据通过，无需重编；016继续在当前浏览器消费者6f46…与线上固定前端960a…不同时拒绝。知识卡84q64…桌面包签名缓存/latest Pin发布通过，其他四应用Pin不变；本仓消费者固定未改，尚未组合放行、apply或system switch。

2026-11-09用户“上线安装”并确认已保存：010/C7固定源码桥真实重建且字节一致，12项实际组合通过，PC/NUC正式更新器已激活xfwz…；136份知识卡资源HTTP/磁盘摘要匹配，旧9maz后端不变，未恢复数据库。Android同包同证书覆盖安装成功。桌面知识卡固定84q64…，隔离基础配置完整system/HM候选通过，ExecStart、可执行文件及组/内核/udev已核对；未执行system switch，未包含其他聊天未提交Helix改动。阶段C1–C7完成，0项自动交付步骤剩余，用户手动系统切换及日常验收分开记录。权威结果在knowledge-cards/specs/010-capture-reliability/install-results.json。

2026-11-09知识卡010/H原生桌面修复：仅将packages/knowledge-cards.nix从84q64…固定至实际Tauri/WebKit拼音/Rime各七组通过的p8zlqa…；可信签名缓存/latest Pin保留1版、其他四应用Pin不变，完整隔离PC/HM候选及内嵌可执行文件/快捷键/菜单、组/内核/udev通过。Android同包同证书更新且摘要一致。未激活服务、重跑Tag All后端或执行system switch；隔离候选排除其他聊天未提交Helix改动，原改动保持。唯一阶段计数knowledge-cards010/H1–H4完成，剩余0步，用户手动切换与日常验收分开。权威结果knowledge-cards/specs/010-capture-reliability/webkit-delivery-results.json。

2026-11-10知识卡011/D上线：只将knowledge-cards消费者固定至真实WebKit拼音/Rime各11组通过的iqc1h1…，可信签名/latest Pin保留1版、其他四应用Pin不变；隔离完整PC/HM候选和内嵌可执行文件/菜单/快捷键及组/内核/udev通过，未包含其他聊天未提交Helix配置、未system switch。PC/NUC正式事务已更新08r22…前端并保留9maz后端；347份原资源/旧哈希资产、全部489份静态摘要及两端136份知识卡HTTP资源通过，未恢复数据库；Android同证书覆盖安装摘要一致。未发布Tag Browser收藏重构或重编其Firefox/后端。唯一跨仓计数knowledge-cards011/D1–D4完成，剩余0步；用户手动系统切换与日常体验另列，权威结果在knowledge-cards/specs/011-card-management/deployment-results.json。

2026-11-10知识卡012/W同步发行：仅知识卡消费者固定改为wflj303…，可信签名缓存/latest Pin及其他Pin保持；排除未提交Helix源码/补丁的隔离完整PC/HM候选zxhg59…通过，菜单/Ctrl+Alt+K、5个原生模板与恢复顺序、内核/组/模块/udev保持，未system switch。网页基于两端各自线上基底，只合并知识卡目录并保留旧哈希资源，NUC学习规划保留；用户新鲜已保存确认后原正式管理器激活两端成功。各12项真实组合及HTTP/只读边界回查通过，原后端未变。唯一计数在knowledge-cards/specs/012-mobile-touch-editor/W1–W5，不另开阶段；用户激活PC系统另列。

2026-11-10知识卡012/F配套：只将知识卡消费者从wflj303…更新到可信签名8kg9n4…；真实WebKit空光标宽高/位置、中文、图片和系统滚轮通过。完整隔离系统0wl0v8…、内嵌HM7rdkpy…和独立HM候选构建通过，预演13个装配派生物不含Firefox/后端重编译；菜单/Ctrl+Alt+K、五模板/恢复顺序、当前内核/组/模块/udev保持，未执行system switch，用户原Helix修改/暂存补丁保持且未纳入。PC/NUC各自12项组合通过，用户对本次准备事务确认已保存后正式更新器激活40f2b6…/b0d5ec…，两端236份知识卡和35份网格资源HTTP匹配，NUC学习规划14份及632份磁盘摘要、5008只读保留，现用9maz后端未变、无数据库恢复。唯一计数沿knowledge-cards012/F1–F5；Android正式包仍在产品侧准备，不把QA通过当正式安装。

知识卡012/F配套收尾：产品正式Android候选e2b477…已在用户追加确认后同包/永久证书覆盖安装，摘要与UID10294、实际启动通过；未清数据或迁移QA。产品F1–F5交付完成，剩0步，PC仍需用户手动激活0wl0v8…候选（GC根/data/project/knowledge-cards/.devenv/F-pc-system），Agent未切换系统。三项目总纲白名单发布与checksum回查通过，原未提交Helix配置/暂存补丁摘要保持。

知识卡013三端收尾（2026-11-13）：消费者仅固定到可信签名2ybz591…/0.1.1；最新提交基底的隔离完整系统7xk4a…及内嵌HM jhnqhy…通过，菜单/Ctrl+Alt+K均指新版，5个原生模板/恢复顺序、当前内核及原Helix修改保持。用户最终选择自己跑rerun，Agent未system switch。两端各12项组合通过后，仅知识卡目录从各自当前前端组合激活；现有2wf6后端/数据库、382/396份非所属资源及NUC14份学习规划/685份磁盘摘要、认证只读保持。实际NUC精简Web零写入/列表DOM检查通过。Android已接私有GitHub主发行+国内镜像并原证书覆盖安装，旧手机包按用户授权独立双备份后清理；唯一计数见[知识卡013](https://github.com/liu0fanyi/knowledge-cards/blob/3146e570742443175561967e3d96ff6d787a4027/specs/013-platform-release/tasks.md)，不另建基础设施阶段。

## 共享PC宿主nix.113消费（2026-11-13）

沿用产品Tag Browser049的三项唯一交付计数，不重复计步。当前已获具体GitHub／Cachix载荷授权；CI43366255343与本机2700dns…相同、可信签名和其他4个应用Pin保持已核验。仅tag-browser-src消费锁更新至21803f2；实际完整系统mpgd7i…与HM0m3kfa…、五应用缓存预取、菜单／可见版本／四类MIME／五原生模板／默认target与恢复顺序通过。CI仅73秒、无Firefox重编。用户既有Helix改动及补丁、知识卡0.1.1消费者与其他输入保持；Agent未system switch、未访问日常profile或操作手机。收尾只读检查已观测系统在外部切换到同一mpgd7i…候选、入口2700dns…，Agent未执行switch。产品049本阶段仍剩1项：正常完整重开确认113；无需重复切换，不另装Nix profile。见[安装证据](tag-browser-nix113-install-results.json)。

## 知识卡014重构0.1.2发布（2026-11-13）

仅知识卡消费者由2ybz591…/0.1.1固定到可信签名599gii…/0.1.2，latest Pin保留1版且其他Pin保持。以67dfe36提交为基底，仅叠加该消费者的隔离完整系统mla8fg…和内嵌/独立HM构建核验；菜单/Ctrl+Alt+K、五原生模板、恢复顺序、MIME、当前内核保持，未提交Helix改动原样保留且未纳入候选，Agent未switch。网页从PC/NUC各自当前frontend只叠加知识卡，旧hash保留，两端12项真实组合和prepare通过，用户本次确认已保存后经正式更新器激活；各139份HTTP摘要、382/396份非所属资源、NUC14份学习规划/736份磁盘摘要和认证只读保持，实际入口刷新零业务写入/列表。Android0.1.2/code1002原证书GitHub/国内镜像发布回下载通过；用户选择仅发布渠道暂不安装，未改手机数据。唯一R001–R005计数均在[知识卡014任务](https://github.com/liu0fanyi/knowledge-cards/blob/a66e91da4638e0fcc800d06828e2ba9578798b81/specs/014-list-editor-boundaries/tasks.md)，发布阶段剩余0，不另起基础设施计步。

### Tag Browser nix.114 下载按钮修复交付

用户授权发行后，仅更新tag-browser-src消费锁至887261c，产品源码14b1305及同版共享UI固定；CI43372683135用74秒装配同一0643fq…精确输出，可信签名与latest保留1版已核对，无Firefox重编。完整PC/HM、菜单、MIME、五原生模板、默认target及恢复顺序通过；既有Helix修改与暂存补丁、未跟踪资料保持，其他锁节点不变。未执行系统switch或关闭用户窗口，普通终端手动切换并完整重开。见[安装证据](tag-browser-nix114-install-results.json)。跨仓执行计数仍归产品049，不另建Android计划。

## 知识卡015卡片样式0.1.3发布（2026-11-13）

仅知识卡消费者由599gii…/0.1.2固定到可信签名rd8qg…/0.1.3，latest保留1版且其他Pin保持。以a7f7be4已提交源为基底，仅叠加该消费者的完整隔离系统krqgdi…及内嵌/独立HM通过；菜单/Ctrl+Alt+K、五原生模板、恢复顺序、MIME和当前内核保持，未提交Helix修改与暂存补丁原样保留且排除，Agent未switch。Android0.1.3/code1003原证书GitHub/国内渠道回下载与实时清单核验通过；按既有用户选择仅发布、不操作手机。正式前端139文件与已验收样式候选完全一致，复用原行为证据。网页版只新建，展示交DUFS网格，本轮不切网页或重建后端/TagBrowser。唯一R001–R004计数归[知识卡015](https://github.com/liu0fanyi/knowledge-cards/blob/02fa9393553f4e82f1c94b1b02ab4f3b437630c0/specs/015-grid-card-presentation/tasks.md)，发布阶段剩余0，不另建基础设施任务计数。

## 知识卡016共享标题/侧栏0.1.4发布安装（2026-11-13）

复用已验收候选，无重复编译；知识卡消费者由rd8qg…/0.1.3固定68blqh…/0.1.4，可信缓存/latest保留1版、其他Pin保持。以8d6e81d提交为隔离基底只叠加该消费者，完整系统7y6z1y…与内嵌/独立HM通过，菜单/Ctrl+Alt+K、五原生模板/恢复顺序、MIME和当前内核保持，未提交Helix改动保留且排除，Agent未switch。Android原证书GitHub/国内镜像与实时清单、回下载和实际安装字节一致；首次GitHub回下载EOF沿原不可覆盖事务恢复。用户本次确认保存暂停后，手机0.1.3→0.1.4/code1004同包覆盖，UID10294、登录和输入法保持；真实新建/列表标题及顶栏侧栏打开关闭核验，无真实卡片写入，手机已交还。网页/后端/TagBrowser未切换。唯一R001–R004计数归[知识卡016](https://github.com/liu0fanyi/knowledge-cards/blob/f5a91a89a75fe550287c060860219197e9903139/specs/016-consistent-app-header/tasks.md)，阶段剩余0。

### Tag Browser051公网移动同步配套
- [ ] 精确传输源码、原生签名负例和Caddy候选验证；浏览器／管理路径仍认证。
- [ ] 按原事务核对并交付源站及EdgeOne版本；真实手机个人域同步验收由Tag Browser051 S3持有，不另计步。

## 2026-11-14 Tag Browser nix.115 发行消费

- [x] 固定 Firefox 内核，仅组装正式共享宿主；CI 43563375741 与本机输出一致且 Cachix 签名存在。
- [x] 仅更新 tag-browser-src 至 d5ae5f7；完整 PC 系统/HM 候选、原生服务模板、菜单/MIME及外部 Helix 修改保留检查通过。详见 tag-browser-nix115-install-results.json。
- [ ] 用户自行运行原 rerun 入口及完全重开验证；本轮未执行系统 switch，不读写日常浏览器 profile。

## 知识卡0.1.5字号渠道发布

用户授权发布。PC原签名可信缓存/latest知识卡pin已更新为8z7mlv…0.1.5；其他pin保持。仅更新packages/knowledge-cards.nix，固定4bd5422已提交配置加该消费者的完整系统5mbw7b…与内嵌HM核验通过，独立HM不安装知识卡。菜单/Ctrl+Alt+K、五原生模板及恢复顺序、MIME/内核保持；用户Helix未提交修改保持且不纳入候选，不代执行switch。Android原证书0.1.5/code1005渠道由产品018发布，手机未安装本轮，网页/后端和真实卡片保持。证据[PC候选](knowledge-cards-015-font-release-results.json)，产品权威任务为knowledge-cards/specs/018-editor-font-size。

## Tag Browser nix.116 配套修复消费

nix.116正式包与可信缓存发布通过，固定Firefox引擎，CI与本地包c8vp8j…一致。仅更新tag-browser-src到93069d2；同一工作树完整liu-bigpc系统及内嵌HM候选构建通过，五个原生模板逐文件与nix.115候选一致，外部Helix两文件摘要保持且不纳入提交。只构建、未switch/激活系统或操作用户profile；PC/NUC Web前端另由原事务激活且现用后端保持，删除后端完整候选与Android目录尚未完成。见[tag-browser-nix116-install-results.json](tag-browser-nix116-install-results.json)。用户仍须自行rerun与完整重开，核对设置实际nix.116。
