# AGENTS.md

维护源：`/home/liou/nix-tools/config/agent-rules/project/AGENTS.md`；
`/data/project/AGENTS.md` 由 `just agent-rules --apply` 链接到此文件，修改后在 nix-tools 提交。

## 串口权限统一规则

沙盒内看不到 `/dev/serial/by-id/` 或目标设备时，先通过沙盒外执行权限只读核对
同一稳定路径；本环境存在设备被沙盒隐藏的情况，不能直接断言未连接，也不要先让
用户重新插线或换电脑。确认宿主机同样不可见后再排查连接。此检查不替代下述串口权限规则。

打开串口的探测、烧录、monitor 和 soak 默认通过 `sg dialout -c '...'` 执行。
仅当 `sg` 因沙盒的 `setgroups`/`setgid` 权限限制被拒绝，且已核对目标稳定
`/dev/serial/by-id/` 路径确实可读写时，才允许直接访问该路径；其他失败先诊断，
不得无条件裸跑回退。不得放宽设备权限或改用动态 tty 编号。此规则不授予烧录许可，
也不替代各工程的硬件安全检查和用户确认。

## 计划与资料

`/data/project` 是多仓库工作区，**本身不作为产品仓库、不使用 spec**（它没有 Git
历史）。规格由各产品仓库自行管理，权威源始终在对应仓库内：

- 功能规格放在该仓库的 `specs/NNN-<feature>/`（`spec.md` / `plan.md` / `tasks.md`），
  由 Spec Kit 驱动（`/speckit-specify` → `plan` → `tasks` → `implement` → `converge`）。
- 一般工程状态汇总镜像到 `liou@nuc.local:/home/liou/dufs-lan/todos/<项目>/`。
  **xiaoqiang 全部工程例外：只同步到 `/home/liou/dufs/<工程发布目录>/`，禁止 todos 双镜像**；
  精确路径和白名单遵守 `xiaoqiang/AGENTS.md` 及各仓库规则。
- 跨项目事项查阅根部 `a-next.md`、`a-observe.md`、`a-done.md`；项目内状态以该仓库
  `specs/` 为准，不另建冲突计划。

新增需规格驱动的工程时，在该仓库执行 `specify init --here --force --non-interactive
--integration dsh`（并按需 `specify integration install codex`），不要在此工作区根
或 `nix-tools` 中替代它管理产品规格。

### 执行前与收尾的边界核对

- 接手任务或切换仓库时，主动读取适用的上级/本仓库 AGENTS、constitution 和相关 spec，
  不假定子目录规则已自动加载。简述当前范围、关键禁令与实际写入目标后继续执行；
  已确认的范围不反复询问，用户说“继续”不代表扩大范围。
- 同步、清理或发布前，按仓库实际入口核对源、目标、文件白名单及删除范围；支持
  dry-run 时先预演。通用技能中的示例不得覆盖项目明确规则，规则冲突须先定位并解决。
- 收尾同时验证结果和操作边界：内容/摘要一致之外，还要核对目的地合法、删除项有
  明确去向、无任务范围外写入。无法核验的部分如实列出，不能仅凭命令成功宣称完成。

### 资料整理纲领（每个仓库必过）

历史资料散落在多处以"日期 + 事项"形式堆积，且存在非显然位置。整理时**必须扫描全部**，
不得只查 `docs/`：

```bash
# 1. 所有 Markdown（排除构建产物与上游参考）
find <repo> -name "*.md" -not -path "*/node_modules/*" -not -path "*/target/*" \
  -not -path "*/ref/*" -not -path "*/.devenv/*"

# 2. 任何深度的文档目录（含 doc/ 单数、documentation 等变体）
find <repo> -type d \( -name "doc" -o -name "docs" -o -name "documentation" \)

# 3. 子模块内的文档（父仓库扫描无法覆盖）
git submodule foreach --recursive 'pwd && ls doc* 2>/dev/null'
```

**每份文档按性质归入六类之一**（判据见右列）：

