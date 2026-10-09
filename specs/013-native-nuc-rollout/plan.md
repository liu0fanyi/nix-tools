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
尚未运行Caddy实际解析、容器socket访问或生产切换；双实例和Whisper仍待N2完成。

## N2 候选装配完成

[candidate-results.json](candidate-results.json) 固定已构建的独立候选八个用户单元
（双区 core/tools/files、Unix bridge及target），不安装或启用系统/HM配置。
主区配置同步、媒体映射、专用Git HOME与只读模型；只读区禁用同步，不挂Git凭证，
workspace采用ReadOnlyPaths/BindReadOnlyPaths，无DUFS写权限。每区DB、journal和tool runtime独立。

固定Whisper1.8.6原CLI及musl动态库字节/链接与023制品一致；--help真实运行成功，
未读用户模型或音频，不代表真实识别通过。用产品锁包装，不重编译Rust或换推理版本。
运行期env转换保留秘密值、转换模型和Git路径，拒绝自定义程序/危险覆盖；4项回归通过。
10项现有拓扑/入口门槛复验通过。实际Caddy解析和临时双Unix HTTP转发通过，无TCP新入口。

构建中的只读复制权限和HM属性路径问题已修正，失败不计通过。当前沙盒systemd-analyze
缺basic.target，未完成管理器验收；实际生成单元运行、容器socket访问、外网/Authelia规则
及真实模型识别归N3。生产迁移、环境文件生成、socket目录准备和旧writer互斥归N4。
N2是候选实现完成，不是cutover_ready；当前未停NUC生产服务。

## N3 当前隔离证据

[runtime-results.json](runtime-results.json)：实际用户管理器运行生成单元，六项通过；
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
无用户录音读取、模型不入store/发行包；当前仅CLI推理，最终设备转写HTTP属于N3-E。

测试脚本二进制误读、Caddy文件能力/临时CA目录/Host重定向及客户端3秒超时均已定位修正，
失败不算通过。超时遗留worker仅在自有VFS、固定image/任务名前缀/本次输入挂载核对后回收。
当前N3尚未完成，下一项为N3-D；后续N3-E转写HTTP和N3-F旧CLI回退分列，不扩大原阶段结束条件。
