# NUC 重装：准备与恢复

## 最终重启验收（2026-09-06）

修复后已再次整机重启：Art 检查退出 0、正常读写挂载，8 个容器等待磁盘就绪后
自动启动；容器内 Art 列目录及 DUFS JSON 接口 200，Authelia 200，隧道 active，
系统失败服务为 0。用户确认访问正常，决定保留每次挂载前检查 Art 的现有策略。
本次检查约 9 分钟；下方“待冷启动验证”是历史阶段状态，已由本节取代。

用户授权仅保留最终业务快照 20260906T062004.899909Z（约 3.24 GB），
恢复演练报告另存其内 restore-rehearsal-report.json；旧全量、中断和演练数据副本
列为清理目标，不涉及资料盘上的正常业务文件。

## Art 容器挂载时序修复（2026-09-06）

宿主 Art 已挂载并不代表容器可访问：容器 16:15 启动，exFAT 16:24 才挂载完成，
rprivate 绑定保留了旧 autofs 入口，tag-server 列目录报 ELOOP，网页出现 403/500。
生成的 compose-control 现在对 up/start/restart 检查 required_mounts：先用有界 stat
触发自动挂载，再用 findmnt 排除 autofs 占位；未就绪则失败，由服务每 15 秒重试。
down 等清理操作不受此门禁影响。不修改磁盘、权限或挂载传播规则。

已同步生成器和启动入口，旧入口保留为 compose-control.before-art-20260906。
仅重启 dufs 与 tag-server 两个受影响容器；容器中确认 exFAT 子挂载存在，
Art 列目录成功，Authelia 200。30 项部署测试通过；仍待下一次整机冷启动验收。

## 重启验收与启动修复（2026-09-06）

用户已再次重启。8 个容器自动启动，Authelia healthy、登录页 200、LAN 匿名 401，
系统 mihomo、Avahi 与 coretemp 温度读取正常。Art 再次访问触发 exFAT 检查，仍在推进，
未强停或关闭校验；随后检查成功（Result=success、退出 0），Art 已读写挂载。

Compose 初始启动使用未包装的 newuidmap，报权限错误；重试后恢复。
生成器已为 Compose 和 ttyd 的 PATH 优先加入 /run/wrappers/bin，30 项部署测试通过。
用户再次明确许可后，已在 NUC 保留两个服务文件的 .before-path-20260906 旧副本，
应用 PATH 修复，同步运行目录副本及 NUC render.py，然后 daemon-reload，未重启业务。
独立用户服务验证 newuidmap/newgidmap 均解析为 /run/wrappers/bin 下的包装工具，
podman unshare 成功；8 个容器持续运行。仍需修复后的再次冷启动，不能提前宣称通过。

阿里云原 SSH 服务 ClientAliveInterval=0，NUC 重启前的旧会话持续占用 2222。
已在阿里云安装 deploy/ssh/20-client-alive.conf 的副本到
/etc/ssh/sshd_config.d/20-client-alive.conf，sshd -t 与有效配置检查通过，reload ssh
而非重启；仅终止已确认的旧隧道 sshd PID 2167049，NUC autossh 随即自动恢复。
此配置每 60 秒探测，连续 3 次未回应才断开；正常空闲连接保留，登录权限未改变。
官方语义：https://man.openbsd.org/sshd_config#ClientAliveInterval 。
该文件属于阿里云宿主 SSH 配置，当前需人工安装，不由容器 infra 发布自动覆盖。
回滚仅删除这一新增配置文件、sshd -t 后 reload ssh，不修改既有 sshd_config。

## 收尾：用户确认业务正常（2026-09-06）

用户已确认外网恢复、业务均正常，并授权撤销临时 root 权限及提交推送。
后续维护使用 `liou@nuc.local` 或无线地址 `192.168.1.12`；有线已拔除。
此前 DDNS 指向无线 IPv6、回程优先有线，与严格反向路径过滤冲突；仅保留无线后
用户确认外网恢复。未放宽防火墙。未来重新接有线时需统一 DDNS 网卡与路由。

移除本次新增的 PC 临时 root 公钥，保留原有独立管理员公钥和 liou 正常登录。
新启动配置不再包含临时公钥，当前系统也同步撤销该条授权。备份全部保留。
安装后已成功实机启动；业务恢复之后的再次整机重启验收尚未执行，不宣称通过。
下方历史阶段的临时 root 有效期或未恢复说明已被本节取代。

