# Nix 与 clipboard-sync 改进计划

更新时间：2026-08-25

## 目标

- 保证 standalone Home Manager 配置不依赖 NixOS 专属能力。
- 简化重复、过时或不必要的 Nix 配置。
- 让 `rerun.nu` 使用 flake 锁定的 Home Manager，并正确处理部署目标。
- 提升 clipboard-sync 的输入边界、文件路径和网络超时安全性。
- 改善 Linux 与 Windows 的安装、升级和自启动方式。

## 实施步骤

- [x] 1. Home Manager 与 Nix 清理
  - 删除由 `programs.*.enable` 已经安装的软件包重复项。
  - 将 `pkgs.system` 改为 `pkgs.stdenv.hostPlatform.system`。
  - 让 nuc 的 autossh 服务声明式启用。
  - 修正 clipboard-sync user service 对固定 `wayland-1` 和 NixOS profile 路径的假设。
- [x] 2. `rerun.nu`
  - 从当前 flake 暴露并运行锁定版本的 Home Manager CLI。
  - standalone 目标可显式选择，默认仍为 `liou-nuc`。
  - 删除普通 switch 中不必要的 `--refresh`。
  - 自检使用实际选择的目标，并改善缺失 profile/unit 时的错误信息。
- [x] 3. clipboard-sync 安全性
  - 增加 TCP 连接、读取和写入超时。
  - 限制内存内容大小、文件数量、单文件及总传输大小。
  - 清理远端文件名，拒绝绝对路径与 `..` 路径逃逸。
  - 为新增边界逻辑补充单元测试。
- [x] 4. 部署方式
  - Linux 服务优先使用稳定安装路径，去掉 debug binary fallback。
  - Windows 将 exe 安装到 `%LOCALAPPDATA%\\Programs\\clipboard-sync`，任务计划只引用稳定路径。
  - 修复 Windows build 模式的变量遮蔽问题，并让更新过程先停止旧任务再替换文件。
  - 将 clipboard-sync 源码作为锁定的私有 Git input，并用 `buildRustPackage`
    可复现构建；Home Manager 服务直接引用 Nix store 包路径。
- [x] 5. 验证
  - `nix flake check --no-build --offline`。
  - 强制求值 `homeConfigurations.liou-nuc.activationPackage`。
  - Nushell 脚本语法检查。
  - Rust format、test 和 clippy（通过项目 devenv；若环境缺依赖则记录原因）。

## 实施结果

- Nix flake、NixOS configurations、`liou-nuc` activation package 和锁定的
  Home Manager CLI 均已求值通过。
- 两个 Nushell 部署脚本均已通过语法加载检查。
- Linux 与 Windows 目标的 Clippy 均以 `-D warnings` 通过；Rust 单元测试 2/2
  通过，Linux/Windows release 二进制已重新构建并更新到 `bin/`。
- clipboard-sync 已迁移为正式 `buildRustPackage`：应用仓库跟踪 `Cargo.lock`，父 flake
  通过 SSH input 锁定源码 revision 和 cargo vendor hash；Linux 部署不再依赖父仓库
  `bin/clipboard-sync` 或 activation 的运行时复制副作用。
- clipboard-sync v0.2.0 已加密 UDP 通告和 TCP 内容，新增 `--doctor`、协议错误分类、
  防篡改/防重放/回环端到端测试、Windows 日志轮转及 `just release` 统一发布流程；
  Rust 测试现为 7/7，Linux/Windows release 由同一源码提交生成并输出 SHA-256。

## 验收标准

- NixOS 和 standalone Home Manager 均可求值。
- standalone 生成的服务不引用必须存在的 NixOS system profile。
- `rerun.nu --home-target <name>` 的部署和自检使用同一 flake attr。
- Windows 编译模式和现成 exe 模式最终都安装到固定目录。
- 恶意或损坏的远端长度、文件数量和文件名不能造成任意路径写入或无界内存分配。

## 后续计划：面向其他用户的密钥与配对

当前实现采用“一组设备共享一把 32 字节密钥”的信任模型：密钥相同的设备可以
互相发现、认证并加密传输，密钥不同的设备相互隔离。该模式适合个人的少量固定
设备，但公开分发时不能复用本仓库的私人密钥。

- [ ] 1. 独立初始化
  - 首次启动时为每位用户生成独立的密码学随机密钥，不依赖 nix-tools、git-crypt
    或仓库内的 secrets。
  - 已存在密钥时绝不覆盖；密钥文件使用平台适当的最小权限。
  - 无交互 daemon 启动与首次初始化分离，避免意外建立不安全的默认信任组。
