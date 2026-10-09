# NUC 实施方案

## Constitution Check

本机唯一构建、产品与基础设施各自规格、三级访问隔离和生产备份边界保持。
用户授权原生服务迁移是既有只允许容器激活规则的明确例外，记录于宪法；
仍禁止 NUC NixOS switch，使用显式持久用户单元，不替换整个 Home Manager generation。
不引入外部参考或浮动依赖；新源仅本仓 Python 与固定产品包装。

## 拓扑

以 deploy/instances/home.toml 和实际 podman inspect 交叉核对，不能凭 PC 拓扑假定 NUC。
两套独立 DB/metadata/worker journal；主区媒体映射、Whisper 模型及专用 Git 凭证按现网保留。
本轮保留入口四容器。Caddy 通过只读挂载私有 Unix bridge 访问 loopback native API，
DUFS 使用各自 Unix socket；变更 Caddy upstream 不复制或裁剪旧完整 app_routes。
bridge 权限和只读挂载必须通过实际容器访问 gate；native API 不暴露额外公网端口。

## 顺序与回退

先隔离验收固定包和生成单元，再传闭包及已验收工具归档；全程不发源码、不远端编译。
准备仅写专属候选目录、不停现网。生产离线迁移前确认编辑安全，停止所有五个旧应用 writer，
保留入口配置和 CA/认证备份，双区 SQLite backup/integrity，旧源不覆盖。
通过互斥守卫才启原生；首次新写入后不能以旧 DB 回退。失败停止并保留快照，
明确允许保留新状态的 rollback，不进行无条件启动旧容器。

## 已核对

NUC x86_64、Nix/Podman 可用、linger=yes，九容器运行。双区 DB/metadata uid1000；
两处 /media/liou/Art、/media/liou/project 挂载可读写，模型和 Git 凭证目录存在。
PC 包缺 Whisper CLI，不能直接宣称完整兼容，补齐属于 N2。

## N1 证据与 N2 已完成部分

[topology-results.json](topology-results.json) 来自实际九容器只读 inspect；预检不输出
环境变量/命令/凭证。scripts/native_nuc_plan.py拒绝缺实例、浮动镜像、只读可写、
缺模型映射和只读区Git私钥。scripts/native_nuc_ingress.py仅替换四个固定上游token；
从home.toml生成的完整Caddy候选逐字保留其余规则。10项单元测试通过。
N2装配与N3隔离验收已完成；生产切换仍未执行，不能把早期拓扑报告当实际部署结果。

## N2 候选装配完成

[candidate-results.json](candidate-results.json) 固定已构建的独立候选八个用户单元
（双区 core/tools/files、Unix bridge及target），不安装或启用系统/HM配置。
主区配置同步、媒体映射、专用Git HOME与只读模型；只读区禁用同步，不挂Git凭证，
workspace采用ReadOnlyPaths/BindReadOnlyPaths，无DUFS写权限。每区DB、journal和tool runtime独立。

固定Whisper1.8.6原CLI及musl动态库字节/链接与023制品一致；--help真实运行成功，
未读用户模型或音频，不代表真实识别通过。用产品锁包装，不重编译Rust或换推理版本。
运行期env转换保留秘密值、转换模型和Git路径，拒绝自定义程序/危险覆盖；4项回归通过。
10项现有拓扑/入口门槛复验通过。实际Caddy解析和临时双Unix HTTP转发通过，无TCP新入口。

构建中的只读复制权限和HM属性路径问题已修正，失败不计通过。静态systemd-analyze
曾因沙盒缺basic.target无法完成，已由N3实际八单元管理器运行及重启验收覆盖；
容器socket访问、完整入口契约及真实模型识别证据见下文。生产迁移、环境文件生成、socket目录准备和旧writer互斥归N4。
N2是候选实现完成，不是cutover_ready；当前未停NUC生产服务。

## N3 当前隔离证据

[runtime-results.json](runtime-results.json)：实际用户管理器运行生成单元，八项通过；
同一固定主程序/工具镜像，双区文件与DB独立，私有写入成功，只读DUFS PUT拒绝，
绕过网关直接调用只读API写文本亦被OS namespace拒绝。PDF/EPUB/解压真实处理和
整套target重启后新标签保持；临时单元、runtime、workspace已核对清理。

