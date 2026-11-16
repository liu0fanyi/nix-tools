# 计划

Constitution Check：只在PC实现/验收，nix-tools owns交付；读取产品proof与固定制品，不修改产品源码、Bevy/quick-note、认证或用户profile。外部参考无新增，锁定依赖不变；自产文档spec/contracts，工具scripts，合成数据仅临时目录。核对工作区AGENTS及本仓constitution。没有系统switch、服务发布或数据恢复。

模块：application_release_bundle.py负责清单/冻结/证明与prepare桥接；check_application_bundle.py只负责自有组合生命周期；application-bundle.browser.cjs只负责隔离浏览器场景。just提供create/check/prepare固定入口，沿用原Manager，不复制其事务。纯合同单元覆盖漂移、错误证明、版本不匹配/路径逃逸、伪造成功和prepare前拒绝；真实CLI/Basic/strict/API/WASM覆盖组合。

顺序按B1–B4。只使用合成namespace迁移fixture，不重跑生产迁移；若实际组合发现业务失败，报告具体失败并在所属产品另按规格修复，不降低断言。

本轮nix.124完整后端包装适配：组合工具原只登记037增量证明，而本轮PDF执行器正确进入full。加入显式full-matrix输入核验，保留原增量路径；不重编产品、不降低原39步矩阵/实际CLI/源码与隔离运行门槛，不改管理器。宪法核对：PC构建、冻结组件、独立应用/认证/数据保护和无系统switch保持；无外部参考新增。唯一交付计数仍归Tag Browser049本轮发行。