- [ ] 2. 用户可控的设备配对
  - 提供导出/导入配对文件，后续可增加二维码或短时配对码。
  - 配对材料应有明确版本、过期时间和一次性随机值，并通过已有安全信道传递。
  - 日志和错误信息不得输出共享密钥或完整配对材料。
- [ ] 3. 安装与迁移
  - Windows、Linux 安装器默认走用户自己的初始化/配对流程，不再假设存在
    `secrets/clipboard-sync/shared-key`。
  - 保留显式 `--key`/环境变量导入方式，方便无人值守部署和现有三端平滑迁移。
  - 当前三端共享密钥继续可用，不要求为了发布功能立即轮换。
- [ ] 4. 多设备撤销模型
  - 评估从“整组共用一把密钥”升级到每台设备独立身份和点对点配对。
  - 支持查看已配对设备、撤销单台设备，并避免每次撤销都要求所有剩余设备手工
    更换组密钥。
- [ ] 5. 验收标准
  - 两位用户各自首次安装时生成不同密钥，默认互不可见、不可传输。
  - 同一用户的新设备只有完成显式配对后才能加入信任组。
  - 配对材料重放、过期材料、错误密钥和已撤销设备均被拒绝。
  - 从当前共享密钥部署迁移后，现有文字、图片和大文件加密传输保持兼容或提供
    清晰的一次性迁移步骤。

## 当前阶段：配对系统之前的安全性与可维护性

按以下顺序实施；本阶段继续使用当前三端共享密钥，不改变配对模型。

- [x] 1. UDP 通告加密
  - 使用共享密钥派生独立的 discovery key，以 AEAD 加密设备名、内容摘要、文件名、
    大小、内容 hash 和传输端口。
  - 明文只保留固定 magic、协议版本和随机 nonce；损坏或错误密钥的通告被静默拒绝。
- [x] 2. `--doctor` 自检
  - 检查版本、密钥路径/长度/权限、配置和下载目录、剪贴板访问、局域网地址、
    广播地址以及 UDP/TCP 端口可用性。
  - 自检不得输出密钥、剪贴板正文或其他敏感内容，并以退出码区分成功与失败。
- [x] 3. 协议错误提示
  - 对本机日志明确区分不支持的协议、认证失败、密文损坏、重放请求和内容不存在。
  - 网络响应仍避免向未认证客户端泄露额外内部信息。
- [x] 4. 端到端集成测试
  - 覆盖加密通告、文字/图片/多分块内容、错误密钥、密文篡改、请求重放和中途断线。
  - 测试只使用回环地址和临时目录，不依赖桌面会话或真实剪贴板。
- [x] 5. 统一发布命令
  - 单一命令依次执行格式化、测试、Linux/Windows 编译、产物类型检查和原子更新
    `bin/`，任一步失败均不替换已发布产物。
  - 输出源码提交与二进制校验摘要，降低子模块指针和二进制不同步风险。
- [x] 6. 日志轮转与安全诊断
  - Windows 日志达到上限后轮转并限制保留数量；Linux 继续交由 journald 管理。
  - 日志可记录协议版本、远端地址和错误类别，但不得记录密钥、完整认证 tag、
    剪贴板正文或完整文件内容。

本阶段验收：三端升级后文字、图片和大文件仍可互传；抓包中 UDP 内容摘要和 TCP
内容均不可读；`--doctor` 在三端给出可操作结果；发布命令可从干净源码重复生成
两个平台的已跟踪产物。

## 当前阶段：通知去重与 Linux 二进制缓存

- [x] 1. 修正通知去重语义
  - 每个发送设备只保留最近一次内容作为去重依据；连续相同内容仍抑制。
  - 不同内容会替换旧记录，保证 A → B → A 的第二个 A 能再次提示。
  - 增加多设备隔离及 A → B → A 回归测试。
- [x] 2. 独立 Nix package
  - clipboard-sync 子仓库提供自己的 `flake.nix`、锁文件和默认 Linux package。
  - nix-tools 直接消费子仓库 package，保证 CI 和客户端使用同一 derivation。
- [x] 3. Cachix CI
  - master 推送触发 GitHub Actions 的 Nix build，并使用仓库 Secret
    `CACHIX_AUTH_TOKEN` 上传到 `liu0fanyi-nix`。
  - token 不进入源码；公开 cache key 可安全提交。