[container-ingress-results.json](container-ingress-results.json)：同一现网Caddy完整ID，
自有rootless VFS、无网络、只读根，仅测试CA/config tmpfs可写。容器实际只读挂载Unix
socket可连接；无密码拒绝、只读POST405且未到upstream、完整外网路由经合成授权检查。
终端及EdgeOne规则保留。仅scope测试端口/TLS传输及Authelia upstream，未验证真实公网TLS/登录。
固定镜像内置NET_BIND_SERVICE需显式保留；其余cap删除，不改变生产能力或配置。

[whisper-inference-results.json](whisper-inference-results.json)：从NUC只读复制190085487字节
模型到PC私有夹具，摘要与NUC一致；现用Whisper1.8.6真实识别合成英语，命中预期句子。
无用户录音读取、模型不入store/发行包；该报告只证明CLI推理，设备HTTP另见下文N3-E。

测试脚本二进制误读、Caddy文件能力/临时CA目录/Host重定向及客户端3秒超时均已定位修正，
失败不算通过。超时遗留worker仅在自有VFS、固定image/任务名前缀/本次输入挂载核对后回收。
N3六项现已全部通过；下一项N4，不扩大原阶段结束条件。


## N3-D/E/F 收尾与边界

[peer-results.json](peer-results.json)：固定完整后端和NUC完整入口路由，经临时真实CA/TLS、
私有Unix bridge完成发现夹具/申请同意、双向批准、签名同步与远端文本/stream读取。
不信任CA、错误指纹、单边批准、无签名、重放、坏签名及撤销均拒绝；重启保留身份与信任。
LAN仅限定loopback；原Host规则保持（已包含localhost），不借PC裁剪网关替代NUC入口。
Authelia上游在本测试故意指向不可用本地地址，管理内容仍不能匿名读取；真实登录归N5。

runtime报告第七项验证设备Bearer认证、合成中文音频上传、容器PCM处理和真实Whisper推理；
使用现网模型的只读测试副本，返回非空识别文本，不代表语音准确率测试。
第八项在全部原生单元确认停止后让已验收旧CLI打开新DB，分别读到双区原生新增标签。
主区启动生成的实际身份摘要不变，只读区保持不配对；未恢复旧DB或操作生产数据。
生产回退仍需N4工具与N5实际部署验收，不能把隔离夹具等同生产回退完成。

失败尝试不计通过：临时单元缺OpenSSL、启动等待偏短、测试Host改写误触发origin重定向、
配对夹具缺管理token、sync关闭时identity HTTP按契约403，均修正测试配置/断言。
中途一次合成PDF渲染非200未保留响应，追加有限状态/错误诊断后串行完整八项通过；
尚不能给该单次失败断言后端根因，不把重跑成功写成已定位生产PDF故障。
临时单元/独立runtime/数据均已清理；只读核对NUC九个原生产容器全部仍运行。

## 下一阶段 N4 固定交付

N4仍为一项阶段，结束要求不变：固定闭包/镜像传输与摘要核对、离线双区DB/metadata/CA快照、
原容器与native启动互斥、完整入口socket挂载，以及可dry-run的切换/保留新状态回退入口。
停服必须等待并确认全部应用单元/容器停止，不只检查target命令返回。
N4准备不要求用户停编辑；真实停服仅在N5文件已保存关闭的确认之后。
当前总阶段3/6，剩余N4切换工具、N5实际切换与入口同步验收、N6持久恢复与收尾三项。


## N4-A/B 已实现与接入边界

[preparation-results.json](preparation-results.json) 固定本次已验收候选：199个store路径，
NAR字节合计1138947880（不是本轮实际网络传输量）。本机权威构建，NUC只接收；
传输前复核九个源容器的完整镜像、角色与挂载，核验远端全部NAR hash/size和精确控制文件摘要。
候选以manifest摘要命名，700目录/600文件，GC root只有明确指向该固定候选的受控symlink。
不安装单元、不读取生产DB、不传模型/密钥，不改变原四入口或认证配置。

