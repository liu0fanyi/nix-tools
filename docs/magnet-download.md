# 磁力与 BT 下载

liu-bigpc 通过 Home Manager 安装 qBittorrent，关联 `magnet:` 链接和 `.torrent` 文件。
打开 qBittorrent，按 `Ctrl+Shift+O` 粘贴磁力链接；也可在浏览器直接点击磁力链接。

首次激活生成可编辑的配置，启用 DHT、PeX、LSD 与原生 Tracker 列表订阅。
订阅使用 XIU2 精选列表的国内访问镜像：

```text
https://jsd.onmicrosoft.cn/gh/XIU2/TrackersListCollection/best.txt
```

备用地址：`https://cdn.jsdmirror.com/gh/XIU2/TrackersListCollection/best.txt`
和 `https://cf.trackerslist.com/best.txt`。
镜像是列表获取入口，Tracker 本身分布在不同国家，不保证每个节点在国内均可连接。
列表帮助发现做种者；没有做种者的资源不能靠添加 Tracker 恢复下载。
上游说明：https://github.com/XIU2/TrackersListCollection/blob/master/README-ZH.md

在「工具 → 选项 → BitTorrent」查看或修改自动添加 Tracker 的 URL，应用后重启。
配置文件为 `~/.config/qBittorrent/qBittorrent.conf`，后续系统切换保留应用内修改。
已有配置时不会覆盖，需在上述界面手动启用订阅。

## Clash / mihomo 直连

本机启用 TUN，但使用 `rule` 规则模式。`secrets/mihomo-config.yaml` 的规则最前面
将 `qbittorrent`、Nix 包装后的 `.qbittorrent-wrapped` 和 `qbittorrent-nox` 指向
`DIRECT`，并使用 `find-process-mode: always` 识别进程。下载连接、DHT 与 Tracker
请求都按进程直连；qBittorrent 的「连接 → 代理服务器」应保持不使用代理。
已建立的连接需重连后才采用新规则。

保持 Clash 的「规则模式」；「全局模式」会跳过进程直连规则。
其他软件继续遵循原有国内直连、国外代理规则。TUN 仍负责接管流量，
`DIRECT` 表示由 mihomo 直接出站，并非完全绕过 TUN 或其 DNS。

安装配置由仓库维护；Agent 完成只读构建验证后，用户在普通终端执行：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```