- [x] 4. 客户端拉取配置
  - NixOS 和 standalone Home Manager 均加入 Cachix substituter 与公钥。
  - 保留官方 cache 和已有清华镜像；缓存未命中时自动回退到本地编译。
- [x] 5. 发布与端到端验收
  - [x] 推送子仓库并确认 GitHub Actions 成功上传构建产物及签名 narinfo。
  - [x] 更新父仓库锁定 revision，并确认其 derivation 与 CI 完全一致。
  - [x] 部署 homebox，再让 nuc pull + rerun 验证命中缓存。
  - [x] 实机复测 A → B → A 通知，以及 Windows ↔ Linux 双向复制。

## 当前阶段：发布可靠性与可追溯性

按以下顺序实施；已完成的通知覆盖实机验收不再重复。

- [x] 1. 通知覆盖实机验收
  - A 尚未接收时，B 的通告能够替换通知；之后 A → B → A 仍能再次提示。
- [x] 2. 父仓库更新脚本等待 CI
  - `update-clipboard-sync.nu` 默认定位子仓库精确提交对应的 workflow run，等待整个
    workflow 成功后才更新父仓库锁文件和子模块指针。
  - CI 失败时显示失败日志并停止，不发布尚未进入 Cachix 或缺少 Windows 成品的版本。
- [x] 3. Windows 部署后自检
  - 新 exe 与密钥安装完成、旧进程停止后运行 `--doctor`；失败时展示 doctor 报告并
    停止创建/启动计划任务。
- [x] 4. Windows CI 构建缓存
  - 缓存 Cargo registry、git 数据与增量构建目录，锁文件变化时自动隔离缓存。
- [x] 5. 版本可追溯性
  - `--version` 与 doctor 同时显示 crate 版本、protocol 和源码短提交；Nix、Windows
    CI 与本地 Cargo 构建均能注入或推导对应 revision。
- [x] 6. 最终验证
  - 运行 Rust 测试、Clippy、Nix 构建/检查及 Nushell 脚本静态检查；再推送并观察
    GitHub Actions 与 Cachix。

## 后续阶段：精简的桌面配置与 Linux 托盘

保持 daemon 单一职责，不加入账号系统或复杂设置中心。

- [x] 1. 配置格式与安全默认值
  - 增加用户级配置文件，并支持命令行/环境变量覆盖；缺省行为保持当前兼容。
  - 增加 `receive_enabled` 总开关，默认开启；关闭时忽略其他设备广播、不弹接收通知，
    但本机复制仍可向其他设备发送通告。
- [x] 2. 实用配置项
  - [x] 支持接收开关；继续由用户点击通知确认接收，不加入自动写入剪贴板或自动
    保存文件的模式。
  - [x] 经三端使用确认，不加入设备名与下载目录配置；现有默认值满足需求，避免为
    不需要的选项增加配置和 UI 复杂度。
  - 密钥、协议版本、认证参数仍由安全部署路径管理；端口暂不开放配置，避免设备间
    配置漂移和防火墙复杂化。
- [x] 3. Linux 托盘
  - 提供运行状态、版本、打开下载目录、切换“接收已开启/已暂停”和退出操作。
  - 无托盘环境仍可作为纯 daemon 正常运行，不让图形界面成为服务启动的硬依赖。
- [x] 4. Windows 托盘对齐
  - 复用同一配置语义，在现有托盘中显示/切换接收策略，避免两端行为分叉。
- [x] 5. 验收
  - 覆盖配置解析、非法值回退/报错、接收开关和无桌面环境启动；实机验证关闭接收
    后不弹远端通知、发送仍有效，以及 Linux/Windows 托盘和双向传输。

## 后续计划：对外发布准备（暂不实施）

状态：暂停。当前版本继续作为个人三端工具使用；在以下发布门槛完成前，不宣传为
面向普通用户的稳定版本。公开范围原则上只包含独立的 `clipboard-sync` 仓库，不将
带有个人主机配置和加密 secrets 的 `nix-tools` 父仓库作为应用发行物。

- [ ] 1. 明确发布级别与支持范围
  - 区分“源码预览/开发者自助部署”和“普通用户稳定版”；前者可以要求手工导入
    共享密钥，后者必须具备清晰、安全的首次初始化和设备加入流程。
  - 明确首发支持 Windows 版本、Linux 桌面/显示协议和通知/托盘环境；列出无托盘、
    无图形会话及不受支持发行版的降级行为。
  - 写明仅支持可信局域网，不支持公网暴露；说明可见的 IP、端口、流量大小和时序
    等网络元数据，以及剪贴板/文件读取的隐私边界。
