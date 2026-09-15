# Clip 开发与回归入口

规格由本仓库统一管理：[传输](../specs/005-clipboard-core/spec.md)、[限额与恢复](../specs/006-clipboard-reliability/spec.md)、[发布](../specs/007-clipboard-release/spec.md)。实现位于 clipboard-sync 子模块。

在子模块 devenv 中执行 cargo test、cargo clippy --all-targets -- -D warnings；Windows 程序与测试交叉编译，Android 在对应目标检查。纯元数据策略可独立宿主测试；Android-only 插件不能以宿主编译替代真机验收。

人工回归覆盖双向文字/图片/多文件、重名保存、中断重试、配对开关、Windows 通知、Linux 通知替换及 Android 升级返回。待验收项只在上述 specs/tasks.md 维护。

## 父仓库期望的 store path 为何随每个提交改变

`clipboard-sync/flake.nix` 把 `self.rev` 前 12 位作为 `revision` 传给 `nix/package.nix`，
后者写成 `CLIPBOARD_SYNC_REVISION` 环境变量，经 `build.rs` 注入并最终由 `main.rs` 的
`env!("CLIPBOARD_SYNC_REVISION")` 编进二进制。该变量参与 derivation 哈希，因此**每一个
提交都会产生新的 store path，即使是纯文档提交**。

实测（同一份 nixpkgs、同一份源码，只改 revision 字符串）：

```
revision=0dd79b278c7b -> /nix/store/81yzn02w...-clipboard-sync-0.2.0
revision=4202ff3dee7d -> /nix/store/mx4a1fcl0...-clipboard-sync-0.2.0
```

`nix/package.nix` 用 fileset 只把 `Cargo.toml`/`Cargo.lock`/`build.rs`/`src` 纳入源码
hash，但这一点被上述 revision 注入抵消：它挡不住无意义的重编译。

### 后果与约定

`rerun.nu` 在部署前会去 Cachix 校验该 path 是否存在，缺失即硬失败（避免静默本机编译
Rust）。于是「子模块 docs 提交带 `[skip ci]`」与「父仓库要求每个 revision 都有 CI 产物」
互相冲突，会让整条发布链卡住：

- `nix.yml` 触发条件是 `push: branches: [master]`，没有 paths 过滤；
  唯一能拦住 CI 的是 commit message 里的 `[skip ci]`。
- 带 `[skip ci]` 的提交不会产生 run，Cachix 便没有对应产物。

`update-clipboard-sync.nu` 的 `wait-for-ci` 已改为：轮询找不到 run 时，若该提交正是
`origin/master` 顶端，则自动 `gh workflow run nix.yml --ref master` 补跑，再继续等待；
若非顶端则明确报错（`workflow_dispatch` 只能针对分支顶端）。补跑产出的 `self.rev`
与目标提交一致，path 相同，因此能直接命中。

若 `rerun.nu` 再次报「Cachix 尚未发布 clipboard-sync」，可手工补跑后重试：

```bash
gh workflow run nix.yml --repo liu0fanyi/clipboard-sync --ref master
```
