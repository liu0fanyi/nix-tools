# NUC 备份与恢复手册

需求与边界见 [基础设施规格](../../specs/009-infrastructure/spec.md)。本页不代表当前停机、安装或恢复授权；每次以实际主机身份、磁盘 UUID 和 manifest 生成命令。

## 备份与演练

- business 备份包含 dufs/dufs-lan 隐藏状态、静态产物、凭据、服务状态、SSH/Syncthing 身份；不等于整个 home 或所有模型都已备份。
- 先盘点、再停写取得最终一致性副本，保留原副本，checksum 无差异后才做隔离恢复演练；热备不能自动作为清盘许可。
- 私有备份位于 project 盘 .nuc-migration-backups，root 所有且 0700，不通过 DUFS 发布。密码在用户自己的终端输入。
- nuc-backup.py 的 --check 只检查，--scope business --final 用于已确认停写后的新快照；full 模式必须显式指定。实际远端脚本位置与参数应先核对 --help。
- nuc-restore-check.py --snapshot <id> 复制到独立 restore-checks 目录，核对内容、UID/GID、权限、ACL/xattr，并在副本做 SQLite integrity_check；install_ready=false 不能被绕过。
- link-dest 快照可能共享硬链接，不得原地编辑旧快照。安装前另行核验真实硬件、稳定磁盘 ID、文件系统尺寸和救援方案。

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
进度以本仓库 specs 为准。
