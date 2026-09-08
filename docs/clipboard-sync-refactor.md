# Clip 跨平台重构与风险记录

日期：2026-09-08。源码位于 nix-tools 的 clipboard-sync 子模块。
重构与加固完成后，用户授权提交发布 Android 0.1.13（源码 `8eaff20`，
标签 `android-v0.1.13`）。沿用 Actions 签名及自有域名发布流程；
不切换 NixOS、不替换正在运行的 daemon，手机由用户在 App 内升级。

## 模块职责

| 位置（相对 clipboard-sync） | 职责 |
| --- | --- |
| `src/transfer/mod.rs` | 对外 API、类型、协议限额与缓存 |
| `src/transfer/crypto.rs` | 请求认证、防重放、AEAD 分块读写 |
| `src/transfer/client.rs` / `server.rs` | 接收与发送编排 |
| `src/transfer/staging.rs` | 不完整接收批次的临时文件生命周期 |
| `src/transfer/payload.rs` | SHA-256、借用式 RGBA 校验和 PNG 编码 |
| `src/notify/mod.rs` | 用户接受事件与接收结果协调 |
| `src/notify/linux.rs` / `windows.rs` | 平台通知、确认与进度反馈 |
| `src/notify/saving.rs` / `clipboard.rs` | 下载持久化与系统剪贴板写入 |
| `src/clipboard/mod.rs` / `archive.rs` | 监听、目录打包 |
| `src/content.rs` | 三端共用的兼容通告描述与解析 |
| `src/transfer/cache.rs` / `connections.rs` / `workspace.rs` | 缓存限额、连接准入、崩溃临时文件清理 |
| 移动端 `inbox.rs` / Android `ReceiptStore.kt` | 待接收恢复、逐文件保存凭据与手动重试 |
| `mobile/src-tauri/src/{engine,settings,pairing,incoming,outgoing,updates}.rs` | 移动端业务分离；lib.rs 保留共享状态与命令注册 |
| `mobile/src-tauri/src/file_metadata.rs` | 不依赖 Tauri 的文件名与 MIME 策略，可独立运行测试 |
| Android `AndroidUpdater.kt` | 更新状态、下载校验、系统安装器交接；通过回调交给插件发送事件 |

原 816 行 transfer.rs、667 行 notify.rs、543 行 clipboard.rs 已拆分；
移动端业务与 Kotlin 更新器均已分离，后续加固继续在这些职责明确的模块内实现。
没有为简单的平台差异引入大型泛型框架。现有公开传输入口、v4 协议、端口、
配对身份、Tauri 命令名与 `update-progress` 事件名保持不变。

## 修复和优化

- 接收临时文件由“进程号+文件序号”改为随机名称与 create_new 原子创建。
  不同接收批次不再覆盖；网络中断、写盘失败、SHA 校验失败时清理本批次全部文件。
  Unix 临时文件以 0600 创建；接收结果持有剩余临时文件，销毁时自动清理。
- SHA-256 解析按字节处理，非 ASCII 的 64 字节字符串不会因 UTF-8 切片边界 panic。
- 内容缓存内部使用 Arc 快照，多个接收方共享同一内存块，释放缓存锁后再发送。
  后续加固已加入容量限制和拥有型文件快照；旧缓存淘汰不会删除活跃传输正在使用的文件。
- 图片解析/尺寸上限在共享库统一，桌面写剪贴板及 PNG 编码直接借用 RGBA 数据，
  避免原先整图复制和重复校验实现。
- 桌面同名图片不再覆盖。文件保存改用原子 hard_link 快路径，跨文件系统使用
  create_new + 流式复制，消除 exists-then-rename/copy 竞争窗口；失败清理部分目标。
  Windows 特殊设备名、控制字符及不安全路径名称被拒绝。
- Android APK 缓存文件名采用数值 versionCode，不再插入服务器提供的版本名称。
- 开发环境补齐桌面测试链接需要的 xdotool/libxdo，与已有 Nix 包依赖对齐。

## 兼容性边界

- Android 前端仍只用事件更新进度；保留已验证的监听 ACL、异步安装命令、UI 线程
  trigger，以及安装器交接后 resolve。保留已有进度快照 API，不在本轮混入删协议接口。
- 后续加固改变了关闭接收的行为：不再清空待接收/失败项；仅停止新通告接收。
  Android 服务改为 START_NOT_STICKY，进程被杀后不冒充仍可接收；重新打开 App 修复引擎与服务。
- 保留前端纯事件进度。在恢复可见时只读取一次快照补齐后台错过的状态，没有恢复定时进度轮询。
- 跨平台编译不能替代 Windows 托盘/剪贴板或 Android 真机生命周期验证。

## 后续加固：已实现（2026-09-08）

### 资源限额

- 每个进程发送缓存最多 64 项、128 MiB 内联数据；单项内联上限 64 MiB。
  文件缓存总量 20 GiB，单次接收批次也限 20 GiB、最多 256 个文件。
  这些是组件限额，不代表程序总 RSS 或全部临时目录合计只有 20 GiB：
  正在准备的新发送批次、接收批次、桌面失败重试暂存会占额外空间。
- 历史缓存 30 分钟过期，维护线程每 30 秒清理；最新一项保留到被新内容替换，
  避免未变化的剪贴板在缓存过期后无法重新发送。空间紧张按最旧非活跃项淘汰；
  活跃传输不可淘汰，占满时明确拒绝新缓存。
