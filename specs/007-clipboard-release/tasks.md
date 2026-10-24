# 任务

- [x] T001 提炼桌面集成、Android 更新与 0.1.18 操作反馈要求。
- [x] T004 修复带 CI 跳过标记的提交无 Cachix 产物导致 rerun 卡死：wait-for-ci 对顶端提交自动 workflow_dispatch 补跑，非顶端明确报错。
- [ ] T002 后续版本实测共享更新器完整下载/安装及数据保留。
- [ ] T003 公开稳定版门槛评估（暂停，重新确认范围后实施）。
- [x] T005 根因收敛：revision 改为运行期注入，不再参与 derivation 哈希；实证源码相同、commit 不同得到同一 store path。

## 最新版缓存保护（LP）

- [x] LP1 发布入口增加固定名称及 `--keep-revisions 1`，失败不移动旧 Pin，CI 拒绝旧任务回写。
- [x] LP2 失败路径回归及当前固定输出远端 Pin/保留策略核验。
- [x] LP3 文档、独立提交/适用远程推送和本仓镜像校验。

LP 阶段 3/3，剩余 0。四应用共 18 项隔离回归通过；本应用远端 Pin、保留一版及实际发布结果见[证据](latest-cache-pin-results.json)。本轮仅改缓存发布流程；安装 flake.lock 和运行包不变，不要求用户执行 rerun。