## 最新：业务恢复与 NUC 桌面适配（2026-09-06）

- 两块资料盘按 UUID 挂载；Art exFAT 检查 Result=success、退出 0。
- 最终业务快照的 dufs/dufs-lan、凭据、Caddy/Authelia/DDNS 和运行目录均恢复，
  checksum/权限验证通过，三份 SQLite integrity_check 为 ok。旧全量备份补回
  182 MiB Whisper 模型、Syncthing secrets 文件夹；原 SSH 与 Syncthing 身份恢复。
  新生成 Syncthing 状态保留于 ~/.local/state/syncthing-before-restore-20260906。
- 六个生产镜像从 PC 恢复且摘要一致，tag-server 恢复 da887616503d；临时 PC
  镜像导出策略已删除。八个容器运行，Authelia healthy。主 HTTPS 认证跳转与登录页
  smoke 通过，LAN 与密码只读入口匿名返回 401。只读入口不适用要求 Authelia 页
  返回 200 的通用 smoke；该检测失败不是服务停机。外网 CDN 和实际登录交互尚待验收。
- ttyd/dufs-plus-compose 已 enable，用户 linger 启用；autossh、clipboard-sync、
  Syncthing active，Syncthing API 报 idle、errors=0。尚未做业务恢复后的重启验收。
- NUC terminal_bin 显式设为 /etc/profiles/per-user/liou/bin，未设置时兼容旧
  ~/.nix-profile/bin。部署 30 项测试及迁移 21 项测试通过。
- mihomo 外置盘配置已为明文，恢复到 clashtui 运行目录并补 GeoData 后，控制接口
  200、代理出站 204。没有重新解密或输出订阅密钥。
- NUC ACPI thermal_zone0 返回 -263200，Waybar 显示约 65273°C；改为按 coretemp
  与 Package id 0 标签发现 CPU 温度，并过滤无效值，实际约 56°C。仅 NUC 使用
  新组件，其他设备保持原配置。Home Manager 已激活；系统 boot 配置同步该修复，
  不执行运行时 switch。临时 root 授权到期时间仍为 20260907070324Z。

下面是历史阶段记录，未恢复等状态不再代表当前进度。

## 最新：实机重装并启动成功（2026-09-06）

用户明确授权清空 Samsung 970 EVO 250GB，两块外置资料盘安全卸载后物理拔除。
通过固定版本 nixos-anywhere 分阶段 kexec、分区、安装和重启，严格校验 nuc.local
主机密钥并保留原主机密钥。上游默认关闭校验且追加选项无法覆盖，本次使用 PC 临时
副本修正该默认值；仓库只读 install-check/install-plan 未改为自动清盘入口。

实机当前闭包：`/nix/store/mk0hpyfwil0msmqb3271xi92kdmjrdfy-nixos-system-nuc-26.11.20260829.e8be781`。
SSH 已验证从 NVMe 启动，根目录 ext4、EFI vfat 可写、16 GiB swap 生效；sshd、
NetworkManager、greetd、home-manager-liou 均 active，检查时 failed units 为 0。
桌面实际交互尚待用户设置 liou 密码并登录。业务未恢复，资料盘仍未接回。
新系统 root 公钥也限制 PC 192.168.1.100，20260907070324Z 到期，恢复后应移除。

安装中发现并处理两项问题：

- PC glibc 缓存摘要损坏，传输校验阻止清盘。通过其 derivation 的 nix build --repair
  从官方缓存修复后，完整系统及分区闭包递归内容校验通过，才继续。
- EFI 新分区仍识别旧的约 487 MiB FAT，写引导器时损坏并只读；仅对已核验的 1 GiB
  disk-system-ESP 重新建立 FAT32，根分区不动。fsck.fat -n 通过后重装引导器成功。
  空白虚拟盘测试未覆盖此旧盘残留场景；今后安装入口需加入新建文件系统尺寸校验。

本记录只保存在 PC；冻结期间不向 NUC 业务目录发布，也不修改离线备份。
下方均为历史阶段记录，尚未安装等状态不再适用。

