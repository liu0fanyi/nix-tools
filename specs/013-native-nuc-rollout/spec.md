# NUC 原生部署与入口保留

产品能力权威规格：/data/project/tag-all/specs/025-native-nuc-rollout/。
本仓负责 NUC 拓扑预检、固定制品传输、离线双区快照、用户单元注册、生产激活和保留新写入的回退。
用户已授权继续 NUC；不得执行 NUC NixOS switch，不触碰 Aliyun，不从服务器构建。
五个应用容器替换为原生服务，四个入口服务保留：Caddy、Authelia、只读网关、DDNS。
必须保持现有认证/公网/终端路由、只读 OS 挂载和方法拦截，保留 CA/身份/模型/Git 专用凭证。
秘密不入 store、Git 或日志；预检结果只输出固定路径、挂载写权限和镜像摘要。

## 当前验收状态

NUC原生迁移六项已完成，剩余0项；自动验收证据见 [live-results.json](live-results.json)。
用户确认公网文件、标签正常显示，标签筛选正常。该人工验收覆盖显示与筛选，未声明公网写操作已测。
八原生单元正常、开机配置已核对；未实际重启整台NUC，后续正常使用中观察。

## 构建来源与下一阶段

原生应用由PC的Nix包装交付；当前四类worker共享固定Alpine/Containerfile工具镜像，
存入Nix store仅用于固定分发，不代表dockerTools构建。四个保留入口容器未改构建来源。
历史023曾部署完整Nix后端，但已被原生API替换；当前工具镜像不能由旧部署状态推断。
下一优先产品方案为 `/data/project/tag-all/specs/027-application-entry-boundary/`，固定E1–E5共5项，配套装配归 [014](../014-application-entry-boundary/spec.md)；
随后是 `/data/project/tag-all/specs/026-nix-processing-images/`，固定F1–F5共5项。
基础设施只负责将来明确的原生工具更新/回退，不调用被原生模式守卫禁止的旧容器发布流程。
本013仍6/6完成，剩余0；本次只整理规格，无生产配置或制品变更。

027旨在tag-all承担本地应用入口，Caddy保留公网代理/TLS/Authelia接入和其他站点；私人节点TLS辅助单独核对，不随网页入口移除。基础设施配套契约现已登记014，按027实施，不取消既有认证边界。
