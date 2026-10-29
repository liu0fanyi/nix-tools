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