## 最新：虚拟磁盘 UEFI 安装测试通过（2026-09-06）

在 PC 执行 `devenv shell -- just install-test-nuc` 可复现。使用锁定版本 disko 的
官方测试器和 NUC 分区配置，只连接 32 GiB 稀疏虚拟盘，不接入任何真实块设备。
测试完成分区、安装 systemd-boot、关闭安装虚拟机，再从虚拟磁盘经 OVMF UEFI 启动。
已断言 EFI 环境、ext4 根目录、vfat /boot、引导器安装和 16 GiB swap 均正确。
成功产物：`/nix/store/ykdn9c5vsf3l4cwq39qhcf9d7b9d3i7j-vm-test-run-disko-nuc-uefi-install`。

测试使用共享 Nix store 和 VM 专用覆盖，不代表真实 nixos-anywhere SSH/kexec 交接、
实机所有服务或业务恢复已验收。业务备份和隔离恢复已通过，真实安装仍缺临时 root
访问与明确的 NVMe 清盘授权；installation_enabled 继续为 false。未重启/格式化 NUC。
下方是分阶段记录，旧的“尚未构建/扫描/接有线/恢复演练”状态已被本节与下一节取代。
本文在冻结备份之后更新，不属于该快照。

## 硬件与启动检查更新（2026-09-06）

- 用户已回传恢复报告：文件/权限校验通过，两套 tag-all 各 13 表、Authelia 26 表，
  SQLite integrity_check 均为 ok。该检查未启动应用。
- 已在实际 NUC 执行固定版本官方 nixos-generate-config --show-hardware-config
  --no-filesystems，原始报告保存于 nixos/hosts/nuc/hardware-detected.nix 并接入
  hardware-configuration.nix。不带入旧 LUKS、swap 或文件系统声明。
- 最新 PC 完整构建产物：
  `/nix/store/m8m8klnpp3kjziwgij4jhpfpq0sn9arb-nixos-system-nuc-26.11.20260829.e8be781`。
- 虚拟机基本启动到登录界面，SSH 启动成功；首次 Home Manager 检查暴露 .config
  归属问题，NUC 配置增加显式用户所有的父目录；在测试机应用对应权限并修复测试用
  tmpfiles 配置所有者后，Home Manager 和 SSH 均 active。NUC 启动时不再联网自动
  更新可选 dsh/npm 工具，其他主机不变。
- VM 共享 Nix store 的 UID 映射为 65534，导致 logrotate 拒绝配置；SMART 服务也
  失败，真实硬盘检查仍待实机验证。未宣称虚拟机所有服务通过。
- 测试虚拟机使用临时磁盘、禁止外网；为诊断使用的临时 root 控制台登录设置只通过
  VM overlay 传入，未保存到 NUC 生产配置。测试机已请求关机。
- 此验证是直接启动内核的 VM 基本启动检查，不是 UEFI/disko/nixos-anywhere 安装链路测试。
  实机仍无 root 免交互权限；安装锁定仍保留，不能据此立即清盘。
- 安装计划不再自动重写已审查的硬件文件。最后需单独确认 NVMe 清盘，并安排恢复密钥、
  初次登录与现场救援；建议安装时拔开两块资料盘。

## 恢复演练入口（业务副本，不覆盖生产）

PC 已完成 nuc 系统闭包构建：
`/nix/store/wx8z6gzsavnjrln4kdfa46wnj7p24p6w-nixos-system-nuc-26.11.20260829.e8be781`。
这不是 VM/实机启动验收。NUC i915 显卡与 e1000e 有线驱动已只读核对；专属
hardware-configuration.nix 仍标记 provisional，尚未完成官方硬件扫描报告采集。

用户已提供精简业务备份成功输出，快照为 `20260906T062004.899909Z`。下一步执行：

```bash
ssh -t -o HostKeyAlias=nuc.local -o StrictHostKeyChecking=yes liou@192.168.1.4 'sudo python3 /home/liou/nuc-migration/nuc-restore-check.py --snapshot 20260906T062004.899909Z'
```

