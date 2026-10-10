# 基础设施配套方案

## Constitution Check

继承工作区及nix-tools宪法：PC唯一构建源，NUC只接收固定制品、不编译/系统switch；
秘密/模型/用户DB不入Git或store，不修改Aliyun，不覆盖Bevy或独立应用产物。
来源为本仓现有native-workspace/native-peer/native-nuc/render及产品027；没有新增参考仓库/浮动gitlink。
产品契约权威位于tag-all027，配套规格只记录安装/入口/恢复边界；不增第二套业务路由。
现阶段只核对与记录，不执行生产配置更新，E1固定库存以产品baseline-results.json为准。

## 对应五步

- E1：产品已核对实际两端六个listener库存、源码SHA、认证/内部头/路径；本仓职责及产品契约引用固定。
- E2：产品Rust同进程应用入口，不在本仓实现数据库业务或另一套路径兼容器。
- E3：移除PC网页代理依赖、生成NUC双实例入口/受信Unix与精简外部代理、守卫及回退候选；保留私人TLS单writer。
- E4：最终服务/路由/认证/来源/只读/独立应用/新DB回退组合验证。
- E5：范围内预演、传输、激活与真实验收，失败保留新状态；PC系统switch用户执行，NUC无系统switch。

当前1/5、剩余4，下一步产品E2；不重复将两仓各5项相加。
