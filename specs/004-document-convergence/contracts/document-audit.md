# 本地与 NUC 文档复核

结论：上一轮 18 工程的规格镜像已建立，但不能据此认定所有工程文档都已迁入 spec、可以整体删除旧资料。本次核验区分文件一致性、内容归属、历史失效和仍待整理项。

## 核验范围与证据

- 本地：18 工程、nix-tools 和 clipboard-sync；Git 清单和文件系统扫描交叉检查，含嵌套文档目录、未跟踪文件及可用子模块。上游 ref/refs/vendor、SDK/构建缓存和工具模板不作为待迁移产品计划。
- NUC：/home/liou/dufs-lan、/home/liou/dufs，以及 /media/liou/project/me/nix-tools、/home/liou/nix-tools 候选 checkout。记录 1,349 份文本类文件路径与摘要；不等于 1,349 份工程规格。运行缓存、个人学习/写作与上游文档占多数。
- 附件 inventory.json 是文件级清单和初步类别，不是逐句需求覆盖证明；原始只读快照保存在 PC 临时审计目录，未作为新计划发布。
- 18 工程已有 157 份 specs Markdown 与 NUC 摘要一致；写作机另有未跟踪的 specs/000-hardware-selection/selection.md 未同步，属于新增工作，未代为提交。后续新增的补迁规格另走各仓库同步核验。
- tag-all/tag-server/docs/device-api-v1.md 被 src/device_api.rs 的 include_str! 编译期引用，必须保留原路径；不是可直接删除的遗留文档。
- 未初始化上游子模块只核对 gitlink，不下载上游；xiaoqiang 不迁移、不改文件。

## 18 工程复核结果

| 仓库 | 已有规格覆盖 | 本次结论/剩余边界 |
| --- | --- | --- |
| dufs-plus | 文件一致性、阅读与媒体 | 发现远端 transcriptions.md 的详细交互/批量删除未在原规格中完整体现，补入 003-transcription-management；原运维布局已在 AGENTS |
| tag-all | 音乐、设备 API、写作、位置、录音联删等 | 原规格镜像一致；子模块编译期 API 文本保留，不能整体清空 docs |
| device-bean-mobile | 后台同步、写作回执 | 四路开关/通知已在规格；远端 ANDROID_RELEASE 混有 Clip、公库与旧发布流水，仍需逐段退出 |
| esp32-common | 公共功耗、模块边界、OTA、平台边界 | BLE 线协议正文原在组件目录，本次补入 OTA contracts/wire-v1.md，组件留链接；渲染参考混有版本试验流水，待进一步分离 |
| esp32-focus-writer | 离线保存、回执、手动取回及协议 | 原镜像一致；新增选型文件未同步/提交；旧混合 mp3/writer 资料包含跨设备事项，不可整份删除 |
| esp32-multi-timer | 倒计时与休眠 | 原镜像一致；CMake/version/SDK资料不进 spec |
| esp32-mp3-player | 音乐镜像与播放 | 原镜像一致；保留的旧 mp3 文件是混合记录，需逐段退出 |
| esp32-recorder-bean | 录音与安全传输 | 原镜像一致；recording/相机交叉资料不能按文件名直接删除 |
| esp32-p4-game | 游戏、OTA、PPA、UI | 原镜像一致；DISPLAY_BRINGUP 仍混合参数、操作、约束和历史，需对照 plan/constitution 清理正文 |
| esp32-p4-dufs-terminal | 媒体终端、中文输入 | 原镜像一致；BOARD_SHELL 是可复现操作/验收手册，不整份搬走或删除 |
| android-app-kit | 更新器、签名发布 | 原镜像一致；两 App 的接入约束分别归宿主，公共库规格继续独立 |
| dufs-client-rs | 公共 DUFS 客户端 | 原镜像一致；README 为操作入口 |
| bevy-game | 动画、活动、对白、纸片、职责、运行时 | 原镜像一致；docs 多为制作/回归手册，但 gallery-regression 等含旧结果和混合记录，仍需逐段收敛 |
| bevy-sketch | 绘画、保存、原生、输入性能 | 原镜像一致；许可、字体和上游参考保留 |
| bevy-canvas-kit | 通用画布基础 | 原镜像一致；无远程，不建远程/归档 |
| bevy-app-foundation | Web 外壳 | 原镜像一致；README 为操作入口 |
| bevy-project-planner | 结构、兼容、只读镜像、项目总览 | 原镜像一致；旧备份及生产 document.json 保留，不随同步删除 |
| bevy-env | 本机构建与隔离发布 | 原镜像一致；子仓库保持独立归属 |

