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
  - 记录后续将 Rust 项目正式打包为 flake package 的迁移路径；受 git submodule 边界影响，本轮不强行引入脆弱的本地 path 打包。
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
- 正式 `buildRustPackage` 迁移保留为后续工作：clipboard-sync 当前是独立 git
  submodule，在父 flake 中直接引用工作树路径会破坏远程 flake 的可复现性。

## 验收标准

- NixOS 和 standalone Home Manager 均可求值。
- standalone 生成的服务不引用必须存在的 NixOS system profile。
- `rerun.nu --home-target <name>` 的部署和自检使用同一 flake attr。
- Windows 编译模式和现成 exe 模式最终都安装到固定目录。
- 恶意或损坏的远端长度、文件数量和文件名不能造成任意路径写入或无界内存分配。