第一次复制因本机自建制品无受信任签名被NUC拒绝，失败不计通过。
只读核对NUC既有trusted-users包含liou后，使用仅本次nix copy的--no-check-sigs显式导入自建制品；
不改系统require-sigs、trusted-public-keys或trusted-users，不跳过SSH主机密钥/TLS验证。
通过SSH传输后逐项NAR与字节摘要核验；这一做法不意味着已把制品发布到Cachix。

[preparation-tests.json](preparation-tests.json)：31项通过（17项新增、14项已有）。
离线模块在任何源状态遍历之前和原子发布之前调用停止守卫；两区一起用SQLite backup并检查integrity。
保留metadata（含配对/CA）、原Caddy/config备份和环境语义，模型仅路径引用；拒绝命令展开、
未知可执行覆盖、链接、损坏数据库、served mount内状态、writer重启、CA/config变化与已有目的地。
主区将外置发现改为同一native主进程接管广播，保留id/HTTPS地址/IP/接口；只读保留旧默认node id nuc，
不是生成新身份，继续禁用sync/pairing/discovery且不添加私人管理token或Git凭证。

互斥纯模块已覆盖五旧应用writer和八native单元，固定完整九容器库存、源镜像与私有标志权限；
container模式拒绝旧DB挂载或旧数据库命令。当时尚未接入持久启动链路；现接入代码及隔离实际验收见下方N4-C，生产注册仍归N5。
N4-C必须把守卫接到每个官方原生/容器启动入口，N4-D把离线模块接到真正可预演的控制入口；
首次生产离线备份仍归N5，编辑安全确认之前不停止现网。

## N4-C 启动接入验收

[startup-results.json](startup-results.json) 对应冻结脚本，92项启动/快照/发布/管理回归通过，
六组实际临时systemd用户单元验收通过；容器库存使用合成数据，不读取生产DB。
七服务分别追加ExecStartPre并Requires/After保留Compose入口；不覆盖已有环境检查或服务主体隔离。
守卫独立以既有用户在宿主命名空间执行（+前缀不使用户单元变成root），实测uid保持1000、
七个服务主体仍有独立PrivateUsers。宿主库存查询固定HOME/XDG/PATH/bus，避免核心Git HOME或
工具容器socket使查询误入另一存储。共享启动检查可并行，容器动作/迁移采用排他锁；竞争拒绝。

Compose开机、manage up/recreate均经过受控入口；native只允许明确保留的四服务，up带--no-deps，
down只停止保留容器，不删除整套库存。拒绝隐式依赖启动、旧writer、未知参数和restart；
需要重启保留入口时采用明确stop/start。只读查询仍可用。render不能覆盖已由native控制的runtime，
旧infra/tag-server/all发布在构建/传输/激活前拒绝；前端独立发布和Aliyun流程不变。
回退模式拒绝任何native单元仍运行或旧DB挂载，普通管理不重建回退容器，交给N4-D专门入口。

只读核对发现NUC另有Podman开机恢复入口，五个旧应用当前restart policy均unless-stopped。
native守卫必须同时检查它们均停止且策略为no，阻止绕过Compose的自动恢复；
真实策略修改归N4-D控制/N5执行，保留四容器策略不变，不能仅靠停止Compose服务。
实际注册、持久模式/锁文件和新入口安装统一在N5确认编辑安全后执行，当前生产入口未替换。
测试临时单元精确清理，原九容器仍运行；最新候选控制目录见preparation-results.json，
闭包仍为同一N3候选，模块已传输并核验，但不是生产切换。

N4-C完成时为3/4；N4-D现已通过，见下节固定切换与回退证据。
控制需持久transition屏障、单独操作锁和startup读写锁，不能持有startup排他锁等待
会调用precheck的systemd启动（否则死锁）；停止全部八原生单元后才允许回退writer。
并固定完整Caddy仅改四upstream和socket只读挂载、范围内重建Caddy、新DB回退命令。
D通过才结束N4；总阶段仍3/6、剩余N4/N5/N6，不新增结束条件。

## N4-D 完成：固定切换与保留新状态回退

