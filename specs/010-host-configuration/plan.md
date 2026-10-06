# 技术方案

FreeCAD 在 `home.nix` 与 Blender 并列声明，通过 `packages/freecad-bin.nix` 固定官方 1.1.3 AppImage 与 SHA-256，使用 appimageTools 包装。当前 nixpkgs 源码包未命中完整缓存，为避免长时间编译 IFC/FreeCAD 改用同版本官方二进制。验证完整 toplevel、HM generation 和命令/desktop 入口，不执行 switch。

EDA 使用独立 `home-manager/nix_modules/eda.nix` 模块；KiCad 来自锁定 nixpkgs，
嘉立创包位于 `home-manager/packages/lceda-pro.nix`，固定官方 3.2.203 ZIP 与哈希，
使用 buildFHSEnv 保留官方 Electron 及原生模块，生成桌面入口并安装上游图标。
不关闭 Electron 沙箱，不修改用户现有工程。升级需核对下载页、哈希及完整构建。

嘉立创下单助手封装在 `home-manager/packages/jlc-assistant.nix`，复用 FHS/Electron 方案，
并在解包时修正主程序、crashpad 与 sandbox helper 的可执行权限；由 EDA 模块传入
`primaryOutputScale`。百度网盘封装在 `home-manager/packages/baidunetdisk.nix`，
单独使用 `nixpkgs-gtkmm2` 锁定输入补足 GTK2 C++ 运行库，仅在 liu-bigpc 导入。
`flake.lock` 随本次输入变动固定其源及同步刷新过的现有输入。Mako 模块按应用名设置
常驻通知，Blueman 菜单成功返回时清除通知并禁止写入历史。

本次验收先完成包、完整 toplevel、HM generation 与生成配置构建；图形应用的登录、
文件传输及通知交互由桌面实测单独确认。任何构建结果均不等于系统已激活。

复用 nixos/hosts、Home Manager 模块与 vault 工具。远端旧 todo 中已完成项作为回溯需求，不直接复制旧勾选。

系统构建、运行激活、桌面实机验证是独立阶段，旧记录中 deferred switch 仍不可认定为已激活。

## 宪法检查

蓝牙复用 NixOS hardware.bluetooth / services.blueman，在 liu-bigpc 主机模块启用；
Home Manager Niri 模块按 isLiuBigpc 条件生成 Waybar bluetooth 配置，点击使用 store 中的 blueman-manager。

Mako 对 app-name=blueman actionable 设置独立超时和格式；点击通过 makoctl menu -n "$id"
调用 fuzzel，使用固定程序路径并携带 jq 依赖。普通通知及勿扰模式保留原行为。

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。

## 截图标注方案

在 Niri Home Manager 模块中仅为 liu-bigpc 安装锁定 nixpkgs 的 Satty。
`Shift+Print` 调用 writeShellApplication 封装的 `screenshot-edit`，使用现有
slurp 选区、grim 截图，再以临时 PNG 打开 Satty；复制使用 wl-copy，保存路径
使用带纳秒时间戳的 `~/Pictures/Screenshots/Edited-*.png`。flock 防止重复启动，
取消选区直接退出，EXIT trap 清理临时图片。其他截图绑定不变。

宪法检查：仅 PC 权威仓库配置；未引入外部参考源码或文档原件，依赖沿用
锁定 nixpkgs；说明放 docs、需求放 specs；不部署、不执行系统 switch。
验证必须覆盖 liu-bigpc 完整 toplevel、Home Manager generation 和生成 KDL。

## 快捷键录屏方案

仅 liu-bigpc 在 Niri 模块安装锁定 nixpkgs 的 wf-recorder 与 screen-record-toggle。
Scroll_Lock 通过 flock 串行切换，slurp 取消即退出。录屏运行于专属临时
`nix-tools-screen-record.service`，systemd-run 显式传递 Wayland、运行目录和通知/文件
环境；再次触发用 systemctl stop，只向该单元发 SIGINT 并等待文件正常收尾。
ExecStopPost 替换开始通知，按 SERVICE_RESULT 与文件存在性区分保存/失败。
录制期间 systemd-inhibit 阻止 idle/sleep，结束释放；单元结束自动回收，无常驻服务。
MP4 使用 libx264/yuv420p、24fps、veryfast/crf24、maxrate=4000000、bufsize=8000000、
g=48；FFmpeg pad 修正奇数尺寸。音频 pulse backend、AAC b=128000、48kHz。

