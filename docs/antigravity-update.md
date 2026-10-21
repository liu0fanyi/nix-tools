# 优先工具与 Antigravity 更新

## 2026-10-20 四项安全与稳定性更新（阶段 AG）

| 工具 | 原安装版 | 本次固定版本 | 目的 |
| --- | --- | --- | --- |
| FreeCAD | 1.1.3 | 1.1.4 | FCStd 文件处理安全修复 |
| GitHub CLI | 2.101.0 | 2.102.0 | 下载写入、来源校验、技能安装参数处理修复 |
| pnpm | 12.3.4 | 12.14.0 | 输出管道断开转储、安装等待和缓存修复 |
| KiCad | 10.0.6 | 10.0.7 | 崩溃、铺铜/DRC 和工程导入修复 |

系统原 nixpkgs 及已有应用输入不变，仅新增 `tool-updates` 输入并固定
`7a6522c868711d06e3a520bbcdfafe9806f4337f`，只消费其中的 gh 和完整 KiCad 包。
两者命中 Nix 二进制缓存；不使用全局 overlay，不更新 Podman/npm 或其余工具。
该输入的 pnpm 仅12.9.0，因此 pnpm 独立固定官方 npm 平台包
`@pnpm/exe.linux-x64-musl@12.14.0` 及官方 registry 的 SHA512；保留 pnpm/pnpx/pn/pnx
命令和补全，仍通过 Nix 安装，未新增 npm 全局副本。

FreeCAD 沿用 `home-manager/packages/freecad-bin.nix` 的官方 AppImage 包装，版本与
SHA256 同时更新，摘要已与官方 Release asset.digest 及 SHA256 文本交叉核对。
工程与用户设置不改；KiCad 保留符号/封装/3D 库及原命令和桌面入口。

完整系统/HM 构建通过：

- 系统：`/nix/store/lfqd67qf36fkq6y9rv86i8x5g7ca6lpm-nixos-system-liu-bigpc-26.11.20260922.b6c98e9`
- HM：`/nix/store/lsmvj6ksqb9bvsdvhlgr706q86radhaz-home-manager-generation`

四项版本、命令及桌面入口核对正确；隔离临时 HOME/缓存/运行目录下，pnpm 离线
安装与 stdout 读端关闭回归通过（退出0），KiCad CLI 空原理图 SVG 导出通过，
FreeCAD 控制台新建/保存/重开 FCStd 和 STEP 导出通过。HM 激活脚本/hm-backup、
相关用户服务路径与系统设备权限已核对。报告在`/tmp/tool-fixes-verification-20261020.json`。

构建包含工作区已有配置。Agent 未执行 switch、未操作真实工程或重开用户 GUI；
阶段 AG 剩余1项 AG3：用户手动应用后验证工程打开/保存、输入法、缩放和 KiCad 3D 视图。
应用命令仍为本页末尾的 `nu rerun.nu liou --host liu-bigpc`。

