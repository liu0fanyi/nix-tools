# 任务

- [x] T001 收敛主机配置与密钥维护约束。
- [ ] T002 下次主机变更时分别核对构建、激活与桌面验收，不沿用旧快照作为现状。
- [x] T003 liu-bigpc 启用 BlueZ/Blueman，Waybar 条件增加蓝牙状态与管理入口，不改其他主机。
- [x] T004 验证蓝牙配置求值及 Waybar 生成内容；bluez/Blueman/powerOnBoot 为 true，JSON 有且仅有一个 bluetooth 模块和绝对路径管理入口。
- [x] T006 通过 just sync-todos 同步蓝牙规格与任务状态，checksum 复查通过。

2026-09-14：整机 toplevel.drvPath 求值通过（nmfr49zlkxhxkv842yi33jwcbln4jwxf）；
未执行完整构建、switch 或桌面验收，T005 保持待验证。已有 default.nix 暂存修改未动。
- [ ] T005 用户 switch 后验证 bluetooth.service、适配器与点击配对管理窗口；不自动配对或信任设备。
- [x] T007 为 Blueman 交互通知增加点击操作菜单与可见提示，取消此类通知5秒自动消失；不自动接受配对。
- [ ] T008 验证 Mako 生成配置和菜单脚本；switch 后由用户实测 Confirm/Deny，JBL 配对结果单独核对。

2026-09-14 真实链路验证：复用安装中的 Blueman _NotificationBubble，测试186的直接invoke
及用户点击测试188菜单Confirm均实际收到一次confirm回调；不是只验证菜单exit 0。
JBL随后读取Paired/Bonded/Connected均yes，未删除配对或断开。截图092736确认是旧通知157，
已单独dismiss（非确认/拒绝）；永久超时导致旧请求残留，改60秒且history=false。
图形菜单回调已通过，测试193的Deny菜单也实际收到deny回调；实际全新硬件配对的图形全流程仍未复测，取消及过期测试待补。
60秒/history=false规则求值通过，待用户rerun激活；未执行switch，未把真实配对全流程标记完成。

2026-09-14 Mako：生成配置求值、git diff --check 通过；蓝牙 actionable 规则含独立超时、
提示文本与绑定通知 ID 的菜单入口，普通5秒超时和勿扰模式保留。尚未 switch 或实测点击，
不能据此宣称 JBL 已配对成功。通知保留不延长 BlueZ/音箱自己的认证时限。

2026-09-14 点击失败复现：makoctl menu 缺少程序参数分隔符，Fuzzel 的 --dmenu 被当成
makoctl 参数，报 invalid option。补充 -- 后，用独立测试通知151和无副作用选择器验证
菜单命令退出0；Fuzzel显示测试单独执行，未操作JBL配对。修正后仍需switch及用户点击验收。