继续遵守上述宪法检查；仅更新 PC 配置和合法资料镜像，不替用户 switch。
验证完整系统/HM、KDL、脚本检查及不捕获桌面的录屏控制测试；真实画面与性能待用户验收。

### 录屏后文件剪贴板

ExecStopPost 成功且文件非空时，以 Python Path.as_uri 编码路径（含空格、中文和
特殊字符），通过 wl-copy 的 text/uri-list 提供文件 URI。wl-copy 单独运行在
唯一命名的 transient user service 中，Type=forking 等待默认 daemon 初始化；
不让剪贴板 owner 随录屏服务收尾被杀掉。剪贴板被替换时 owner 自动退出并回收
单元。失败分支不复制，复制失败保留视频并明确通知。命令构造与错误分支采用
隔离 mock 验证，不覆盖用户当前剪贴板；真实应用粘贴待用户验收。

### 声音菜单与轻量剪辑

screen-record-audio 包装 scripts/screen-record-audio.py；Waybar 每2秒显示录屏/音源状态，
左键 fuzzel 选择来源并写入 XDG_STATE_HOME，右键调用原录屏切换入口。与录屏入口共享
flock，录制期间拒绝选择。系统声音取默认 sink 的 monitor；麦克风仅选择非 monitor
输入，优先默认输入。both 创建独立 module-null-sink 与两个 module-loopback，
逐次记录模块 ID、名称和精确 sink 参数，失败与结束时逆序清理；音频服务重启后
不得因 ID 复用误删其他模块。不设置默认设备、不把麦克风连接真实扬声器。

Shift+Scroll_Lock 传 --edit，在录屏单元保存 SCREEN_RECORD_EDIT；成功收尾后另启
transient 单元运行锁定 nixpkgs 的 Avidemux --load，避免编辑器随录屏单元结束。
Copy 模式支持关键帧剪切，另存 MP4；不监控编辑器输出、不自动替换原文件剪贴板。
Python 隔离回归覆盖音源、混音部分失败及模块所有权；脚本控制检查不捕获桌面或
真实音频，不修改用户剪贴板。软件包、完整系统/HM、KDL/Waybar 配置与合成编码验证
和用户桌面验收分开记录。依赖沿用锁定 nixpkgs，无新增外部参考仓库或系统 switch。

### Avidemux 蓝屏预览修复

实机截图为 Lavcodec / VDPAU，用户 config3 为 videodevice=4 且 vdpau/libva 解码关闭；
锁定 2.8.1 的 GUI_render.h 确认4为VDPAU、0为原生渲染（Qt GUI显示Qt）。
screen-record-edit 在启动前合并 videodevice=0、关闭硬件解码；其他偏好保留，
变更前复制带纳秒时间戳备份，再以同目录临时文件原子替换。ExecStopPost 调用
该入口，已有视频可用同一命令重开。不直接写当前用户配置或终止其编辑器；
用临时HOME与独立Xvfb检查视频副本加载、实际预览画面，再验证完整系统/HM和脚本构建。
offscreen插件无法提供VDPAU初始化所需的X显示，故使用独立虚拟显示；不连接或截取用户桌面。

## Screen Cut声明式安装与录屏接线
packages/screen-cut.nix固定公开Cachix desktop bundle，通过fetchClosure读取签名可信的运行闭包，
小symlinkJoin安装到x86_64 Linux Niri的home.packages，菜单由desktop文件自动索引。
rerun首次运行也启用fetch-closure，NixOS/非NixOS配置持久声明支持。
已有录屏收尾服务在成功+非空+--edit时直接传路径给screen-record-edit→screen-cut；
普通录屏及失败不打开，无新自启动、无源码路径、无额外profile安装。
完整toplevel、Home Manager generation、KDL、ShellCheck与隔离收尾行为验证后用户switch。

