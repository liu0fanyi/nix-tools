# 主机角色与安装入口

PC 是源码与构建权威源，NUC 运行私有服务，阿里云运行公开只读服务。NixOS 主机分别维护 hosts 配置和真实硬件报告，standalone Home Manager 不承担系统安装。

安装前核对目标主机、稳定磁盘 ID、型号/序列号、容量、UEFI、网络、权限、异盘恢复演练及现场救援条件。资料盘排除清盘配置，不以自动 /dev/sda 或另一台主机 profile 代替身份。

历史 Pop!_OS 审查快照不代表 NUC 当前系统；现行规格见 [基础设施](../../specs/009-infrastructure/spec.md)与[主机配置](../../specs/010-host-configuration/spec.md)。构建、预演、VM、安装、数据恢复、真实重启验收是不同阶段。
