# PC 原生服务切换与回退

**当前不可执行生产切换：S2 已通过，S3 文件/媒体兼容尚未通过。**
本文给出通过所有关卡后由用户执行的顺序。Agent 不执行 switch、离线生产迁移或停止现用容器。

## 固定入口与产物

- `tests/native-pc-host.nix` 扩展实际 `/home/liou/nix-tools` 的 liu-bigpc 配置。
- `nixos/modules/native-pc-candidate.nix` 仅由候选入口导入；默认主机配置不启用原生服务。
- 系统与 Home Manager 精确路径以 [宿主预演报告](../specs/012-native-core-gateway/host-preflight-results.json) 为准。
  本机 `.devenv/native-pc-final-system`、`.devenv/native-pc-final-home` 是自有 GC 根，不是活动系统 profile。
- 状态固定为 `/home/liou/.local/share/tag-all/pc-native/`；源 `pc/` 保留，绝不自动回写或覆盖。
- 构建包含主仓已有未提交主机配置；固定产物通过不等于把这些无关修改提交了。
  主机配置、产品模块或前端变动后须重新构建完整候选和 HM，并更新报告再交付。

本阶段是固定候选的试用切换。普通 `rerun.nu liou --host liu-bigpc` 使用默认主机配置，
会撤掉候选模块；原生试用期间升级系统须重新构建本候选入口，不能把普通 rerun 当成候选升级。

## 已验证的保护

- `ready` 必须来自完整离线快照，数据库、状态目录及原 CA 根/中间证书与密钥必须为当前用户所有、私有、非 symlink。缺失 CA 拒绝启动，避免生成不同身份。
- 原生 target 和三个服务要求 ready 且无 `container-mode`。三个实际服务的 ExecCondition
  通过本机 Podman socket 确认固定五个容器均已停止；API 不可读也拒绝启动。
- 候选的 `pc-private-node-restore` 只在 ready 与 container-mode 同时存在时参与默认启动。
  其 ExecCondition 核对四个原生单元停止、五个容器身份及固定镜像、新数据库/CA/证书/工作区挂载。
  ExecStart 只启动以下五个固定名称；不再按项目标签批量启动可能指向旧状态的容器。
- 回退 overlay 使用新 `data/core.db`、新 metadata、复制的 CA/信任证书与认证环境，分别固定五个源镜像；核心与发现镜像不要求相同。
- 合成 [回退合并报告](../specs/012-native-core-gateway/rollback-merge-results.json)、
  [实际 ExecCondition 报告](../specs/012-native-core-gateway/mode-guard-results.json)
  已通过。生成单元的拒绝分支实际没有执行启动命令；没有运行生产停止/创建/启动命令。

## 所有切换前关卡通过后的用户顺序

以下 shell 示例仅用于交付审查，**S3 未通过时不执行**。在 `/home/liou/nix-tools` 使用 Bash。

1. 保存编辑内容，核对 S1–S3 全部通过，固定报告中的候选系统/HM和源镜像。
   先记录运行系统与当前 system profile 的路径，保留它们的 GC 根；不要删除任何源备份。
2. 停止旧恢复单元，再停止固定五个容器：

   ```bash
   systemctl --user stop pc-private-node-restore.service
   podman --remote --url unix:///run/user/1000/podman/podman.sock stop \
     dufs-plus-pc_caddy_1 dufs-plus-pc_peer-gateway_1 \
     dufs-plus-pc_peer-discovery_1 dufs-plus-pc_tag-server_1 dufs-plus-pc_dufs_1
   ```

3. 用户执行离线准备：

   ```bash
   TAG_PODMAN_URL=unix:///run/user/1000/podman/podman.sock \
     python3 scripts/native-pc-cutover.py --prepare-offline
   ```

   在数据访问前和快照发布前均复查源已停止。SQLite backup/完整性、metadata、额外状态、
   CA/认证、配置往返和权限都成功才原子发布 ready。已存在的目标绝不覆盖。
   准备失败且原生从未写入时，仍可启动原来容器；源 DB/CA 未被覆盖。
4. 检查快照和原生启动守卫：

   ```bash
   python3 scripts/native_pc_mode_guard.py --mode native
   ```

   在新私有目录记录原系统并保留 GC 根；从报告读取已验证候选：

   ```bash
   native_state=/home/liou/.local/share/tag-all/pc-native
   system_before=$(readlink -f /run/current-system)
   profile_before=$(readlink -f /nix/var/nix/profiles/system)
   umask 077
   printf '%s\n' "$system_before" > "$native_state/config/system-before-cutover"
   printf '%s\n' "$profile_before" > "$native_state/config/profile-before-cutover"
   nix-store --add-root "$native_state/config/system-before-gc-root" --indirect --realise "$system_before"
   nix-store --add-root "$native_state/config/profile-before-gc-root" --indirect --realise "$profile_before"
   candidate_system=$(python3 -c 'import json; print(json.load(open("specs/012-native-core-gateway/host-preflight-results.json"))["actual_toplevel"])')
   ```

   确认 candidate_system 仍为报告中已验证的 liu-bigpc store path，不是另一主机。