## 快捷键统一修订
截图继续用Print及Shift+Print；普通/编辑录屏改Scroll_Lock/Shift+Scroll_Lock，无需Cmd或Alt组合。
预先扫描官方模板与自定义绑定确认未占用，保留原Ctrl+Print/Alt+Print截图语义。
生成最终KDL后检查唯一性与Niri validate；完整系统和HM构建，不改变录制/编辑脚本。

### Screen Cut波形与恢复缓存更新
沿用packages/screen-cut.nix fetchClosure，仅更新经发布验证的desktop bundle；
核对完整liu-bigpc toplevel、HM generation与desktop实际程序目标。录屏快捷键和启动脚本不变。
上级目录来源分层与本仓constitution检查通过，无新增外部参考、无系统切换。

### Screen Cut切点与字幕升级
沿用公开Cachix fetchClosure，固定006/007发布的desktop bundle，验证缓存签名、
完整liu-bigpc系统/HM和实际命令/desktop目标。上级规则和本仓宪法检查通过；
无新增外部参考，不改快捷键、不切换系统。已有AGENTS、flake.lock和home.nix改动保留，
构建包含当前工作树，提交只包含本次包pin与010规格。

### Screen Cut配音升级
沿用fetchClosure，固定008 desktop bundle；核对签名、匿名归档、完整liu-bigpc系统/HM和实际命令/desktop目标。
41项单元测试、隔离GUI合成声音和mock输入验证；不自动采集用户麦克风。真实麦克风及输入延迟由用户验收。
Constitution Check通过：PC构建、目录分层、无新增外部参考、镜像白名单、保留既有工作树改动；不切换系统。

### Screen Cut缓存提示方案
packages/screen-cut.nix通过passthru公开原缓存bundle，flake输出screen-cut-binary-path，rerun复用Tag Browser所在主机分支核对/预取并显示命中。
不重复硬编码pin、不把本地symlinkJoin当作已上传包；只读运行独立检查段和完整系统/HM构建，不执行switch。

### Screen Mark接线方案
packages/screen-mark.nix固定已构建desktop bundle，flake导出唯一binaryPath，rerun当前liu-bigpc分支核对/预取并打印命中。Niri screenshot-edit保留flock/slurp/grim/trap，传PNG和另存目标给screen-mark；运行依赖声明，原截图/录屏动作不改。
Constitution Check：独立产品规格、PC构建、无外部参考，缓存只运行闭包；预演白名单镜像，完整系统/HM/Niri与ShellCheck及模拟截图流程检查，用户switch。

### Screen Mark共享核心发行
Screen Mark的源码Nix输入锁定canvas-kit e5237aa70e628f585418cca19b4e91196880f0a9，系统仅fetchClosure读取成品bundle j1cvwiafizx98f8qzwj2n6szalsqldm8（core 0i6739bmprmv7hbnqhsfnq4830xsnrfy）。不把源码依赖加入宿主flake、不上传共享仓源码，原截屏/录屏入口不改；核对运行闭包签名、rerun独立预检和完整host/HM构建，不执行switch。

## YouTube 视频下载方案

在 `home-manager/home.nix` 的 `home.packages` 添加 `pkgs.yt-dlp`。锁定 nixpkgs 包默认已启用 FFmpeg 与 JavaScript 支持，包含 Deno 和 yt-dlp-ejs，无需额外安装运行时或自写包装器。保留原有 FFmpeg。

宪法检查：仅修改 PC 权威配置；需求与任务归入现有 010 规格，操作说明放 docs。没有引入外部参考仓库或文档原件，无新增 gitlink；依赖沿用固定的 flake.lock。保留既有工作树改动，不刷新锁定、不执行 switch；资料仅通过既有白名单镜像入口同步。

## 本地字幕 OCR 方案

`scripts/subtitle-ocr`构建独立Nix运行环境并初始化版本固定的用户缓存venv；核心Python脚本探测区域后以4fps裁剪识别、精确合并及不改数量的闪烁桥接，输出SRT、诊断报告、批次索引和分块检查点。监测模式处理落盘稳定的新视频；复用输入/参数签名一致的检查点，不覆盖非工具管理或外部编辑过的字幕。