| 类别 | 判据 | 去处 |
| --- | --- | --- |
| 规格 | 描述"要做什么 / 验收标准" | `specs/NNN-*/spec.md` |
| 契约 | 接口路径、状态码、数据结构、协议 | `specs/NNN-*/contracts/` |
| 约束 | 含 MUST / 禁止 / 不得，且可判定 | `.specify/memory/constitution.md` |
| 手册 | 操作步骤（点击/输入/如何运行） | `README.md` 或 `AGENTS.md` |
| 参考 | 上游资料 / 自行整理的转录 | `ref/`（上游）或 `docs/`（自己整理） |
| 历史 | 日期标题 + 镜像哈希 + 测试数字 | 删除（git 历史已有） |

**目录按来源分层，不得混放**：

- `ref/` = 上游/厂商原始资料（vendor 源码、原始压缩包、厂商原理图）
- `docs/` = 本项目产出的说明与索引
- `specs/` = 需求与接口契约
- **禁止同时存在 `doc/` 与 `docs/`**

### 跨项目资料与外部参考约束

本节适用于本工作区所有层级的项目，不限于 ESP32。它是工作区级规则，
不得仅记录在某个 feature spec 后视为其他项目自动继承。

- 外部原始文档、厂商资料及参考源码 MUST 放在所属仓库的 `ref/`；自己编写的
  说明、分析、转录与索引 MUST 放在 `docs/`；需求与契约 MUST 放在 `specs/`。
  `README.md`/`AGENTS.md` 可作入口，不复制整套规格。
- 引入外部 **Git 参考仓库** MUST 使用 `ref/<name>` 下的 Git submodule，
  初次添加使用 `git submodule add --depth 1 <url> ref/<name>`，并在 `.gitmodules`
  设置对应 `shallow = true`；父仓库 gitlink MUST 固定经核对的完整提交 SHA。
  恢复参考使用 `git submodule update --init --depth 1 ref/<name>`；不得以复制目录、
  浮动分支或 `--remote` 隐式更新代替版本固定。
- 外部 PDF、ZIP 等非 Git 原件按原格式保存，记录来源与校验信息；不能为它们
  虚构 submodule。需要完整历史、上游补丁或其他引入方式时，先在对应 spec 的
  plan 中记录具体原因和验证方式；已有用户授权足够时不重复询问。
- 此规则针对外部**参考**，不强制将独立产品仓库或正常包管理依赖改为 submodule。
  共享参考已有权威位置时由使用方引用，不在每个产品重复克隆。
- 各仓库新建或修订 constitution 时 MUST 纳入这些长期约束；每次 Spec Kit plan
  的 Constitution Check MUST 同时核对工作区规则和仓库 constitution，检查目录
  来源分层、gitlink、固定 SHA 与浅克隆设置。feature spec 只补充该功能的具体来源
  与验收，不能替代长期约束。
- 本规则本身不扩大迁移或历史改写授权；既有内容按用户已确认范围逐仓库落实。
  `signature-server` 的功能改造仍暂缓，文档归纳与 dufs 镜像照常进行。

**三类易漏的陷阱**：

1. **编译期嵌入的文件不能移动**：搜 `include_str!` / `include_bytes!` / `embed`
   等引用；被嵌入的文档必须留在原路径。
2. **子模块有独立仓库**：父仓库的 `git rm` 对子模块无效，需在子模块内单独操作与提交。
3. **迁移后必须修引用**：跨文件相对链接、`../` 路径、README 索引、代码内路径常量。

**收尾必做**：死链检查、相对路径检查、权限规范化（目录 755 / 文件 644，防 umask
泄漏到 NUC 镜像）、提交并推送（父仓库若有子模块变更，先推子模块再更新指针）。

### 大文件归档与敏感信息

SDK、image、历史 ZIP 默认按原格式备份并记录来源与 SHA256，不因体积、文件格式
或“私有备份”而整包或分块加密。只有确认含需保护的配置、密钥或记录时才使用
已有 git-crypt 机制，优先分离敏感文件。不得将“敏感信息要加密”扩大为“所有
归档都加密”；spec 和 constitution 必须遵循此边界，既有已完成归档不因此自动重做。

### 工程与 Git 工作目录清单

**每个独立仓库自行管理 Git 历史与 spec**；下表列主要工程入口，不是完整递归
仓库计数或 spec 清单。worktree 不重复计为独立仓库，子模块及更深层仓库需另行核对。

#### 顶层 13 个仓库

