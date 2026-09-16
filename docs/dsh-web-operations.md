# DSH Web 运维手册

`dsh web`（DeepSeek Harness Web GUI）跑在本机 `http://127.0.0.1:3080`，由 home-manager
的 `systemd.user.services.dsh-web` 管理（不 enable，保持手动启动语义）。

- 启动/重启：`systemctl --user restart dsh-web`
- 日志：`journalctl --user -u dsh-web --since "10 minutes ago"`
- 桌面入口：Mod+D → fuzzel → `dsh-web.desktop` → `dsh-web-toggle`

dsh 与 dsh-tui 通过 npm 全局装到 `~/.npm-global`，由 home-manager 的
`ensureDshLatest` 在每次 switch 时按 npm 最新版滚动更新。
**该机制是插件事故的直接触发源**：dsh 一升级，旧插件就可能加载失败，见下。

## 任务完成通知

**结论：通知由 dsh 的 hooks 桥接在主机上发，不是浏览器发的。**

dsh 前端完全不调用 Web Notification API（实测 `dsh-web-frontend` 构建产物中
`Notification` 出现 0 次，`requestPermission` 0 次），所以浏览器（Zen）无从弹起——
网页不主动调用，浏览器不能替它决定要通知什么。

改用 dsh 官方 hooks 桥接 `@deepseek-ai/dsh-hooks-claude-code`，它在**主机**上执行
命令，可直接走 D-Bus → mako：

| 位置 | 作用 | 归属 |
|---|---|---|
| `~/.dsh/hooks/notify-stop.sh` | 解析 payload → `notify-send` | home-manager 声明 |
| `~/.dsh/hooks/hooks.json` | `Stop` 事件 → 调用脚本 | home-manager 声明 |
| `~/.dsh/profiles/web/cordis.patch.yml` | 挂载 hooks 桥接 | dsh profile 生成物，手工维护 |

`Stop` 事件 = 一轮运行即将结束。通知显示工作区名（如 `nix-tools`）便于分辨项目。

### 协议约束（重要）

`dsh-hook-protocol` 规定**退出码 2 = 阻塞并强制 agent 再跑一轮**。因此钩子脚本在
**所有失败路径**都必须静默 `exit 0`，且不向 stdout 输出任何内容，否则每次任务结束
都会迫使 agent 继续，形成死循环。脚本已按此实现（无 `notify-send`、JSON 畸形、
缺字段全部吞掉并返回 0）。

`hooks.json` 由 `builtins.toJSON` 生成，避免手写 JSON 出错。

### 验证方法

```bash
# 直接喂真实形态的 payload，必须 exit 0
echo '{"session_id":"x","cwd":"/home/liou/nix-tools","hook_event_name":"Stop"}' \
  | ~/.dsh/hooks/notify-stop.sh; echo $?
makoctl history | head -5
```

会话日志里的 `hook/invoked` / `hook/result` 是 dsh 自己的权威记录：

```bash
for f in $(ls -t ~/.dsh/sessions/*/*/session.v3.jsonl.zstd | head -3); do
  zstd -dc "$f" | grep -c '"hook/invoked"'
done
```

## profile 插件

插件由 dsh 自己管理（`dsh plugin --profile web add/rm`，转发 pnpm），home-manager
不接管——插件是动态的、有依赖顺序，声明式管理会与手动操作冲突。

当前已装（dsh 0.1.5-rc.1，2026-09-16）：

| 插件 | 版本 | 用途 |
|---|---|---|
| `dsh-better-sidebar` | 0.19.1 | VSCode 式右侧栏 |
| `@zhangfengshun/dsh-remote-ssh` | 2.4.4 | 远程 SSH 开发 |
| `dsh-context` | 0.52.2 | 上下文洞察与 token 管理 |
| `@openviking/dsh-memory-plugin` | 0.3.2 | 跨会话记忆 |
| `dsh-blender` | 0.2.1 | Blender 建模/渲染工具 |

**`dsh-doctor` 刻意不装**，原因见下。

### 升级 dsh 后必须逐个复核插件

**2026-09-10 事故**：`ensureDshLatest` 把 dsh 从 `0.1.2-rc.1` 升到 `0.1.5-rc.1` 后，
`dsh-doctor@0.4.3` 加载失败：

```
Error: dsh: plugin tree failed to load:
failed to apply loader entry dsh-doctor: cannot get property "webServer" without inject
```

**整个 profile 起不来**，只能把坏掉的 profile 挪走并重建空白 profile 才恢复
（这就是 `~/.dsh/profiles/web.bak` 的由来）。

2026-09-16 复测：`dsh-doctor` 上游最新仍是 `0.4.3`（发布于 2026-08-15，比 dsh
0.1.5-rc.1 早近一个月），**同样崩溃**，无适配版本，故不安装。其余插件升级到当时
最新版后逐个在隔离 profile 中实测可启动。

复测方法（不碰正在使用的 3080）：

```bash
# 建隔离 profile 并验证启动；--port 0 让 OS 随机分配端口
dsh --profile webplugtest --from-default-profile web --dump-config >/dev/null
dsh plugin --profile webplugtest add <pkg>
timeout 90 dsh --profile webplugtest --port 0 --no-open & sleep 45; kill %1
```

### 两个已知坑

**1) `dsh plugin add` 不同步 `bundles`**

它只写 `package.json` 的 `dependencies`，**不会**把包名加进
`dsh.profile.bundles`。只加依赖不补 bundles，插件根本不会加载（表现为装完毫无变化）。
装完要手工按顺序把包名补进 `bundles`。

**2) `node-pty` 需要原生编译**

`dsh-better-sidebar` / `dsh-remote-ssh` 依赖 `node-pty`（原生模块，npm 不带 Linux
预编译产物）。NixOS 无 gcc/make，首次及每次 node-pty 升级后需用临时工具链重建：

```bash
cd ~/.dsh/profiles/web
# pnpm 11 默认拦 build scripts，先放行（dsh 首次会写成
# "set this to true or false" 占位符，需手工改成 true）
sed -i 's/^  node-pty: set this to true or false$/  node-pty: true/' pnpm-workspace.yaml
nix shell nixpkgs#gcc nixpkgs#gnumake nixpkgs#python3 \
  --command bash -c 'pnpm rebuild node-pty'
ls node_modules/node-pty/build/Release/pty.node   # 应存在
```

### 生效方式

`~/.dsh/profiles/web/package.json` 的 `patchReload: live` **只热重载
`cordis.patch.yml`**（launcher 会自建 hmr 服务监视该文件），**npm 依赖变更必须重启**：

```bash
systemctl --user restart dsh-web
```

重启会中断正在该进程里运行的会话（包括触发重启的那个对话）。
