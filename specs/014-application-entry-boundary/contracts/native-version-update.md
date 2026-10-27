# 原生应用常规版本更新

本契约补充已完成入口迁移后的日常发布。产品进度权威为tag-all/specs/030-native-version-release，F1候选、F2更新回退验证、F3实际发布共三个步骤，不重新迁移数据或扩大014原有P3人工业务验收。

`just native-release pc|nuc --package <固定Nix应用包> --frontend <固定Nix前端>`默认只读预演。`--prepare`保存私有、摘要绑定的manifest和候选/前版GC根，不停服。`--apply <prepared目录> --editors-saved`在取得当轮切换授权后执行；`--rollback <prepared目录> --editors-saved`只恢复程序/前端选择，继续使用最新数据。

PC只管理tag-all-core.service，NUC只管理tag-nuc-private-core.service和tag-nuc-readonly-core.service。只新增各自80-tag-version.conf并记录版本指针，不改原单元/启动守卫、环境、配置、数据路径、认证、CA、DUFS、工具、Caddy/Authelia/DDNS及外网路由；不执行系统switch，不启动退役业务容器。

准备绑定原单元与所有已安装drop-in、当前版本指针、固定候选程序和全部前端文件摘要。未知ExecStart覆盖、配置漂移、任务活跃、并发更新及越界来源拒绝。只修改现有ExecStart的应用及前端路径，保留所有其他参数；元数据仅进入用户所有700/600的版本目录，不进入Nix store。

持全局更新锁；停对应core后取得原instance.lock并离线备份当前SQLite和metadata，保留数据库inode；备份从不自动恢复。安装配置后只重载用户单元并启动对应core，核对真实运行程序与原认证/HTTP入口。正常回退、失败回退、断电/控制器被杀后的显式回退均继续使用当前数据；只认可本事务明确的before/after字节，未知修改拒绝覆盖。无法回退时保留备份与journal、作用域core保持停止并报告。

部署仍由本机nix-tools负责；服务器只接收固定闭包和运行，不编译、不导入凭据、无需更换现用工具镜像。浏览器仍走私有Release/Cachix，不擅自关闭旧窗口或迁移用户profile。

现用target的Upholds会立即重启已停core。prepare同时绑定target原fragment、全部drop-in及保活成员；事务在/run/user/1000/systemd/user.control/<固定target>创建700目录内600的自有临时target副本，仅移除对应core的Upholds，保留其他单元保活与所有其他配置。systemd依赖列表不能通过空drop-in清除，故不得以空Upholds=声称停用。临时副本内容和原源摘要均核验，正常/失败结束删除并重载，恢复原保活；SIGKILL后explicit rollback识别同一自有副本并恢复。禁止停整个target或扩大停服到文件/工具服务，未知override拒绝。

## 普通PC系统更新的注册保留

liu-bigpc普通flake必须保留五个已验原生应用单元和default.target.wants链接。nixos/modules/pc-native-service-registration.nix声明固定应用入口模板，Home Manager在linkGeneration与reloadSystemd之后按ready存在且container-mode不存在恢复target；各服务原模式守卫继续有效。不得重新启用旧容器、重跑迁移、覆盖80-tag-version或boot守卫、创建新数据库。候选单元字节及钩子排序必须从实际Home Manager生成物验证，普通系统完整构建不能代替实际激活成功核验。源generation的“未移除”备用链接不是普通HM已经持久管理服务的证据；由用户执行系统switch，Agent只修复明确归属注册并恢复服务。

## 当轮上线授权（用户于2026-10-27修订）

对已经确定范围的常规PC／NUC应用或前端更新，用户说“上线”即授权本轮短暂停服切换；完成候选、预演与回退门槛后直接执行，不再追加保存关闭的二次问答。执行前简要提醒暂停编辑/上传即可；用户明确暂缓、仍在编辑或变更范围时遵守最新指令。兼容CLI参数名仍为`--editors-saved`，由执行方依据该轮明确上线指令传入，不得在用户未授权上线时自动设置。该规则不放宽固定制品、活跃队列/配置漂移保护、离线备份、实际验收及不恢复数据的回退边界，不授权系统switch、数据删除/恢复或未确定的发布范围。旧验收记录中的逐轮保存确认保留为历史事实。
