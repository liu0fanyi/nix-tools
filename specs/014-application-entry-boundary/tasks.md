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