- [ ] 2. 完成独立密钥初始化与最低可用配对
  - 复用上文“面向其他用户的密钥与配对”计划：每位用户首次初始化生成独立密钥，
    公开版本不得依赖 nix-tools、git-crypt、KeePassXC 或作者的共享密钥。
  - 最低可发布方案可先提供一次性导出/导入配对文件；二维码、短时配对码、单设备
    撤销可作为后续增强，但错误密钥和未配对设备必须默认隔离。
  - 现有三端共享密钥部署保留显式导入和迁移路径，不自动覆盖或上传任何已有密钥。
- [ ] 3. 清理仓库与法律材料
  - 为 clipboard-sync 增加实际 `LICENSE` 文件（Cargo 元数据目前声明 MIT，但仓库
    尚无许可证正文），并补充第三方依赖许可证清单/NOTICE（如需要）。
  - 对当前文件和完整 Git 历史执行 secret/隐私扫描，检查密钥、token、私人地址、
    用户名、内部路径及构建产物；确认 refs/submodule 不带来不可分发内容。
  - 增加 `SECURITY.md`、漏洞私下报告方式、支持版本策略和合理的安全响应范围。
- [ ] 4. 去除私人基础设施前提
  - Windows 安装器不再硬编码作者仓库、SSH 凭据或私有 `windows-build` 分支；改为从
    公开、带版本的 GitHub Release 下载，并校验与源码 tag 对应的摘要/签名。
  - Linux 用户不依赖作者的 nix-tools 或私人 SSH flake input；独立 flake 可直接使用，
    Cachix 作为可选公开缓存，缓存失效时仍能从源码重复构建。
  - 安装/卸载/升级不得假设存在 git、gh、KeePassXC、Syncthing 或管理员终端，必须
    明确区分普通用户安装与开发者模式。
- [ ] 5. 建立正式版本与制品发布
  - 采用语义化版本、Git tag、CHANGELOG 和发布说明；protocol 变更说明兼容范围、
    升级顺序及回退方法，不再只使用滚动 master 成品。
  - CI 从同一 tag 构建 Windows exe 和 Linux/Nix package，生成 SHA-256、源码 revision、
    SBOM/依赖清单；评估使用 GitHub artifact attestation 或 Sigstore 签名。
  - 收紧 workflow 权限：构建 job 默认只读，只给发布 job 最小的 `contents: write`；
    固定第三方 action 版本或 commit，并保护 release/tag 与主分支。
- [ ] 6. 面向普通用户的安装体验
  - Windows 提供无需源码仓库的安装/升级/卸载入口，处理计划任务、防火墙、运行时
    密钥和旧版本迁移；稳定后再评估 winget，避免过早承担包审核和升级兼容承诺。
  - Linux 提供通用安装说明以及 Nix/Home Manager 示例；说明托盘依赖、桌面 portal、
    zenity/文件管理器行为和 systemd user service 的启停/日志查看方法。
  - 首次启动错误必须可操作：无密钥、端口冲突、无剪贴板、无托盘和防火墙问题均
    可由 `--doctor` 或 GUI 提示定位，不要求用户阅读源码或 journal 才能安装。
- [ ] 7. 发布前安全与可靠性验收
  - 在干净 Windows 用户和至少两个干净 Linux 桌面环境执行从零安装、配对、升级、
    回退和卸载；验证文字、图片、多文件、大文件、暂停接收和托盘操作。
  - 增加协议解析 fuzz/property 测试，复核长度上限、文件名净化、AEAD nonce、防重放、
    错误密钥、恶意广播洪泛和半开 TCP 连接的资源消耗。
  - 验证日志、doctor、崩溃信息、通知和发布产物均不泄漏密钥或剪贴板正文；进行一次
    独立代码审查，并记录剩余风险和已知限制。
- [ ] 8. 发布与后续维护决策
  - 只有上述发布门槛和干净环境验收完成后才创建首个公开稳定 tag；否则明确标记为
    preview，不承诺兼容或普通用户支持。
  - 确定 issue 模板、bug 报告所需诊断信息、版本支持周期、协议弃用窗口和依赖更新
    节奏，避免发布后形成无法持续维护的隐性承诺。
