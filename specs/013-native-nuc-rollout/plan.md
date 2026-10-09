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

N4现在完成3/4、剩余1项N4-D：可预演的切换/新状态回退控制及集成验收。
控制需持久transition屏障、单独操作锁和startup读写锁，不能持有startup排他锁等待
会调用precheck的systemd启动（否则死锁）；停止全部八原生单元后才允许回退writer。
并固定完整Caddy仅改四upstream和socket只读挂载、范围内重建Caddy、新DB回退命令。
D通过才结束N4；总阶段仍3/6、剩余N4/N5/N6，不新增结束条件。
