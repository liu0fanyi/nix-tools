# PC 原生服务切换预演

**当前不可执行切换**：S2 的完整系统构建仍未通过，S3 功能兼容尚未验收。
以下是待审核的操作顺序，不是现在让用户停服务的指令。Agent 不执行 switch。

## 已准备的产物

- `nixos/modules/native-pc-candidate.nix`：明确的 PC 候选模块工厂。只由预演入口导入，不改现用配置。
- `tests/native-pc-host.nix`：扩展实际 `/home/liou/nix-tools` 的 liu-bigpc 配置；同时构建系统和 Home Manager。
- `scripts/native-pc-cutover.py`：默认仅显示计划；显式 `--prepare-offline` 是用户切换阶段的离线准备入口。
- 私有新状态固定为 `/home/liou/.local/share/tag-all/pc-native/`，旧状态不覆盖。

## 构建核对

在本机 nix-tools 源码中，以实际路径传给 `tests/native-pc-host.nix`。分别构建 `.toplevel`
和 `.home`，核对主机为 liu-bigpc，记录完整产物路径及配置来源。
不得只凭 Home Manager 成功就让用户切换系统。当前完整构建被既有 Tag Browser
fetchClosure 的依赖缓存读取阻塞；已单独核对本机依赖存在，缓存 HTTP 请求返回403，
不能以换掉浏览器包或绕过真实系统依赖来宣称构建通过。

## 所有切换前关卡通过后的用户操作顺序

1. 保存编辑内容，固定通过构建的系统/HM产物、原系统产物和五个源容器镜像；核对 S1–S3 均通过。
2. 停止 `pc-private-node-restore.service` 和固定 dufs-plus-pc 的五个容器。只操作这些实例，不删除容器/卷。
3. 用户运行 `TAG_PODMAN_URL=unix:///run/user/1000/podman/podman.sock python3 scripts/native-pc-cutover.py --prepare-offline`。
   脚本在状态访问前、发布快照前都复查五个容器停止和旧恢复单元 inactive；任何不符拒绝。
4. 检查新目录完整性与私有权限。SQLite 使用只读源 backup API，保留 metadata 和其他状态；
   CA/认证离线复制，路径转换并 TOML roundtrip 核验。全部成功才发布 ready 标记；已有目标绝不覆盖。
5. 用户按最终交付的、与固定候选产物匹配的系统切换命令激活。该命令须在 S2/S3 通过后交付，本文不提供未验收的 switch 命令。
6. 验证 5006 认证入口、loc_pc、签名同步与发现，再进行登录/开机和浏览器验收（T005e）。

候选服务要求 ready 且无 container-mode；旧容器恢复单元不挂 default.target，且只有
container-mode 时才允许运行。不能仅激活配置就生成一份空数据库替代原数据。
新旧网关不共享在线可写 CA 存储，原始数据和原始 CA 留作备份。

## 回退边界

- 激活前失败：源容器仍存在，未覆盖源 DB；可以恢复旧配置/源实例，不能删除已有备份。
- 原生开始写入后：先停完整原生 target，确认三个子单元均停止，再选择容器回退模式。
- `pc-native/config/container-rollback.json` 是 Compose 合并配置，固定原镜像、把源核心和发现
  容器的数据挂载切到 **新** `pc-native/data`，数据库改为 `/data/core.db`；网关改用复制的 CA 存储。
  与现有 `/data/project/tag-all/deploy/pc/compose.pc.yaml` 合并后先只读核对最终配置，再重建固定 PC 服务。
- 不直接启动仍指向旧 pc.db 的旧后端，否则原生期间的新写入不会出现在旧节点。
- 容器回退可继续使用新数据，不自动回写原源 DB。真要恢复旧备份，必须用户明确选择，且恢复到全新目录。
- container-mode 与 ready 的操作、最终用户切换命令、Compose 合并预演仍须随 S2 最终产物审查；本轮未执行。
