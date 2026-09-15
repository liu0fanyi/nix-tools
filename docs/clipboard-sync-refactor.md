# Clip 开发与回归入口

规格由本仓库统一管理：[传输](../specs/005-clipboard-core/spec.md)、[限额与恢复](../specs/006-clipboard-reliability/spec.md)、[发布](../specs/007-clipboard-release/spec.md)。实现位于 clipboard-sync 子模块。

在子模块 devenv 中执行 cargo test、cargo clippy --all-targets -- -D warnings；Windows 程序与测试交叉编译，Android 在对应目标检查。纯元数据策略可独立宿主测试；Android-only 插件不能以宿主编译替代真机验收。

人工回归覆盖双向文字/图片/多文件、重名保存、中断重试、配对开关、Windows 通知、Linux 通知替换及 Android 升级返回。待验收项只在上述 specs/tasks.md 维护。

## 源码 revision 与 store path 的稳定性

**结论：revision 不再参与 derivation 哈希，store path 只由源码内容决定。**
同一份源码即使提交不同，也得到同一个 path，不再需要为纯文档提交重跑 CI。

### 曾经的问题

revision 原先作为 `CLIPBOARD_SYNC_REVISION` 构建输入，经 `build.rs` 用
`cargo:rustc-env` 烘焙进二进制，由 `main.rs` 的 `env!` 取用。它因此进入派生哈希：
**每个提交都会产生新的 store path，连纯文档提交也一样**。而 `nix/package.nix` 的
fileset（只取 `Cargo.toml`/`Cargo.lock`/`build.rs`/`src`）挡不住这一点。

实测（同一份 nixpkgs、同一份源码，只改 revision 字符串）：

```
revision=0dd79b278c7b -> /nix/store/81yzn02w...-clipboard-sync-0.2.0
revision=4202ff3dee7d -> /nix/store/mx4a1fcl0...-clipboard-sync-0.2.0
```

配合「docs 提交会被 GitHub 跳过 CI」，`rerun.nu` 的精确 Cachix 校验便无产物可命中，
发布链当场卡死。

### 现在的做法

revision 只用于 `--version`、doctor 与托盘标题展示，不影响协议或功能，因此改为
**运行期解析**：

- `src/main.rs` 的 `revision()` 依次读：`CLIPBOARD_SYNC_REVISION` 环境变量 →
  编译期 `option_env!`（回退）→ `"unknown"`。
- `build.rs`：`CLIPBOARD_SYNC_NO_BAKE` 存在时直接返回，不写 `rustc-env`。
  Nix 构建在 `nix/package.nix` 设置该变量；本地开发与 Windows CI 的裸
  `cargo build` 行为不变（仍会烘焙）。
- 父仓库在 `home-manager/nix_modules/clipboard-sync.nix` 用 `writeShellScriptBin`
  包一层，把 `inputs.clipboard-sync-src.rev` 作为环境变量注入后 `exec` 原始二进制。
  底层仍是同一个 Rust 包，`.#clipboard-sync` 与 Cachix 校验目标未被包装掩盖。

实证（两个源码与 `flake.lock` 完全相同、仅 commit 不同的仓库，以及真实仓库）：

```
revtest a (7d9ee67fac36) -> /nix/store/jdchs28f...-clipboard-sync-0.2.0
revtest b (b1a11eda5c2c) -> /nix/store/jdchs28f...-clipboard-sync-0.2.0
真实仓库  (14ef35add887) -> /nix/store/jdchs28f...-clipboard-sync-0.2.0
```

三条路径一致。Nix 产物内为 `unknown`，经包装层运行后显示正确 revision
（`clipboard-sync 0.2.0+14ef35add887 (protocol 4)`）。

### 仍然保留的兜底

revision 移出哈希解决的是「同一份源码重复产物」；但**源码真正变动**时仍需 CI 产物。
`update-clipboard-sync.nu` 的 `wait-for-ci` 保留补跑逻辑：轮询找不到 run 时，若该提交
正是 `origin/master` 顶端，则自动 `gh workflow run nix.yml --ref master` 再继续等待；
非顶端则明确报错（`workflow_dispatch` 只能针对分支顶端）。

若 `rerun.nu` 报「Cachix 尚未发布 clipboard-sync」，可手工补跑后重试：

```bash
gh workflow run nix.yml --repo liu0fanyi/clipboard-sync --ref master
```

注意 GitHub 扫描**整条 commit message**：正文里出现跳过标记的字面量同样会跳过 CI，
写文档或提交信息提到该机制时要避免直接写出。