## nix-tools 与 Clip 的实际归属

Clip 是 Git 子模块，规格由 nix-tools 统一维护已有历史依据：15def8c 明确“实现位于子模块、规格由 nix-tools 管理”。本次按用户绑定维护要求在 AGENTS、constitution 和子模块入口明确此归属；代码、Git、构建与发布不合并。

| 来源 | 去向/处理 |
| --- | --- |
| IMPLEMENTATION_PLAN.md | 005 Clip 核心、007 发布及暂停的公开发行、010 主机配置；旧平行计划删除，Git 保留 |
| docs/clipboard-sync-refactor.md | 006 限额/恢复、005 核心、007 发布；原路径缩为开发/测试手册 |
| clipboard-sync/docs/android-app-kit.md | 007 更新、反馈、批量取消与图标边界；子模块原路径保留操作手册 |
| docs/removable-backup-plan.md | 008 spec/plan/tasks；原纯计划文件删除 |
| deploy/docs/pc-release.md、production-verification.md、nuc-migration.md、host-structure-review.md | 耐久要求提炼至 009；原文件仍有旧流水，尚未完成正文清理，不能宣称全部退出 |
| docs/secret-vault-cli.md、nixos/reinstall-checklist.md | 操作手册保留；配置约束进入 010，安装边界进入 009 |
| docs/dufs-media-path-identity.md | UUID/路径要求进入 009，操作与参考保留；旧审计数字不是当前数据库证明 |
| docs/ssd201-discovery-firewall.md | 操作/接口来源参考保留；不触及 xiaoqiang 产品实现 |
| NUC 旧 nix-tools/todo.md | dsh Web 已被 ca987da 明确取消，不恢复；主机配置事项归 010；旧 checkout 尚未清理 |
| NUC 旧 clipboard-sync/todo.md | 既有能力归 005/006/007；e8217a1 已证明图片与友好错误不是剩余实现任务；固定 2 分钟失效未重新列入实施 |

旧规格删除的主要原因是“误把已实现当未实现”，不代表 Clip 永远不能有回溯需求；新规格明确基线与未验收项，不把历史 UI/编译验证标为本轮实测。

## 不能删除的部分

个人购物、学习、写作及随手想法按用户指令保留。上游原件、许可、编译期嵌入文本、操作手册和可再生运行数据不转成 spec。NUC /home/liou/dufs 属暂缓区。旧备份不作为活动计划，但未纳入本轮删除清单。

## 尚未闭环的清单

1. 根部三文件与 project-planner-md-trial 中的混合工程记录：必须逐段建立目标映射后再删，不能以曾经同步过推断已迁完。
2. device-bean-mobile/ANDROID_RELEASE、esp32-common/WRITER_RENDER_REFERENCES、P4 DISPLAY_BRINGUP、Bevy 回归手册和 nix-tools 部署/迁移文档中的需求、手册与历史仍有混杂；上述规格补迁不等于原文件全部清理。
3. NUC 旧 checkout 的 todo 与部分旧 docs 副本尚存在；旧版本状态不得覆盖本地 Git 的后续决定。
4. 写作机新增选型文档应由当前选型工作完成规范入口和同步；本次不混入提交。
5. 重新核对所有镜像引用及完成内容对账后，才允许把 004 的 T003/T004 勾完。当前结论不是“所有文档均已整理完成”。