[switch-results.json](switch-results.json) 记录104项回归及NUC默认只读预演通过。
[switch-compose-results.json](switch-compose-results.json) 记录实际Podman Compose 1.6.0和双版本CLI门槛；
[startup-results.json](startup-results.json) 已用最终启动输入复验六组实际临时systemd场景。
控制器默认只读，明确activate/rollback且确认编辑安全才改变生产。操作锁和持久journal防止重复快照；
先安装transition屏障，逐个停止五应用，等待全部停止，再关闭它们的自动恢复。
离线双区快照同时保留metadata/CA/配置；注册八单元与逐服务守卫，Caddy只改四upstream，
只在原Caddy上追加只读socket挂载并范围内重建；其余三入口容器不重建。

控制器集成门槛使用合成进程驱动，但真实SQLite/文件/锁/journal；实际Compose门槛使用自有
rootless VFS和随机项目，两个真实旧CLI停止后迁移，两个固定原生CLI写入新标签，
再用真实Compose create-only/no-start构造回退并核对新挂载和core.db命令，旧CLI重开双区读到新标签。
原库摘要、metadata证明、只读workspace挂载和其他入口容器ID保持，临时资源已清理。
实际Compose门槛的Caddy容器只验证挂载/重建范围；认证、转发和TLS沿用N3入口门槛，
不能据此声称真实公网或Authelia生产登录已验收。

回退停止并核对全部八native单元后，固定旧镜像打开两份迁移后的core.db；不恢复旧库。
原Caddy文本逐字恢复，用户新改动则拒绝覆盖。container开机up转为start已有新状态容器，
普通管理不得重建旧挂载；native管理只允许保留入口。备份/preflight选择迁移后数据库和metadata，
Aliyun无只读实例仍兼容，不改变Aliyun部署。生产Compose路径列表原权限664，只读预演允许
当前用户所有的普通列表；正式切换私有备份后将相同内容发布为600，凭证始终要求600。

失败试验发现并修正Compose长格式volume不能按目的地覆盖的兼容问题，采用短格式并实际
检查合并后的Mounts；更新restart策略放在停止之后，避免rootless运行中资源更新错误。
失败不自动恢复旧writer；快照前失败需依据私有journal明确诊断恢复，不宣称自动事务回滚。
服务active只说明进程启动，真实HTTP就绪与数据同步必须立即在N5验证。

最新[preparation-results.json](preparation-results.json)对应12个控制文件、同一199路径候选闭包；
固定私有release摘要6f8295b316ef9f6ad643b5b213cb55ffe8e25c3dd2fc8e70c533a49e80e4f50f。
默认现网预演核对九容器、源命令/挂载、配置摘要、磁盘和单元冲突通过；没有读取生产DB、
安装生产单元或停服。N4四项全部通过，剩余N5/N6两项。

## 下一步及实际切换边界

N5按既有要求依次完成：重新确认NUC编辑已保存关闭；运行固定activate完成离线迁移；
立即核对主区/只读API与文件入口、LAN/公网认证及PC–NUC新写入同步。遇失败保留journal，
先诊断再明确执行新状态回退，不用旧发布或旧DB恢复绕过屏障。
N6核对实际用户服务注册、linger/开机入口与恢复守卫，固定真实结果/限制并提交推送和镜像。
不新增阶段，不执行NUC NixOS switch，不因准备通过跳过编辑安全确认。

## N5 首次切换与守卫修正（尚未完成）

用户已确认编辑安全，首次实际切换完成双区离线快照、单元注册和Caddy入口适配；
主区核心/文件服务在ExecStartPre前后报226/NAMESPACE，未进入正常应用启动。
立即通过固定回退入口停止八原生单元，使原九容器恢复运行，三份/data挂载均改用迁移后状态，
两个core.db quick_check通过，LAN主区/只读API匿名401；没有恢复旧数据库。
不把九容器恢复等同完整业务验收，真实认证访问和PC–NUC同步仍待原生重新切换后验证。

[activation-repair-results.json](activation-repair-results.json)记录真实阶段及只读核对；
[startup-repair-results.json](startup-repair-results.json)记录修正后六组真实systemd场景。
真实NUC对照仅执行true：BindPaths单独通过，BindPaths结合ExecStartPre=+失败。
因此原因是rootless宿主precheck执行方式与读写mount namespace组合，不能归因于媒体目录损坏。
此前隔离启动守卫门槛只有BindReadOnlyPaths，遗漏了这个组合；现追加实际BindPaths回归。
守卫改为每次通过用户管理器启动独立宿主检查，仍逐服务检查、仍保留原服务PrivateUsers/挂载。
64项本机迁移/启动回归及六组实际systemd通过；原静态API/工具制品未变化。