官方说明：[FreeCAD 1.1.4](https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.4)、
[gh 2.102.0](https://github.com/cli/cli/releases/tag/v2.102.0)、
[pnpm 12.14.0](https://github.com/pnpm/pnpm/releases/tag/v12.14.0)、
[KiCad 10.0.7](https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/)。

## 2026-10-18 优先工具更新（阶段 AC）

| 工具 | 原安装版 | 本次固定版本 |
| --- | --- | --- |
| Codex CLI | 0.159.3 | 0.163.0 |
| Zen | 1.22.2b | 1.23.3b |
| Cursor | 3.21.9 | 3.25.6 |
| Antigravity 主应用 | 2.22.0 | 2.24.0 |
| Antigravity CLI（agy） | 1.3.2 | 1.4.0 |
| uv / uvx | 0.12.17 | 0.13.1 |

Codex、Zen、Antigravity 的独立输入锁定到 `8dc8656b82ed75c9f76002f1368415b1e8471264`、
`5a0d21f99706b231df9ff35ab95dbccda88414d8`、`9ef62b6440b1a33476498b97f9ba57bb28aff846`。
Codex 的 flake-utils 依赖随上游锁定一起更新；系统 nixpkgs 及其他工具输入保持原值。

Cursor 在 `home-manager/nix_modules/cursor.nix` 覆盖官方 AppImage 的版本、哈希及提取路径，
保留原有 Nix 打包、Wayland/fcitx5 参数和桌面入口。uv 在 `home-manager/home.nix`
固定官方 musl 静态发行包，通过 `programs.uv.package` 提供 uv/uvx 和补全；
下载包已与官方 SHA256 文件核对。更新时同时改版本、来源和哈希，完整构建后再应用。
Zen 沿用已有 FFmpeg 包装，核心版本按 Gecko 158 选择解码库。上游 flake 的
1.23.3b 下载哈希与官方实际文件不同；已核对官方 Release asset.digest 为
`bb2045d3e21654d40fe841250092eeadfd2c1fc831eefb509222773c8bdca149`，
在 home.nix 固定官方摘要，继续执行 Nix 校验。不修改默认关联或用户配置。

完整系统与 Home Manager 构建通过：

- 系统：`/nix/store/960lw1dpjyrlpn9hwnclkb1p56dcln60-nixos-system-liu-bigpc-26.11.20260922.b6c98e9`
- HM：`/nix/store/0i09gkw18y6v3yhb5bwjly2bnpig88ca-home-manager-generation`

新 HM 环境的 codex/zen/cursor/agy/uv/uvx 版本命令均通过；Cursor package.json 与
Antigravity app.asar 分别为3.25.6和2.24.0。uv 临时项目初始化、桌面入口、Zen
ffmpeg_9 链接、HM 激活脚本/hm-backup、用户服务路径及系统设备权限核对完成。
构建包含工作区已有配置；验证报告在`/tmp/tool-upgrade-verification-20261018.json`。

Agent 未执行系统 switch，也未重开用户的 GUI。阶段 AC 剩余1项 AC3：由用户在普通
终端运行下文命令；现有任务结束后重开应用，复核实际版本、登录、输入法和浏览器媒体。
后续更新五项工具时，仍先按下文构建两个完整产物，再手动应用。

## Antigravity 单项更新与历史

`home-manager/nix_modules/antigravity.nix` 安装 Antigravity 主应用及 `agy` CLI，
使用 autoPatchelf 变体。版本通过 `flake.lock` 的 `antigravity-nix` 输入固定，
上游为 [jacopone/antigravity-nix](https://github.com/jacopone/antigravity-nix)。
该输入的 nixpkgs follows 本仓库，不单独刷新系统依赖。

2026-10-10 将输入从 `5659be61a6bfad97d934ab43f4dd9edb463612b3`
更新至 `bb5f514a1efaa377f823e5c41d957cb5c9f2d579`：主应用
**2.18.1 → 2.22.0-5446056071266304**，CLI
**1.2.14 → 1.3.2-5813501495738368**。
本次锁定文件只有 `antigravity-nix` 节点发生变化。

验证通过：完整 liu-bigpc NixOS toplevel 与 Home Manager generation 构建成功，
HM 的应用和 CLI 命令均指向新包；包内 app.asar/package.json 版本为 2.22.0，
`agy --version` 输出 1.3.2；桌面入口与 `HOME_MANAGER_BACKUP_EXT=hm-backup` 已核对。
未执行系统 switch，未启动新版 GUI 接管当前会话。

以后更新并验证：

```bash
nix flake update antigravity-nix
nix build --no-link .#nixosConfigurations.liu-bigpc.config.system.build.toplevel \
  .#nixosConfigurations.liu-bigpc.config.home-manager.users.liou.home.activationPackage
```

构建通过后，用户在普通终端手动应用：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```

等待 Antigravity 当前任务结束，再退出重开。构建验证与实际界面、登录和代理功能验收分开记录。