脚本读取 manifest 并要求业务快照复制/停写/校验均通过，再复制到备份盘私有
`restore-checks/<时间>/rootfs/`，不使用跨快照硬链接，不覆盖现有数据。
完整比较内容、UID/GID、权限、ACL/xattr 后，只在恢复副本上运行两套 tag-all 与
Authelia 的 SQLite integrity_check，并检查关键配置和凭据是否存在且非空，不打印其内容。
report.json 保留检查结果，install_ready 仍为 false；未启动应用，不代表端到端恢复已通过。
本说明是备份完成后的新文档，不宣称包含在此前冻结快照中。

## 当前入口：精简业务备份（取代下方整 home 方案）

用户已明确缩小范围。默认 scope 为 business，约 3.1 GiB 的 dufs/dufs-lan 加少量服务状态。
包括两套隐藏 tag-all 数据、Bevy/dist、Caddy 证书和配置、Authelia、DDNS、运行凭据、
部署目录、SSH、Syncthing 配置/证书/密钥和用户单元参考；不复制旧容器存储、整个 home、
整个 /etc、Codex、桌面状态、Syncthing 索引或 Whisper 模型。模型恢复时重新下载。
旧的大热备保留兜底；中断的备份不删除，也不能用于安装验收。

```bash
ssh -t -o HostKeyAlias=nuc.local -o StrictHostKeyChecking=yes liou@192.168.1.4 'sudo python3 /home/liou/nuc-migration/nuc-backup.py --scope business --final'
```

不要带 --previous。新建小副本，复制后做一次完整 checksum 校验，不扫描旧的大热备。
原 scope 如确需使用必须显式 --scope full。所有模式保留 root:0700、磁盘 UUID、停服务检查，
均不自动授予安装许可。小副本不代表其他个人文件已更新备份；它们只保留旧热备时点状态。
发布本说明后停止资料同步，避免最终校验期间继续改动 dufs/todos。

## 停机后的增量备份入口（2026-09-06）

业务容器、ttyd、Syncthing 和剪贴板同步已停止，桌面已注销。有线地址 192.168.1.4。
用户明确 NUC Codex 已不需要，最终备份排除 `/home/liou/.codex/***`，不阻塞其后台进程；
原热备保留这部分历史数据，不删除。其他业务/个人数据范围不变。

```bash
ssh -t -o HostKeyAlias=nuc.local -o StrictHostKeyChecking=yes liou@192.168.1.4 'sudo python3 /home/liou/nuc-migration/nuc-backup.py --final --previous 20260906T035744.999972Z'
```

新建时间戳目录，通过 checksum + link-dest 复用旧副本一致文件，不覆盖原热备，
不使用 inplace/delete。不要在备份完成后原地编辑任一快照，因为一致文件可能共享硬链接。
复制显示进度，前置 checksum 扫描和完整校验仍可能较慢；校验仅忽略明确的特殊文件跳过提示，
所有真实差异或未知诊断仍阻止验收。12 项安装/备份单元测试通过，实际最终副本尚待用户执行。
即使校验通过也不自动允许安装；仍须恢复演练。下方热备命令仅为此前阶段说明。

2026-09-06：用户已确认保留桌面、不保留系统盘加密。这里只准备迁移，不授权清盘。

## 已验证与阻塞

- `nixosConfigurations.nuc` 顶层 derivation 求值成功；安装防护 8 项测试通过。
  尚未完成完整构建、VM 安装测试或实机硬件报告采集，不等于安装验收。
- 仅格式化 Samsung 970 EVO 250GB，稳定路径 `/dev/disk/by-id/nvme-eui.0025385691b22dce`。
  新布局为 1G EFI、16G swap、剩余 ext4，无 LUKS。资料盘只按 UUID 挂载。
- 断电后 sda/sdb 已交换，不能把盘符当身份。project UUID 为
  `8bce6197-7281-40a0-84ec-e31c3d313877`，Art UUID 为 `5F82-B190`。
- 当前仍只有 Wi-Fi；eno1 没有 carrier。sudo 仍需密码，尚未执行完整备份。
- 安装器仍锁定禁用；`just install-check nuc` 和 `just install-plan nuc` 只检查/打印。

## 现在可以执行：交互式授权备份

脚本已放在 NUC `/home/liou/nuc-migration/nuc-backup.py`。用户在自己的终端执行：