显式resume只接受container-active和完整新状态挂载；停止旧应用后保留当前双区DB，
更新受控启动drop-in与入口再启原生，不调用snapshot，回归已禁止再次快照。
修正控制目录cbf74f6a7faa051f8167d1de57824c26d4ae34b9a4efbb92645aa7f9a4869c25
已私有传输/摘要核验，保留原始release、备份、journal及同一候选GC root。
自动审批拒绝回退后的第二次停服，要求新的编辑安全/切换确认；未绕过或执行二次激活。
当前N5未完成，内部剩余2步：确认后从新状态回退重新切换；真实HTTP认证/双区/公网与同步验收。
整个NUC阶段仍4/6，剩余N5/N6；N6持久恢复与结果收尾不提前勾选。

## N5 已切换原生：自动验收完成，公网二次验证待用户验收

用户在回退后的明确询问后回复继续，再次切换现已成功。恢复预检适配真实systemctl disable
会移除显式链接target的行为：仅补回缺失的固定target，七服务仍校验固定目标和摘要。
此前关于“多层链接”的判断不完整，实际拒绝点是target被disable移除；已在恢复回归模拟。
本轮未再次快照或恢复原库，八个原生单元运行，五个旧应用停止且restart=no，四入口仍运行。
固定运行制品仍为同一N3候选；最新控制目录见[live-results.json](live-results.json)。

真实LAN认证后主区/只读文件和标签200，匿名401，只读POST405；保留CA验证的私人HTTPS身份200。
公网主区匿名302到登录页，登录页200；公网只读匿名401。使用现有运行期凭证在内存完成一次
真实Authelia首因子登录，返回OK且有session Cookie。原策略two_factor保持，首因子后API
仍返回登录页HTML而非JSON，符合尚缺二次验证的保护行为；不能把首因子200冒充完整登录成功。
公网二次验证后的文件/标签访问已请求用户在浏览器验收，不索取密码或验证码。

同步首轮失败暴露两项遗漏：源容器有PC extra_hosts，而NUC原生没有保留；原sync配置没有
广播目标，已批准配对地址未自动进入peer_urls列表。从原私有库存和现有批准配对补齐只读
/etc/hosts私有映射、明确peer_nodes广播目标，保留身份/CA/require_signatures=false原策略。
主机/etc/hosts不变。主区核心重启后，NUC新测试标签到达PC，PC新测试标签到达NUC，
两项删除也传播并确认清理。没有单独隔离验证“仅DNS映射”对失败的影响，不把合并修正
后通过等同已定位静态解析器的全部错误。正常同步以配对HTTPS根地址为目标，不附/tag-api。
该适配已纳入snapshot/注册工具及纯函数回归，拒绝别名/批准路由冲突和未批准目标。
现网修正私有备份原配置，只更新主区运行配置/drop-in，不重新复制DB或修改只读实例。

67项迁移/启动回归通过，六组真实systemd仍通过。N5自动工作完成，剩余1步：用户完成
真实公网二次验证并确认登录后文件/标签正常。N5尚未勾选，不新增功能工作。

## N6 持久配置核对与收尾边界

target和原Compose开机单元均enabled，liou linger=yes；mode=native、每服务守卫有效，
原五应用自动恢复关闭。实际核心重启后状态/同步保持，原身份私钥和CA根证书字节与迁移前一致。
没有重启整台NUC，真实下次开机行为仍应在正常使用中观察；不冒充已做主机重启试验。
运行状态位于服务目录，产品/基础设施规格只镜像至各自todos白名单；未修改前端、PC或Aliyun配置。
当前N6配置核对已完成，剩余1步：公网人工验收通过后固定最终状态并收敛两仓规格。
整个NUC阶段仍4/6，剩余N5人工二次验证、N6最终状态收尾；开发/迁移自动工作无新增待办。
