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
该证据使用 Python TLS 夹具，实际 Caddy 配对入口、发现/路径适配仍未完成，不能切换现网。
