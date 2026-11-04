# aMule 首次启动引导文件

2026-11-04 下载的网络引导快照，仅在首次安装且目标文件不存在时复制。
原始二进制按下载内容保留，不包含本机身份、文件清单或下载任务。

| 原件 | 来源 | SHA256 |
| --- | --- | --- |
| server.met | https://upd.emule-security.org/server.met | 72babbd5cc1abd6d2492e825daad7f875026e3d3ce6d4526e5bbfa3fc3639961 |
| nodes.dat | https://upd.emule-security.org/nodes.dat | 03fbc963d0aec7e5a6580c77b04e120417f5ee1aad6e3c4785085e55c1b219a7 |

来源由 [aMule 官方快速入门](https://amule-org.github.io/docs/quickstart-guide)
及仓库锁定的 aMule 3.0.1 `Preferences.cpp` 默认值确认。
初始服务器17条、Kad节点177个；它们是引导联系人，不是文件可用源数量。
服务器启动时从上述HTTPS地址更新；Kad连接后自行维护运行目录中的节点列表。
若后续离线过久，可在“网络 → Kad”中从上述 nodes.dat URL 重新引导，
不将旧快照覆盖到已有运行状态。
