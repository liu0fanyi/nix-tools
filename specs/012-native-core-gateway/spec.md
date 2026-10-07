# 012 — 原生核心的同源认证文件入口

## 范围

在两个独立 loopback TCP 端口和私有 Unix 文件 socket组合 Caddy、原生 core 与 DUFS；保持 /tag-api 和静态/文件入口。Home Manager 默认停用，不 import 到当前配置，不激活 PC/NUC。

## 固定验收边界

1. 同源根入口与 /tag-api 通过真实原生服务。
2. 匿名与错误凭证拒绝；已登录可以受控操作自己的临时文件/标签；不给页面任意指定 API 的能力。
3. 核心缺媒体能力反馈准确，原文件仍能读取；已通过的窗口/节点隔离保留。
4. 实际结果、限制、提交推送与所属固定 todos 镜像收尾。

本规格属于 tag-all 024 T004 的配套关卡；真实 PC 迁移、生产同步/配对、全部工具容器与其他平台不在本步。

## 结果与复验

实际原生核心 + Caddy + DUFS Unix socket 通过：匿名/错误凭证及匿名写入拒绝、认证标签/文本/上传/列表/原文件/流读取、私有应用入口拒绝，合成 PDF 未改变，自有进程/目录已清理。Home Manager 启用/停用求值、全部断言、依赖关系与特殊字符参数转义通过；模块未激活。

在 nix-tools 的 devenv shell 中执行 `just check-native-workspace /data/project/tag-all /data/project/dufs-plus /data/project/tag-browser`。需既有 core 原生 gate 报告、dufs-plus dist、Playwright 的 NODE_PATH 和实际 CHROMIUM_PATH；无 API/静态 HTTP mock。模块复验见 nix-tools 的 tests/native-workspace-module.nix。生产安装、实际开机和迁移/回退属于 tag-all 024 T005。

## 组合安装与迁移状态

安装 generation 已实际构建；自有合成数据完成完整版 → SQLite/元数据离线快照 → 原生核心 → 完整版二进制回退，回退后保留原生新增标签；单独演示旧备份恢复到新目录。凭证/身份仅不透明夹具，真实签名与任务执行未测试。
真实 PC 预检拒绝切换：原生试验关闭配对/同步/发现且不保持 loc_pc/容器嵌套挂载。现用容器、数据和配置未改变。剩余关卡见 tasks T005d/e；结果文件记录 activated=false 与 cutover_ready=false。

合成迁移另验证明确位置 ID、网页收藏与文件标签均保留；该结果不替代现网同步/容器路径转换的验收。

显式 configured 配置透传与运行期认证文件路径已实现；默认 isolated 保持。两种安装产物
构建通过，产品真实双节点配对/CA/签名/重启证据见 [peer-results.json](peer-results.json)。
该证据使用 Python TLS 夹具；实际 Caddy 与目录映射的后续结果见下方。真实发现/现用配置适配仍未完成，不能切换现网。

目录映射/生命周期验收见 [stack-runtime-results.json](stack-runtime-results.json)：
使用实际生成单元，在自有临时状态验证映射读写、三项崩溃恢复、整套停止再启动和清理。
不改变宿主工作区目录；未触碰生产服务。配置入口仍默认停用，实际开机/切换未验。

## 私人节点通信入口

HTTPS 入口默认停用，显式指定 DNS 名、IPv4 监听、允许网段及私有运行期 TLS 文件；
只开放既有配对握手、签名同步和受控代理路径，其余路径 404。
网页管理走已认证的本机入口，管理员环境在运行期读取，覆盖来自网页的管理员头，
不会把管理员权限注入节点通信入口，也不将密钥或令牌复制到 Nix store。
真实双节点及候选/申请/同意验收见 [peer-gateway-results.json](peer-gateway-results.json)。
候选来源为自有临时文件，此结果不代替局域网广播发现、真实开机或现网迁移。
