# 任务

- [x] T001 提炼桌面集成、Android 更新与 0.1.18 操作反馈要求。
- [x] T004 修复 `[skip ci]` 提交无 Cachix 产物导致 rerun 卡死：wait-for-ci 对顶端提交自动 workflow_dispatch 补跑，非顶端明确报错。
- [ ] T002 后续版本实测共享更新器完整下载/安装及数据保留。
- [ ] T003 公开稳定版门槛评估（暂停，重新确认范围后实施）。
- [x] T005 根因收敛：revision 改为运行期注入，不再参与 derivation 哈希；实证源码相同、commit 不同得到同一 store path。
