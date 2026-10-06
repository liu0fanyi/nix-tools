# 同源原生网关契约

- 入口默认 `http://127.0.0.1:18006/`；核心仅 `127.0.0.1:18081`。文件服务绑定所有者私有 700 目录下的 Unix socket，不另开未认证文件端口。
- 所有网关请求先经过 Basic Auth，匿名与错误凭证返回 401。运行期 authFile 必须属于当前用户、普通文件、600，真实路径在工作区外；仅路径进入 Nix store，不导入凭证或散列。HTTP 仅限本机 loopback；不直接用于 LAN。
- `/tag-api/*` 去前缀转核心；清除设备 API/注册头。核心仍属于可信本机服务边界；没有多用户隔离承诺。
- `/.dufs-plus/capabilities.json` 声明文件/标签写入，禁用 Bevy/game/terminal；处理能力由核心目标接口给出，不伪造 PDF 能力。
- `/`、`/index.html` 使用既有前端，no-cache；静态资源与 `/dist/*` 读取前端，`?json` 查询及其余文件操作走 DUFS。设备、转录、录音专用入口返回 404。
- 默认停用模块；网关 Requires/After 核心与文件单元。未导入当前用户配置，不激活、不迁移状态。
- 合成验收凭证只经 stdin 传给测试；本关不使用生产身份、工作区或数据库。

复验模块：`nix eval --impure --json --expr 'import ./tests/native-workspace-module.nix { infrastructure = /data/project/nix-tools-native-core; tagAll = /data/project/tag-all; dufsPlus = /data/project/dufs-plus; }'`。检查 assertions 全为 true、停用无服务、Requires 包含两个上游以及空格/中文/%/$ 转义。它不证明真实安装或开机启动。
