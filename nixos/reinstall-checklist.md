# homebox NixOS 重装与验收清单

目标机：`192.168.1.6`。标准 nixos-anywhere 的 kexec 流程不支持 Wi-Fi，
重装期间应使用有线网络，并保持电源连接、不要让机器睡眠或合盖。
官方说明见：<https://github.com/nix-community/nixos-anywhere#prerequisites>。

## 重装前：只读准备

- [ ] 重要数据、`deploy/` 运行时数据、mihomo 订阅信息和 Rime 词库已有备份。
- [ ] 本机已解锁 git-crypt；`secrets/rime/luna_pinyin.userdb.tar.gz` 已存在。
- [ ] `nixos/configuration.nix` 中 root/liou 的 SSH 公钥仍与本机用于连接目标的公钥一致；重装后 SSH 访问依赖这份公钥。
- [ ] 目标机接入网线，并确认有线网卡获得 IPv4 地址。
- [ ] 目标机当前从 UEFI 启动，且 `/sys/firmware/efi/efivars` 可写；脚本会自动检查这一点，BIOS 机器不能直接复用当前 flake。
- [ ] 如果有线地址不是 `192.168.1.6`，使用它作为目标地址，例如：

  ```bash
  NIXOS_ANYWHERE_TARGET=root@192.168.1.23 \
    bash scripts/check-nixos-anywhere-network.sh
  ```

- [ ] 本地配置检查通过：

  ```bash
  nix flake check --no-build --show-trace
  bash scripts/install-nixos-anywhere.sh --check
  nix build .#nixosConfigurations.homebox-install.config.system.build.diskoScript --no-link
  ```

- [ ] 安装脚本默认会自动探测本机 Clash Verge/mihomo 的 `127.0.0.1:7897`，并追加清华 Nix substituter；默认由本机直接向目标推送闭包。如果本机没有代理，会自动回退直连：

  ```bash
  NIXOS_ANYWHERE_PROXY_MODE=off bash scripts/install-nixos-anywhere.sh --check
  ```

  只有在目标网络稳定、确实希望目标自行从 cache 下载时，才设置
  `NIXOS_ANYWHERE_USE_DESTINATION_SUBSTITUTERS=1`。

- [ ] kexec 镜像默认由本机代理下载并缓存，再上传给目标机；首次运行会额外下载约 418 MiB，后续复用
  `~/.cache/nixos-anywhere/nixos-kexec-installer-noninteractive-x86_64-linux.tar.gz`。可用
  `NIXOS_ANYWHERE_KEXEC_PATH=/path/to/image.tar.gz` 指定已有镜像，或用
  `NIXOS_ANYWHERE_KEXEC_CACHE_DIR=/path/to/cache` 修改缓存目录。只有目标机能直连 GitHub 时才设置
  `NIXOS_ANYWHERE_KEXEC_MODE=remote`。

- [ ] 如果 Clash Verge 的端口或本机地址变化，在重装前从外部传入两个代理 URL；本机 URL 和目标机可达的 LAN URL 可以使用不同端口：

  ```bash
  NIXOS_ANYWHERE_TARGET=root@192.168.1.23 \
  NIXOS_ANYWHERE_PROXY_URL=http://127.0.0.1:8890 \
  NIXOS_ANYWHERE_REMOTE_PROXY_URL=http://192.168.1.3:8890 \
    bash scripts/install-nixos-anywhere.sh --check
  ```

  未设置 `NIXOS_ANYWHERE_REMOTE_PROXY_URL` 时，脚本会自动推导本机 LAN 地址；`--check` 会测试目标机是否能通过它访问 cache。必须依赖该代理时，加上 `NIXOS_ANYWHERE_REMOTE_PROXY_CHECK=required`。

- [ ] 目标地址也可以使用 `NIXOS_ANYWHERE_TARGET=root@<有线IP>`，或分别使用
  `NIXOS_ANYWHERE_SSH_USER` 与 `NIXOS_ANYWHERE_SSH_HOST`；当前安装配置需要 root 权限。
- [ ] Wi-Fi 密码和 NetworkManager connection 不在仓库中；重装期间仍必须使用网线，首次进入桌面后再用 `Mod+N`/`nmtui` 配置 Wi-Fi。

- [ ] `~/.config/secrets/nix-tools-git-crypt.key` 和已解锁的
  `secrets/mihomo-config.yaml` 已准备好。首次设置可运行
  `bash scripts/init-secret-vault.sh`，在其他机器上运行
  `bash scripts/export-git-crypt-key.sh`。默认 `NIXOS_ANYWHERE_RESTORE_SECRETS=required`
  会在清盘前检查它们；如果确实只要基础系统，才显式设置
  `NIXOS_ANYWHERE_RESTORE_SECRETS=off`。

- [ ] 确认磁盘会被清空；安装配置为：EFI 500M、按内存选择的独立 16/24/32/64G swap LV、其余空间为 root LV。
- [ ] 自动档位当前仅适用于 x86_64、唯一内部磁盘 `/dev/sda` 和可写 UEFI；NVMe、ARM、BIOS 或多磁盘电脑必须先准备单独的 flake/disko 配置，脚本会拒绝自动清盘。

## 执行重装

```bash
NIXOS_ANYWHERE_TARGET=root@<有线IP> bash scripts/install-nixos-anywhere.sh
```

脚本会先做有线网络检查，再要求输入 `REINSTALL`。`--yes` 只适合已经人工确认过备份和目标地址的情况。
`nixos-anywhere` 生成的 machine-specific hardware 报告只用于本次构建，脚本退出时会恢复工作区中的通用占位文件，不会把目标硬件信息留在提交里。

## 重装后：自动验收

首次启动并确认 SSH 恢复后运行：

```bash
NIXOS_VERIFY_TARGET=root@<有线IP> \
  bash scripts/verify-homebox.sh --profile reinstalled
```

检查内容包括：NixOS generation、网络路由、关键 systemd 服务、根分区和 `/boot`、swap/resume、合盖策略、Waybar、Niri、Helix、Rime 文件以及 mihomo 的配置、服务、TUN、7897 mixed-port、9090 clashtui controller 和代理出站 smoke test。

`install-nixos-anywhere.sh` 在 NixOS 切换成功后会自动调用
`scripts/restore-secrets.sh`，它会先通过本机代理缓存并上传 mihomo GeoData，再恢复 mihomo/clashtui、Rime userdb 和 npm 工具；安装脚本会等待重启后的 SSH 恢复，因此正常流程不再需要手动补这一步。若之前使用了
`NIXOS_ANYWHERE_RESTORE_SECRETS=off`，再手动运行：

```bash
bash scripts/restore-secrets.sh root@<有线IP>
NIXOS_VERIFY_TARGET=root@<有线IP> \
  bash scripts/verify-homebox.sh --profile reinstalled --strict
```

## 必须在目标机本地手动确认

- [ ] greetd/niri 能正常登录，内置屏幕和外接显示器正常。
- [ ] 用快捷键切换到 Rime，能显示中文候选词并实际输入；SSH 远程脚本无法可靠模拟图形输入法会话。
- [ ] Waybar 能显示温度、风扇转速；播放音乐/视频时 MPRIS 正常。
- [ ] 合盖后先 suspend，打开盖子能恢复；再在本地执行一次真实 hibernate 并确认恢复。
- [ ] mihomo 的代理出站 smoke test 通过后，再分别确认国内站点直连、国外站点代理，以及局域网地址不被代理。

不要从 SSH 会话直接执行真实 hibernate，否则连接中断是预期现象。