```bash
ssh -t liou@nuc.local 'sudo python3 /home/liou/nuc-migration/nuc-backup.py --check'
ssh -t liou@nuc.local 'sudo python3 /home/liou/nuc-migration/nuc-backup.py --seed'
```

密码只在自己的终端输入，不发送给 AI。不必为备份开放 root SSH 或全局免密 sudo。
seed 不停生产，是热备，不算最终一致性备份；运行中变化可能使校验不一致。
备份位置为 `/media/liou/project/.nuc-migration-backups/<时间>/`，root 所有、0700。
不得改成 liou 可读或通过 DUFS 发布，否则可能泄露密钥和个人数据。

包含完整 `/home/liou`（含 dufs、dufs-lan、隐藏状态、模型、身份及容器存储），
另含 /etc、/root、/srv、/opt 和部分 /var 服务状态；排除用户 cache，不跨嵌套文件系统。
外置盘现有内容不重拷，也不格式化；磁盘上原有 nix-tools/secrets 要另核对其可恢复性。
每轮使用新目录，不删除之前备份。完整副本包含敏感数据，恢复前仍需检查 manifest 和 checksum。

## 安装前的维护窗口（尚未执行）

1. 接好有线，明确有线 IP，PC 用 `just install-check nuc --target liou@有线IP` 检查。
2. 准备现场显示器/键盘与救援介质；采集真实 NixOS 硬件报告，保留专属目录。
3. 在 PC 完成 nuc 系统构建及安装验证。安装期间的 root 权限单独安排：可在救援环境
   临时授权 PC 公钥；不要为了当前备份开放永久全局 NOPASSWD。
4. 用户同意停机后停止写入方：DUFS/tag 容器、ttyd、Syncthing、桌面会话及相关任务。
   检查 rootless/rootful 容器均停止。全 home/系统文件可能继续写入，最终副本优先离线制作；
   在线 --final 只有全量校验无变化才可接受，脚本不会自动停止生产。
5. 最终备份后做隔离恢复校验：文件内容、ACL/xattr、UID/GID、数据库完整性和必要密钥。
   `install_ready` 始终 false，必须人工验收，不能仅凭 rsync 返回成功安装。
6. 验收后才单独确认清盘；安装时建议断开两块资料盘。不得关闭稳定磁盘身份防护。

## 完整业务恢复顺序

1. 新系统先验证 SSH、有线、桌面；设置 liou 本地密码。UID/GID 均为 1000，
   subuid/subgid 为 100000:65536；不恢复旧 /etc/passwd、fstab、LUKS 或整个 /etc。
2. 接回资料盘，核验 UUID 和真实挂载；业务保持停止，不能让空挂载点启动容器。
3. 从最终副本恢复 `/home/liou/dufs`、`/home/liou/dufs-lan`，保留隐藏目录及权限。
   这包含两套 tag 数据、文件和 Bevy 产物。恢复模型、dufs-plus 凭据及状态、Caddy
   证书状态、Authelia/DDNS 状态。逐项按当前 Compose 挂载源核对，不凭容器名推断。
4. 选择性恢复 SSH/隧道、Syncthing 身份和用户资料。Home Manager 管理的路径先处理
   文件冲突；不整包覆盖新系统的 .config/systemd，也不直接搬旧 Podman 存储作为运行环境。
5. PC 发布器重传镜像；在 NUC 的 `/media/liou/project/me/nix-tools` 重新生成用户单元：
   `bash deploy/bootstrap/install-user-service.sh`。这一步只安装单元，不立即启动。
   NixOS 已声明资料盘挂载，不再运行旧脚本修改 /etc/fstab。
6. 恢复完数据/凭据、确认配置和挂载后启用 ttyd-compose、dufs-plus-compose；验证
   linger、Podman、Syncthing、autossh，以及此次盘点发现的 clipboard-sync 是否需恢复。
   不把 Pop!_OS 桌面专属服务照搬到 NixOS。
7. 验收 NUC 认证读写、密码只读两个入口、tag 数据和同步、Bevy 应用、终端、代理证书、
   隧道与重启自启。阿里云保持现状，确认 NUC 恢复没有改变其匿名只读站。

实际停机/恢复命令须根据最终 manifest、当前服务与挂载清单生成；本页不是已恢复声明。
跨工程进度仍以 NUC todos 三份文件为准。
