# NUC SIP 实验防火墙

状态：用户明确授权并要求只修改防火墙；已经应用，防火墙阶段验收完成。未应用整套更新候选，内核、软件及用户环境保持原样。

## 范围与声明

仅允许测试板 `192.168.1.88/32` 从 `wlp0s20f3` 访问 NUC `192.168.1.12/32` 的 TCP 15090、UDP 18000–18101。长期声明位于 `nixos/hosts/nuc/default.nix`，与共享 `nixos/configuration.nix` 一起加载。工作站 `.100` 的规则仍保留，不能替代 NUC 规则。规则不设超时，不需要每轮测试 rerun；地址、网卡或端口变化时重新核对。

## 本次仅防火墙应用

NUC 历史部署 checkout 不含当前 NUC 主机模块，不能直接在那里 rerun。原系统仍为 `26.11.20260829.e8be781`；不得用本机最新配置替代它而带入软件升级。原配置可从提交 `950042fe0c9d95c51dd3e3e30cd315168a9888e3` 恢复，未修改时生成的 firewall-start 与现网完全一致。只在该配置加入上述两条规则即可单独生成新脚本，不求值无法恢复的旧桌面安装包。

在PC使用 Nixpkgs 自带 `replaceDependencies`，通过 `nixos/hosts/nuc/firewall-only.nix` 将新脚本纳入现有系统闭包，保留其它依赖；这是一条保持现网软件不变的受限应用路径，不替代以后经授权的完整系统重建。调用方必须核对 baseSystem 等于实时系统代、旧脚本身份及实际脚本差异，并审查最终闭包，不能静默用于其它更新。

- 原系统：`/nix/store/z2vw0406ajw7kznnhcm5hcnwp0adpzba-nixos-system-nuc-26.11.20260829.e8be781`。
- 已应用系统：`/nix/store/bdlrfkdjwap81gi9rf97gwksqdpffxm5-nixos-system-nuc-26.11.20260829.e8be781`。
- 原脚本：`/nix/store/v5k3hjw9hbsq1sbxqhq2jxyzcqfczx90-firewall-start`，脚本SHA256 `cb6c668b3b695a2326f7ff414bce1c156ea5474f359e5e7a01e2147613e0da68`。
- 新脚本：`/nix/store/4q77z6qpvih31wxglnplzdii14aqanil-firewall-start`，脚本SHA256 `8c54e170b51b676724fa50324580515107fc116743a7153f6d7012ad89a498ac`。

结构复审：13行无状态Nix配方，仅封装官方依赖替换；不增加守护进程、手写运行时规则、第三方依赖或产品接口。实际变更仅 firewall-start、firewall-reload、对应服务单元、system-units、etc及系统代引用；2041个其它路径完全一致，六个变更包719项内容在规范化引用后逐字一致，唯一功能差异为两条规则。

## 激活与核验

PC构建后仅传输六个配置包。NUC预演仅需 reload firewall.service；随后更新system profile并switch，保留旧系统代和五分钟失败回退。实际切换成功，新SSH连接正常；再次reload后两条规则仍存在，firewall/sshd active，无failed系统服务，原四个容器保持运行时长，5006/5008匿名HTTP均401。内核仍6.18.48，system-path及用户.bashrc来源不变。默认开机项已指向新系统init；未执行整机重启。核验后停止本轮回退计时器。

旧系统代保留供回退：将system profile设回上述原系统，再执行原系统的 `bin/switch-to-configuration switch`。正式撤销规则时同时移除权威Nix声明，不能仅用临时iptables删除替代声明回退。上一轮为整套更新提交的安装包输入修改已撤回，用户原有工作文件及暂存内容保持。

这里只验收主机防火墙，不宣称PBX已监听或板端LAN通话通过。产品唯一后续计划仍为 `/data/project/xiaoqiang/esp32-p4-sip/specs/010-rtp-adf-codec/` 的 T105-B2f2：LAN源/采集恢复接口、短测与1800秒验收。
