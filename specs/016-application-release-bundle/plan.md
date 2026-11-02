# 计划

Constitution Check：只在PC实现/验收，nix-tools owns交付；读取产品proof与固定制品，不修改产品源码、Bevy/quick-note、认证或用户profile。外部参考无新增，锁定依赖不变；自产文档spec/contracts，工具scripts，合成数据仅临时目录。核对工作区AGENTS及本仓constitution。没有系统switch、服务发布或数据恢复。

模块：application_release_bundle.py负责清单/冻结/证明与prepare桥接；check_application_bundle.py只负责自有组合生命周期；application-bundle.browser.cjs只负责隔离浏览器场景。just提供create/check/prepare固定入口，沿用原Manager，不复制其事务。纯合同单元覆盖漂移、错误证明、版本不匹配/路径逃逸、伪造成功和prepare前拒绝；真实CLI/Basic/strict/API/WASM覆盖组合。

顺序按B1–B4。只使用合成namespace迁移fixture，不重跑生产迁移；若实际组合发现业务失败，报告具体失败并在所属产品另按规格修复，不降低断言。