- 缓存拥有发送文件的生命周期，替代 Android 单独删除 outgoing_batches 路径的实现。
  发送准备也采用独立随机路径，ZIP 和文件复制过程中落实 20 GiB 上限并清理失败批次。
  Android 分享复制检查 shared 目录已有占用，失败清理本次文件。
- 服务端最多 8 个连接、同 IP 最多 2 个；未认证握手总限时 5 秒，拒绝占位慢连接；
  不在连接线程创建失败后遗失准入名额。Android 同时最多接收 2 项、消费 1 个分享。
- 防重放集合最多 65,536 项；满后拒绝新请求并提示重启服务，不淘汰旧 nonce 后放开重放。
  仍是原协议的**进程内**防重放，不宣称抵抗跨重启的历史请求重放。
- 新临时工作区使用持有到进程退出的文件锁。启动时只清理符合本工具标记且已无
  活跃持有者的遗留工作区；不删除其他运行实例或无关目录。旧版直接写到缓存根部的
  遗留文件不自动迁移/删除。

### 逗号文件名

- 三端共用 ContentInfo。新接收端按尾部字段定位，支持旧发送端含逗号的原始名称。
- 新发送端给旧字段提供安全显示名，必要时追加 name_hex 保存完整 UTF-8 名称。
  旧解析器忽略新字段，仍能接收，通知里的逗号可能显示为全角；新端还原完整名称。
- TCP 正文中的真实文件名和内容不变，不更换 v4 加密协议。恶意/无效字段与
  类似协议片段的文件名有回归测试。

### 生命周期与失败重试

- Android 收发、分享哈希与更新检查不再用同步 Tauri 命令占住调用路径；
  Kotlin 文件复制与保存使用固定工作线程。接收/分享忙碌标记由工作线程 RAII 持有，
  不依赖 WebView 的等待状态才能释放。
- Android 待接收最多 64 项，持久化到私有 inbox.json；重开 App 恢复 24 小时内记录。
  重复通告不覆盖失败原因，失败项显示“点击重试”；正在处理时禁用重复点击和取消。
- Android 按接收来源/项目序号/**已验证 SHA-256** 保存逐文件凭据，普通多文件部分
  失败后重试复用已保存的 URI，避免重复副本。凭据最多 4096 项、保留 7 天；
  达限明确拒绝，不无界增长。
- Android 重新可见时检查 Rust 收发线程与前台服务；退出的工作线程可按需重启，
  开关操作串行、持久化失败尝试恢复旧状态。服务启动有 3 秒确认期限，
  不把“发出了启动请求”立即算成正在接收。
- Linux/Windows 网络或保存失败会明确通知并提供再次接收确认，不自动重发副作用。
  只保留一份失败接收最多 30 分钟；文件保存成功项从重试清单移除，图片已经保存时
  剪贴板重试不重复保存 PNG。拒绝、换成其他接收项或超时会释放这份暂存。
- 网络失败为用户确认后重新拉取，不是断点续传。源端历史内容已过期时需要重新分享。

## 仍需验收或明确边界

1. 手机后台/锁屏、网络切换、系统回收后重开、Windows toast/文件锁需真机验证。
   Android 系统强制停止后的自动常驻恢复不在本方案内；用户重新打开 App 后恢复。
2. 原生媒体保存与凭据写入不是跨系统原子事务：若进程恰好在系统文件已写完、
   凭据尚未落盘的极小窗口崩溃，仍可能留下副本。不宣称严格 exactly-once。
   普通部分失败和已有凭据的重试已去重；断电级一致性应另做媒体事务/恢复扫描。
3. Android 分享读取或发送准备失败仍需用户重新从来源 App 分享；
   本轮“点击重试”主要覆盖接收路径，不承诺持久化所有外部 content URI 权限。
4. Linux 确认窗口仍以 PID + kill 取消，窗口替换竞争和 PID 复用专项改造尚未做；
   Windows 消息泵不变。更新下载取消/断点续传也未在本轮加入。

## 验证

Linux 30 项测试、严格 Clippy、Windows 程序和测试交叉编译、Android 目标含测试
编译及完整未签名 APK 打包已通过；纯元数据策略另有 2 项宿主测试通过。
Windows UI 与本轮 APK 尚未真机验收。没有把未签名验证包放到正式下载域名。

移动端完整 `cargo test --lib` 不能在 Linux 宿主直接运行：现有插件直接依赖 Tauri
的 Android API（不是本轮引入）。因此对纯策略单独测试，平台部分只在真实 Android
目标编译，不以假实现绕过平台依赖。最终结果也写入共享 a-done/a-observe 记录。
可复现命令（各自目录执行）：

```bash
# clipboard-sync/
devenv shell -- cargo test
devenv shell -- cargo clippy --all-targets -- -D warnings
devenv shell -- cargo build --target x86_64-pc-windows-gnu
devenv shell -- cargo test --target x86_64-pc-windows-gnu --no-run
devenv shell -- rustc --edition=2021 --test mobile/src-tauri/src/file_metadata.rs -o /tmp/clip-file-metadata-tests
/tmp/clip-file-metadata-tests

# clipboard-sync/mobile/
devenv shell -- cargo check --manifest-path src-tauri/Cargo.toml --target aarch64-linux-android --tests
devenv shell -- npm run tauri -- android build --target aarch64 --apk
```

发布前人工回归：双向文字/图片/多文件与重名保存、故意中断传输、配对与接收开关、
Windows toast/托盘、Linux 新通知替换旧通知、Android 纯事件升级与安装器返回。
