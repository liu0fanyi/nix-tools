# 基础设施配套方案

## Constitution Check

继承工作区及nix-tools宪法：PC唯一构建源，NUC只接收固定制品、不编译/系统switch；
秘密/模型/用户DB不入Git或store，不修改Aliyun，不覆盖Bevy或独立应用产物。
来源为本仓现有native-workspace/native-peer/native-nuc/render及产品027；没有新增参考仓库/浮动gitlink。
产品契约权威位于tag-all027，配套规格只记录安装/入口/恢复边界；不增第二套业务路由。
现阶段构建产品入口候选，不执行生产配置更新；E1固定库存以产品baseline-results.json为准。

## 对应五步

- E1：产品已核对实际两端六个listener库存、源码SHA、认证/内部头/路径；本仓职责及产品契约引用固定。
- E2：产品Rust同进程应用入口，不在本仓实现数据库业务或另一套路径兼容器。
- E3：移除PC网页代理依赖、生成NUC双实例入口/受信Unix与精简外部代理、守卫及回退候选；保留私人TLS单writer。
- E4：最终服务/路由/认证/来源/只读/独立应用/新DB回退组合验证。
- E5：范围内预演、传输、激活与真实验收，失败保留新状态；PC系统switch用户执行，NUC无系统switch。

当前2/5、剩余E3/E4/E5三项，下一步E3.c NUC候选；不重复将两仓各5项相加。

## E3展开与当前边界

沿用产品027的a启动包装/b PC候选/c NUC候选/d更新及回退四项，不重复计数。
E3.a已在产品仓通过同一E2二进制、真实包装/DUFS/独立工具运行时、socket日志及实际用户服务SIGKILL重启、
合成Home Manager generation和纯核心兼容检查。证据为产品027/entry-package-results.json。
PC模块已加入显式应用模式，默认旧模式和生产配置仍未变；c须保留Authelia/其他站点。
E3内部2/4、剩余2项，下一步c；不以产品包装检查代替本仓完整候选或E4组合。

## E3.b PC候选已验收

候选工厂applicationEntry默认false；显式true将5006交给Tagall，同时保留Caddy私人5009 TLS。
Caddy仅固定private peer socket转发与源网段限制，不再剥离API前缀或注入管理员令牌；
typed角色与路径授权由产品Rust承担。应用Requires文件/处理服务，无Caddy依赖。
私有入口TOML配置和socket父目录的生产准备归d，构建不修改生产状态。
`just check-application-pc /data/project/tag-all /data/project/dufs-plus`构建完整系统与实际HM，
复验旧默认HM、8项真实生成守卫及7项隔离TLS场景；所有临时服务使用独立XDG并精确清理。
产品027/entry-pc-candidate-results.json固定源摘要、store路径和门槛。
实际工作站flake.lock只读用于候选，排除其他脏源码、不提交无关锁文件变更。
首次测试误写默认Caddy autosave已按用户明确授权从现用显式配置重建，历史字节不可恢复；
现用服务用不同XDG与显式配置，未重启。最终检查已隔离XDG。
E3内部2/4、剩余NUC候选及更新/回退预演两项；E4最终认证/只读组合不提前计完成。