| 工程 | 说明 | 远程 |
| --- | --- | --- |
| `dufs-plus` | 文件服务产品 | ✅ github:dufs-plus |
| `tag-all` | tag-server 产品（`tag-server` 为子模块） | ✅ github:tag-all |
| `device-bean-mobile` | Tauri/Android/Kotlin 客户端 | ✅ github:device-bean-mobile |
| `esp32-common` | ESP-IDF/ADF/SR 工具链、下载缓存与厂商资料 | ✅ github:esp32-common |
| `esp32-focus-writer` | 独立固件仓库 | ✅ github:esp32-focus-writer |
| `esp32-p4-dufs-terminal` | 独立固件仓库 | ✅ github:esp32-p4-dufs-terminal |
| `esp32-p4-game` | 独立固件仓库 | ✅ github:esp32-p4-game |
| `esp32-recorder-bean` | 独立固件仓库 | ✅ github:esp32-recorder-bean |
| `esp32-mp3-player` | 独立固件仓库 | ✅ github:esp32-mp3-player |
| `esp32-multi-timer` | 独立固件仓库 | ✅ github:esp32-multi-timer |
| `android-app-kit` | Android 组件库 | ✅ github:android-app-kit |
| `dufs-client-rs` | DUFS 客户端 | ✅ github:dufs-client-rs |
| `bevy-env` | Bevy 工程环境仓（下辖 5 个子仓库） | ✅ github:bevy-env |

#### `bevy-env/` 下 5 个独立子仓库

| 子仓库 | 说明 | 远程 |
| --- | --- | --- |
| `bevy-game` | 游戏主体（提交量最大） | ✅ github:bevy-game |
| `bevy-sketch` | 画布/绘图 | ✅ github:bevy-sketch |
| `bevy-app-foundation` | 共享应用基础层 | ✅ github:bevy-app-foundation |
| `bevy-canvas-kit` | 画布组件库 | ✅ github:bevy-canvas-kit（private） |
| `bevy-project-planner` | 项目进展看板 | ✅ github:bevy-project-planner（private） |

#### `xiaoqiang/` 主要 Git 工作目录

| 子仓库 | 分支 | 远程 |
| --- | --- | --- |
| `esp32-p4-cmt2300a`（400m 的 linked worktree） | feat/cmt2300a | ✅ 共用 github:esp32-p4-400m20s（private） |
| `esp32-p4-400m20s`（主工作树） | main | ✅ github:esp32-p4-400m20s（private） |
| `esp32-p4-sip` | main | ✅ github:xiaoqiang-esp32-p4-sip（private） |
| `sip` | main | ✅ github:xiaoqiang-sip（private；共享应用已推送，SDK 采用加密归档 + Git 补丁，恢复构建已验收） |
| `sip-rk3506` | master | ✅ github:xiaoqiang-sip-rk3506（private；SDK 采用校验归档 + Git 补丁，恢复构建已验收） |
| `tauri_config_page` | main | ✅ github:tauri_config_page |
| `device-common` | main | ✅ gitee:xiaoqiang-sip-device-common |
| `signature-server` | master | ❌ 无远程 |
| `xiaozhi` | main | ✅ github:xiaoqiang-xiaozhi（private；固件另在 xiaoqiang-xiaozhi-firmware） |
| `sip_old` | main | ✅ github:xiaoqiang-sip-old（private；保留原 app 历史，SDK 用自身原格式归档 + 补丁恢复） |

`signature-server` 已归纳本地规格并镜像至 dufs；暂缓的是功能/生产改造，Git 远程推送待历史敏感信息处理；`xiaozhi` 源码与固件已推送私有远程，容器构建复验仍受 UID/GID 映射阻塞。不据此推断未完整核验的
嵌套仓库；有上游远程也不等于本地改动已有远程备份。建远程、归档及推送按用户已确认
策略执行；未确认策略的仓库先核对，不擅自处理。

旧 `xiaoqiang/esp32-p4-common` 已退役，SIP/400m/CMT 统一使用顶层 `esp32-common`；旧 Git 历史已有本机私有 bundle 备份。

### xiaoqiang 目录与整理边界

用户约定：本目录下新建私有远程统一以 `xiaoqiang-` 为仓库名前缀，例如
`xiaoqiang-esp32-p4-sip`。已有远程的实际名称以清单为准，重命名前核对消费者引用。

