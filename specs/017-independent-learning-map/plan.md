# 实施与Constitution Check

复用native_application_release.py的plan/prepare/validate/ConfigurationTransaction及现有任务空闲、漂移、保存编辑和回退检查，增加显式--register-learning-map参数。preview/prepare不切换；首次apply将后端程序与固定配置登记放在同一次停服事务内。只私有入口登记，既有只读/公网边界保持。首次需新的后端白名单代码，受保护configuration.rs走完整发行门槛，不修改增量策略。

继承workspace与本仓constitution：本机构建、NUC只接收；不执行系统switch，不触碰helix等既有无关修改；无新增外部原始资料或Git参考。应用目录逐文件SHA及755/644核验；发布只写自有子树，不能覆盖其他应用或全量dist。原生新登记是现有应用机制的扩展，保留原事务而不是另造激活脚本。

已有译文链接及中文版内容归bevy-learning-map/specs/005；其旧纯前端候选未激活，由本次独立入口一并交付。用户已明确确认“当前编辑已保存，可以完成首次切换”；首次切换无需重复请求该确认。源码、制品或有效配置漂移仍必须重验。

## 当前范围纠正（2026-11-13）

用户指出本次为静态页面更新，并授权纠正tag-all037配置粒度：configuration.rs已取消整文件full例外，后续如恢复该原型使用现行三消费者门槛，不再沿本文件原完整矩阵计划。该独立登记未执行；本次仅通过原ff1h管理器切换4文件静态前端至ask58，后端仍2wf6pz，learning-map应用未登记。原型实现与测试保留，不把页面上线当独立发布通道上线。