Constitution Check：仅PC工具和现有010规格；无外部Git参考、无新增gitlink，依赖是常规包管理且版本固定。docs是自编说明，规格仍在specs；NUC资料白名单只读预演后同步。独立runtime构建不涉及系统配置，无需switch或完整系统重建；用户既有工作树改动保留。

## 视频菜谱工具实施方案

### 已实现的链路

契约、内部/阶段JSON Schema和四阶段提示词位于010/contracts，自编手册位于docs，工具与固定模板位于scripts，权威食材词典位于config/recipe/ingredients.json。内部JSON是事实源；Schema及跨记录验收后固定导出HTML、Recipe JSON和食材索引。JSON合法不能代替语义与视觉核对。

`recipe-library`使用独立Nix运行环境与固定验证依赖，接受已经整理好的内部菜谱；`recipe-ingredients.py`负责collect/prepare-review/apply/reindex/directory，共享JS实现别名、父类、可选配料及多词AND检索。目录内嵌索引，在file://下直接浏览，无fetch依赖。当前词典revision=3。

十份真实试稿的文本整理和选图由交互式AI完成，独立语义审阅为pending。试验采用每步3张代表帧及一次定点补帧，记录实际策略；没有执行默认1秒扫描或对全部未选候选逐张精细核验。用户数据留Downloads。`recipe-batch`现已固化登记/字幕准备、任务包交换、代表帧抽取、组装与导出；状态使用SQLite单写者事务和只读查询，成功阶段与结果按摘要不可变缓存。已摆脱/tmp专用组装入口，但AI阶段仍需导入实际执行结果。

### 下一步：可续跑控制器

1. 把试验中的来源登记、字幕准备、候选抽帧和阶段输入准备迁入可复用工具；先支持单视频及十道菜清单，源媒体只读，稳定ID去重，输出新版本。
2. 实现持久任务状态、阶段检查点、状态查询/日志、失败重试和中断恢复。先支持模型任务包导出/结果导入，从而独立验证控制器；状态存储与网页搜索索引分开设计，本版为持久事务状态采用本地SQLite，网页索引保持JSON。
3. 接入文本/视觉模型适配器，落实访问配置、上传范围、预算上限、超时/拒绝处理及实际用量记录。配置前不发起外部模型调用；控制器无需聊天常驻。
4. 用独立审阅阶段复核现有十道菜，处理疑点、数字/用量及缺图，失败留needs_review；重跑只能更新受影响阶段，保留版本与审计记录。
5. 通过恢复和质量验收后扩大到30–50个视频，再决定全库运行。每批重新审阅全库食材清单、同步词典与目录，报告质量、耗时和实际开销；达到质量门槛前不直接处理4000多条。

### 验收与存储边界

结构/输出保护测试用于程序验收，独立语义审阅和视觉核对用于内容验收，人工校对单独登记。控制器须验证强制中断后的续跑、不重复已完成调用、配置变化后的受影响阶段重算、预算耗尽后暂停及坏结果隔离。后台任务记录即使使用SQLite，静态网页仍可导出JSON索引；模拟4200项的检索性能不证明全库菜谱质量或手机性能。

Constitution Check：PC权威源，沿用010工具范围；自编资料在docs、需求与契约在specs，无新外部Git参考或gitlink。源媒体及私有处理数据不进入Git或NUC资料镜像，保护既有AGENTS/flake.lock/home.nix改动；不switch或部署。资料同步仅按既定todos/nix-tools白名单，先预演、再checksum核验。

P0实现细则见[批处理契约](contracts/video-recipe-batch.md)。抽帧采用每窗口均匀代表、每步最多12张，偏离默认全窗口扫描；无自动扩窗/补帧。P1已补齐食材/既有疑点完整审阅、视觉观察转帧证据、白名单修复及独立复审；文本/视觉各最多两次修复。Responses适配器默认预览，实际服务/凭证/上传范围/预算尚待配置，十道菜真实独立复核未执行。不得由事实通过自动认证食材。

P1 Constitution Check：代码与配置样例在本机权威仓库，说明在docs、契约在specs；接口依据引用官方在线文档，无新增外部参考仓库或原始文件，gitlink规则不适用。私有媒体和模型响应留Downloads，不进入Git或NUC规格镜像。不修改系统、锁定、部署或下载状态。
