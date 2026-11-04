# ed2k 下载（aMule）

Linux 工作站 liu-bigpc 使用仓库锁定的 aMule 3.0.1，菜单入口为 aMule，
`ed2k://` 默认交给它处理。Nix 首次激活只初始化缺失的可写文件，
后续保留应用内修改、Kad 联系人与下载任务。

应用配置后运行 `amule`，首次信息提示点“确定”。在“网络”页底部的
ED2K 链接输入栏粘贴每行一条的链接并添加。
已整理的个人下载链接不放进本仓库或发布摘要，也不自动加入下载队列。

## 网络与源

- 同时启用 eD2k 和 Kad；前者通过服务器发现源，后者通过分布式网络发现源。
- 服务器列表启动时更新：`https://upd.emule-security.org/server.met`。
- Kad 首次引导：`https://upd.emule-security.org/nodes.dat`，连接后自动维护联系人。
- “网络 → Kad”中可用上述地址重新引导；服务器列表可在“网络”中手动更新。
- 初始17个服务器、177个Kad联系人只是网络入口，不代表任何文件的可用源数量。
- 上传初始上限1024 KiB/s、下载不限速；实际带宽可在偏好设置中调整。
- mihomo 规则模式将 `amule` 和 `.amule-wrapped` 直连；保持应用自身代理关闭。

源地址来自 [aMule 官方入门](https://amule-org.github.io/docs/quickstart-guide)，
且已核对3.0.1源码默认值。引导原件及SHA256留在 `ref/amule-bootstrap/`。

## 存储与连接状态

完成目录为 `/data/Downloads/aMule/Incoming`，临时目录为
`/data/Downloads/aMule/Temp`；剩余空间小于10 GiB时暂停下载。
只共享aMule专用目录及其下载内容，不添加其他个人目录。
EC外部控制与Web服务保持关闭。

PC防火墙声明放行TCP 4662、UDP 4665/4672；UPnP已启用。
应用配置后如果仍是Low ID或Kad有防火墙，需要检查路由器：
将上述端口转发至PC `192.168.1.100`，并确认WAN是否有可入站的公网IPv4。
运营商NAT或双层NAT需要处理上级网关；加服务器无法解决入站连接问题。
Low ID仍可连接部分源，但两个受限客户端之间可能无法直接传输。
参考 [aMule 防火墙说明](https://wiki.amule.org/wiki/Firewall)。

2026-11-04隔离空任务实测：服务器列表HTTPS更新成功，读取177个Kad联系人，
eD2k与Kad均连接；eD2k为Low ID，Kad为有防火墙；UPnP报告未发现WAN服务。
该实测发生于新防火墙规则尚未应用时，不能据此断定运营商NAT。
运行时mihomo配置已备份、通过 `mihomo -t`，controller热加载后查询确认
aMule两条DIRECT规则及原qBittorrent直连规则存在；未重启代理服务。

同日用户手动应用并打开后，真实主窗口、TCP4662及UDP4665/4672监听确认；
防火墙含上述端口的重载脚本已成功执行。eD2k/Kad均连接，5条活动连接
全部使用DIRECT，但仍显示Low ID/Kad有防火墙，UPnP未发现WAN服务。
下一步检查路由器映射及WAN公网IPv4；当前未确认公网入站可达。

后续路由器排查：网关 `192.168.1.1` 的MERCURY YR1900G确实已开启UPnP，
通过 `http://192.168.1.1:1900/igd.xml` 可读设备描述，并可调用WANIPConnection。
WAN IPv4与用户页面、国内直连出口查询一致，未发现上级NAT证据。
广播发现无响应不代表服务未开启。只读枚举确认UPnP已有64条映射，
三个aMule端口均无条目；尝试新增第一条时网关返回
`501: Port mapping table id full !`，未创建任何映射，也未删除现有条目。
本机已有的3条MiniTP SDK映射不属于aMule，不擅自删除。
公网服务器仅进行TCP4662连接测试，结果超时；未传输文件或更改公网服务。

用户通过主路由器“高级设置 → 高级用户 → 虚拟服务器”添加以下规则并启用，
再复测公网连接及aMule状态；若设备也拒绝手动规则，需要另行确认后处理映射容量。

| 协议 | 外部端口 | 内部端口 | 内部IP |
| --- | --- | --- | --- |
| TCP | 4662 | 4662 | 192.168.1.100 |
| UDP | 4665 | 4665 | 192.168.1.100 |
| UDP | 4672 | 4672 | 192.168.1.100 |

中间设备若确为桥接/AP，无需在它上面再配置NAT映射；若其实是路由模式，
则需另行检查其WAN与LAN地址，不能仅凭“桥接”称呼推断拓扑。
设置入口参考 [水星官方说明](https://service.mercurycom.com.cn/article-1097.html)。

## 应用配置

完整系统与Home Manager候选已构建验证；Agent不执行系统switch。
用户在普通终端手动执行：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```

从菜单打开aMule，检查底部eD2k/Kad状态，再按需要添加链接。
没有用户共享完整文件时，更新引导或连接服务器不能保证下载完成。
