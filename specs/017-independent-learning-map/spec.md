# 独立学习地图登记与发布

用户要求学习地图可独立发布，保留/dist/learning-map/地址；首次允许一次受控服务切换，此后仅静态文件同步。复用现有applications机制和native版本管理器，不新增HTTP服务、端口、通用任意目录映射或认证。

首次配置登记只允许NUC private/config/application-entry.toml，新增固定name=learning-map及固定private/apps/learning-map根。原配置所有解析后字段保留，重复登记拒绝。配置加入原发布事务的精确目标集合；失败或显式回退恢复原配置和程序，不恢复数据库。旧发布调用没有登记参数时行为保持。

静态内容归bevy-learning-map，发布命令归bevy-env既有发布器。原书和用户学习正文不进入应用静态目录。跨仓同一阶段计数归tag-all/specs/041-independent-learning-map/tasks.md，本仓不重复计数。