`xiaoqiang/` 本身不是仓库。本轮已授权的软件工程文档迁移已收尾，
包括 `signature-server`；功能待办不阻止文档归纳。后续按各仓库 specs 维护，不据本清单重新启动批量整理；
新增整理范围先说明内容与方案，保留必要手册和关键参考，核验去向后清理旧流水。

CMT/400m 已按用户选择保留一个私有仓库、两个分支；两者文档已整理、提交推送，
400m 遗留诊断和发布器改动也已纳入。共享 Git 数据位于 `esp32-p4-400m20s/.git`，
不得当作重复目录删除；不能把建立远程误解为还需拆仓或合并分支。

`sip_old` 已统一为独立产品仓库，保留原 app Git 历史并纳入顶层构建与产品配置；
SDK 原历史私有备份，源码适配保存为补丁，原格式归档按 SHA256 恢复。不得与 sip 合并。
文档迁移完成不代表全部构建、恢复或板端验收完成，具体缺口以各仓库 specs 为准。
个人事项、未归属软件工程的硬件探索及运行数据保留；硬件操作、固件发布不包含在资料清理授权内。

资料目录迁移和清理须按用户确认的范围执行。NUC `/home/liou/dufs/` 是 xiaoqiang
专用区；其规则不扩展到其他工程。运行产物 `/home/liou/dufs-lan/dist/` 与资料分开管理。

## 仓库布局

`/data/project` 是多仓库工作区，不作为产品仓库。每个一级工程目录维护自己的
Git 历史：

- `esp32-common`：ESP-IDF/ESP-ADF/ESP-SR、下载缓存、开发环境和硬件参考资料。
- `esp32-p4-dufs-terminal`、`esp32-p4-game`、`esp32-recorder-bean`：独立固件仓库。
- `device-bean-mobile`：独立的 Tauri/Android/Kotlin 客户端仓库。

固件仓库通过 `../esp32-common/devenv.nix` 复用工具链，并按需从
`../esp32-common/ref/` 引用厂商资料。不要把 `esp32-common` 复制进各产品仓库，
也不要为每个产品重复下载 SDK。手机工程使用自己的 Android/Rust 开发环境，
不依赖硬件工具链。

`esp32-common`保持同级独立仓库，不设为产品仓库的submodule。

## Bevy 源码与部署

所有 Bevy 工程都以当前工作站上的下列目录为唯一源码和构建来源：

```text
/data/project/bevy-env/
├── bevy-sketch/
├── bevy-game/
├── bevy-canvas-kit/
└── bevy-project-planner/
```

不要从 NUC 上的历史 `bevy-env` checkout 构建或部署，也不要让 `dufs-plus`
构建、复用或覆盖 Bevy 产物。进入 `/data/project/bevy-env` 的 devenv 环境后使用：

```bash
just deploy-sketch
just deploy-game
just deploy-game-app <app>
just deploy-planner
just deploy
```

这些任务在本机编译，并只把各自拥有的目录同步到
`liou@nuc.local:/home/liou/dufs-lan/dist/`。部署前确认对应子仓库工作树和提交，不能用
另一台机器上碰巧存在的 checkout 替代。

## dufs-plus、tag-all与基础设施

- dufs-plus与tag-all均在本机各自仓库构建，通过`devenv shell -- just deploy`发布NUC；不从NUC历史checkout构建。
- 两者发布入口由本机`/home/liou/nix-tools`统一管理传输、备份、激活和验收；详细参数按各自AGENTS执行。
- NUC `/media/liou/project/me/nix-tools`负责生产备份与容器管理。基础设施与阿里云部署按本机nix-tools的AGENTS执行。
- dufs-plus只同步自己的dist内容，必须排除`bevy-sketch/`、`bevy-game/`和`project-planner/`，不得覆盖Bevy产物。

文件浏览器为`http://nuc.local:5006/#/`；独立应用直接使用`/dist/`路径：
`/dist/project-planner/`、`/dist/bevy-sketch/index.html?...`、`/dist/bevy-game/<app>/`，
不能套用文件浏览器的`#/`路由。只有用户明确要求本地调试时才启动临时预览端口。