5. 用户固定 system profile 并激活该候选；这里的 `candidate_system` 是步骤4核对的精确 store path，
   不能填默认主机的构建路径或其他主机：

   ```bash
   sudo nix-env -p /nix/var/nix/profiles/system --set "$candidate_system"
   sudo "$candidate_system/bin/switch-to-configuration" switch
   systemctl --user start tag-native-stack.target
   ```

   实际执行权属于用户。激活不是跨系统、HM和数据的原子事务；失败后先检查哪些单元已启动，
   只要原生开始写入就必须采用下述新状态回退，不能直接启动旧 DB 的源容器。
6. 核验5006认证入口、loc_pc、5009身份/签名同步与发现，再进行 T005e 登录/开机与浏览器验收。
   固定目标已挂 default.target；无 ready 时不创建空库，有 container-mode 时不启动原生服务。

## 保留新写入的容器回退

回退继续使用候选系统的守卫单元；不先退回没有此守卫的旧系统。

1. 停原生 target 与恢复单元，确认 target、core、files、workspace 全部 inactive/failed：

   ```bash
   systemctl --user stop tag-native-stack.target pc-private-node-restore.service
   systemctl --user is-active tag-native-stack.target tag-all-core.service \
     tag-native-files.service tag-native-workspace.service
   ```

   如果任何单元仍为 active/activating/deactivating，不继续。只停止 target 会连带停止三个 PartOf 子单元；
   必须检查实际结果，不把命令返回成功当作全部 writer 已停。
2. 用私有权限写明回退模式，阻止原生重新启动：

   ```bash
   native_state=/home/liou/.local/share/tag-all/pc-native
   umask 077
   printf 'explicit-container-fallback\n' > "$native_state/container-mode"
   ```

3. 合并原 PC 模板与快照 overlay，先静默解析；再**只创建固定五个容器，不启动**。
   这一步重建容器实体，保留 bind 数据与原源备份，不使用 down、删除卷或 remove-orphans：

   ```bash
   podman-compose --podman-args='--remote --url unix:///run/user/1000/podman/podman.sock' \
     -f /data/project/tag-all/deploy/pc/compose.pc.yaml \
     -f "$native_state/config/container-rollback.json" --profile peer-discovery config -q
   podman-compose --podman-args='--remote --url unix:///run/user/1000/podman/podman.sock' \
     -f /data/project/tag-all/deploy/pc/compose.pc.yaml \
     -f "$native_state/config/container-rollback.json" --profile peer-discovery \
     up --no-start --force-recreate --no-deps --no-build --pull never \
     tag-server peer-discovery peer-gateway dufs caddy
   ```

   若固定镜像已被清理，命令失败；应恢复对应固定镜像后重试，不以浮动标签替换。
   创建失败时保持 container-mode，两个运行模式均不启动；原新数据仍留在私有目录。
4. 核验实际创建的容器，再由带守卫的单元启动：

   ```bash
   python3 scripts/native_pc_mode_guard.py --mode container
   systemctl --user reset-failed pc-private-node-restore.service
   systemctl --user start pc-private-node-restore.service
   ```

   守卫再检查一次：旧 pc.db、旧 CA 挂载、错误工作区、镜像不符或原生未停均拒绝。
   之后登录/开机也只在 container-mode 下恢复这五个已核对容器。
5. 检查认证、已有与新增标签/网页/文件、节点身份与同步。此回退不恢复旧 DB，原生期间的新写入仍在 core.db。

## 从容器回退模式返回原生

先停恢复单元，再用前文固定五个名称停止容器；实际检查它们全部停止。
然后只删除 `pc-native/container-mode` 这个模式标记，保留 ready、DB、CA与所有备份；
执行 `--mode native` 守卫后启动 tag-native-stack.target。两种模式继续使用同一份新状态，
不能在任何 writer 在线时另做数据库复制或共享可写 CA 存储。

## 开发回归与收尾

- `python3 -m unittest discover -s scripts/tests -p 'test_native_pc*.py'`：配置、离线快照与模式守卫。
- `check-native-pc-rollback.py`：PyYAML + podman-compose，仅合成凭证/DB与实际模板解析，不启动容器。
- `check-native-pc-guard-runtime.py --generation <generation> --output <report>`：真实生成命令，
  六个自有临时 systemd 单元；Podman及原生状态均用合成桩；临时单元自动收集、fixture精确清理。
- 还必须构建完整实际 toplevel 与对应 HM，核对生成的固定名称/守卫/自动启动条件。
- 真实停机、离线生产复制、激活、真实开机及 LAN 发现属于用户后续验收，未由合成结果替代。

## S3 PDF 候选边界

`tests/native-pc-host.nix` 显式 `processing=true` 可构建新增工作区/PDF 配置，
镜像/状态/socket 参数来自已固定的产品证据；默认仍是原 core 候选。
PDF 包装和系统/HM 构建已通过，不代表所有媒体兼容，也不代表默认 Podman 已有工具镜像。
此候选尚未激活或通过全部 S3，不用于用户切换；仍等待完整工具接入、实际单元运行、
镜像生命周期、启动互斥和回退复验。切换命令中的最终产物仅在 S3 通过后更新。
