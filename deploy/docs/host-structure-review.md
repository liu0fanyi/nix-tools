# nix-tools 设备结构与 NUC 重装适用性审查

日期：2026-09-05。范围：代码审查、SSH 只读盘点、官方安装文档核对；未执行安装、分区、重启或系统切换，未修改运行配置。

## 当前边界

| 对象 | 配置入口 | 当前管理范围 |
| --- | --- | --- |
| liu-bigpc | nixosConfigurations.liu-bigpc | NixOS 系统及集成 Home Manager；PC 构建控制端 |
| homebox | nixosConfigurations.homebox | NixOS 系统及集成 Home Manager；旧重装脚本目标 |
| nuc | homeConfigurations.liou-nuc | Pop!_OS 上的独立 Home Manager；另由 deploy 管理 Podman 服务 |
| aliyun | deploy/instances/aliyun.toml | Docker 应用发布，不由本仓库管理其操作系统 |

所以是三台个人设备的环境，加一个云端容器发布目标，不是三个同等完整的 NixOS host。
本机和 NUC OS 已实查；homebox 的旧 IP 192.168.1.6 拒绝 SSH，homebox.local 未解析，未确认其当前在线状态。

## 建议改进（未实施）

1. 保留单仓库和 deploy 边界。NixOS 管用户、磁盘、网络、防火墙、Podman、开机服务条件；Compose 继续管 Caddy/DUFS/tag-server，不把产品更新绑进 switch。
2. nixos/hosts 下按 homebox、liu-bigpc、nuc 分目录，各自维护真实硬件报告、引导和挂载；公共系统模块拆为 base、desktop、container-host 等按角色选择。现 configuration.nix 强制装桌面、输入法、代理，Home Manager 也统一导入全套桌面，不适合直接用作精简服务器。NUC 是否保留桌面待用户选择。
3. 增加 nuc 的 NixOS 输出并显式接入 nuc-tunnel；目前隧道只在 standalone liou-nuc 导入，不能认为改成 NixOS 就会自动继承。
4. 日常系统更新、容器发布、首次清盘安装使用独立入口。rerun.nu 默认 host=homebox，建议显式选择目标或核验本机身份后解析，不能在 PC 无参数套用 homebox。
5. 安装入口必须显式要求目标、主机配置和稳定磁盘 ID，核对型号/容量/序列号并确认清盘目标；即便传 --flake 也不能跳过磁盘身份检查。固定 nixos-anywhere 版本和 kexec 镜像校验；不要全局跳过 SSH 主机密钥校验。
6. 保留每台真实硬件报告，而不是安装时写公共 hardware-configuration.nix 后恢复占位。当前模式使后续构建不再使用首次安装的完整硬件信息。
7. 更新旧 README 命令：README.zh-CN.md 仍含 release-apps.py all，已不符合显式 --target 的现入口。先统一文档和目标模型，无需引入更大型部署框架。

## NUC 实测与旧安装器不匹配

- 系统 Pop!_OS 24.04，x86_64，7.6 GiB RAM，UEFI。kexec_load_disabled=0，lockdown=[none]；这些只表明未发现该类限制，不等于已验证真实 kexec。
- 有线 eno1 carrier=0；当前 wlp0s20f3 Wi-Fi 为 192.168.1.12。官方默认 nixos-anywhere 流程不支持 Wi-Fi。
- root@nuc.local 公钥登录失败，liou 的 sudo -n 需要密码；尚不满足 root SSH 或免密码 sudo 条件。非 root 的 EFI 可写预检也不能代表提升权限后的真实状态。
- 系统盘 nvme0n1：Samsung 970 EVO 250GB（232.9 GiB），稳定 ID nvme-eui.0025385691b22dce；现为 EFI/recovery/LUKS+LVM/swap。
- sda 是 5TB Art 资料盘（4.5 TiB，exFAT UUID 5F82-B190）；sdb 是 4TB project 资料盘（3.6 TiB，ext4 UUID 8bce6197-7281-40a0-84ec-e31c3d313877）。两者必须排除在格式化配置之外。
- 旧 disk-config.nix 默认清空 /dev/sda；安装器默认 homebox-install 档位。当前自动预检会因网络/多盘不合而停止，但传 --flake 会关闭自动磁盘检查，不能用此绕过防护。还会装成 homebox 并带入其桌面/休眠策略。
- scripts/restore-secrets.sh 主要恢复 mihomo、Rime、npm 工具，不负责完整恢复 NUC 的数据、业务状态和服务。

结论：nixos-anywhere 技术路线可用；现成包装脚本和 homebox 配置不能直接用于 NUC，仅改 --target 不适用。

## 重装前必须解决的数据边界

NUC /、/home/liou/dufs、/home/liou/dufs-lan 均在系统盘 data-root；现系统盘已用约 164 GiB。
默认发布备份 /home/liou/.local/state/dufs-plus/backups 同在该盘，不能作为清盘后的恢复来源。
manage.py backup 当前保存主/只读数据库、Authelia 数据库、workspace 的 .tag、实例配置、凭据和 DDNS 配置；它不是文件全集或整机备份，不能覆盖所有托管 Git、录音、静态资源和个人状态。

迁移应先盘点并异盘保存完整业务数据、隐藏状态/托管 Git、Bevy 静态产物、SSH/Syncthing 身份、凭据、Caddy 状态、模型、服务定义和恢复说明；业务停写后做最终一致性备份，并在另一位置做还原/校验。敏感备份不得放进对外 DUFS 可读目录。现有 project 盘容量看起来充足，但位置、权限及备份完整性未验收。

保留 /home/liou/dufs-lan、/home/liou/dufs、/media/liou/Art 和 /media/liou/project 的路径语义，媒体盘按 UUID 挂载；服务必须等待真实挂载，不能空目录启动。保留 UID=1000 和 subuid/subgid=100000:65536；旧主组 GID=1000，新 NixOS 组模型需明确处理文件归属，不能只对齐用户名。

NUC NixOS profile 还需声明服务端端口及来源限制、linger、Podman/ttyd socket、Compose 开机入口、反向 SSH 隧道及其身份。当前公共防火墙不是 NUC 业务端口清单，不能直接复用并假定所有访问正常。

## 建议迁移顺序

先做配置适配和异盘恢复演练，再安排停机。接有线网；准备现场显示器/键盘或可救援启动介质。
为 NUC 单独构建系统闭包并做 VM 安装验证；清盘配置只含确认后的 NVMe by-id。安装时建议物理拔掉两块资料盘。
保留现 LUKS 加密还是改为便于无人值守启动的布局，需要用户明确选择，不可隐式降级。
系统启动后先验收 SSH、网络和身份，再接回数据盘、恢复数据和服务，最后复验三个访问场景；PC 构建、NUC 运行和阿里云发布方式保持不变。

本审查不是清盘许可，也不是已通过 NUC 安装验收。没有执行安装脚本的 --check（其包装会先检查桌面 secrets 并禁用主机密钥验证）；使用等价只读命令核对条件，两个安装相关 Bash 文件仅做 bash -n 语法检查通过。

## 上游依据

- [nixos-anywhere 前置条件与数据丢失警告](https://github.com/nix-community/nixos-anywhere#prerequisites)：网络、kexec/RAM 与预先迁出重要数据。
- [官方 Quickstart](https://github.com/nix-community/nixos-anywhere/blob/main/docs/quickstart.md)：root/免密 sudo、正确磁盘、硬件报告及 VM 测试。

待办以 NUC todos 三文件为准，本页为检查快照，不另建独立计划。
