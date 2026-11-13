# bundle-v1

config只接受schema/package/frontend/manager/file_server_package/backend_proof/frontend_proof/tag_source/dufs_source/browser_source。路径显式，包/前端为已有固定Nix目录，proof限定所属specs；不接收网络URL或凭据。创建时核对源码/成功证明/制品，输出内容寻址的components/protocols/inputs/control清单及bundle_id。

check先重新核对所有绑定，真实运行后写result；只有全部必需case成功且清理完成时passed才为true，记录bundle_id、当前control摘要和case集合。prepare重新生成/核对bundle以及成功结果，再仅将package/frontend传给既有固定管理器prepare；不把runtime report字段当任意命令。任何变化须重建当前bundle并验收，不能重用旧passed。

场景清单为LAN Basic manifest/locations、unsigned sync401、anonymous401、cross-origin403、served assets、fresh、aliases-content/reload、progress-conflict、unknown-operation。实际浏览器无API mock；读取失败和确认空数据不能相互替代。

共享WASM适配器与桥源码同样冻结；桥制品与已有构建输出一致，两端固定共享revision必须相同。
初版只接受已有037 native-incremental-v1后端证明，其他种类显式拒绝，不自动降级。
结果中的实际CLI/前端、无mock和无日常profile/生产访问声明必须匹配；日志须存在且摘要相同。
清单与日志是本机可信工具执行的一致性证据，不是对恶意本机用户的签名证明。
实际组合启动包内Rust CLI，不替代原应用监督器/更新回退门槛，也不声称覆盖Firefox特权UI。

## 可选独立学习地图登记

组合配置可显式提供bool `register_learning_map`，省略或false保持旧行为。true仅允许NUC：组合夹具在选定不可变前端的learning-map目录存在时配置同名应用，prepare向已选管理器传递`--register-learning-map`；生产根仍由017管理器固定为private/apps/learning-map，不从该字段接受路径或任意应用名。标志和控制代码均参与组合身份，改变后必须重新创建与验证，不复用旧组合报告。
