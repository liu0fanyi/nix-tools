# Android 同文中文九宫格

本配置针对用户选择的 Trime + 四叶草九宫格。APK和配置原包版本、URL、SHA256、官方签名指纹在 [sources.json](../config/android/trime/sources.json)，本地默认方案补丁在 [default.custom.yaml](../config/android/trime/default.custom.yaml)。官方正式APK与第三方词库/主题分开，不安装配置项目提供的debug整合APK。

手机包名 `com.osfans.trime`，已选应用专属数据目录 `/sdcard/Android/data/com.osfans.trime/files/rime`；主题 `tongwenfeng_plus`，方案 `clover_jiugong`。输入方案与键盘布局需同时匹配，单改九宫格外观不能替代方案。

## 配置与恢复

先核对包身份/签名及现有资料；已有Trime时备份它的数据目录，初次安装也保留初始化的installation.yaml和user.yaml。按sources.json下载原始APK与trime.7z，逐项校验SHA256；7z解压到临时目录。导入方案时排除installation.yaml、user.yaml、用户学习数据库、sync和build，不将上游作者的运行身份覆盖到本机。将本仓default.custom.yaml作为默认方案补丁覆盖，然后在同文主界面点“部署”，在“键盘样式→主题”选tongwenfeng_plus；“方案”应显示四叶草九宫格。后续修改先备份同名文件，不删除已有学习数据库。

本轮初始化备份在本机 `/tmp/trime-install-20261110/before-rime`，权限仅当前用户；它是临时回退备份，不是长期词库同步。上游原始安装包也只暂存在该临时目录；本仓不纳入私人词库。

回退输入法时在Android系统输入法选择器启用并选择原有搜狗；不要先卸载同文或清除数据。同文卸载前先导出资料，否则应用专属目录可能随卸载删除。

## 使用

九宫格右侧现在为“Helix”：点按进入专用控制页并将知识卡QA引擎切到normal，长按仍进入同文通用编辑页。核心布局为前词/上/后词、左/选区/右、行首/下/行尾；“选区”切真实Helix select，随后方向键扩展选择；Esc回normal，输入切insert并返回中文九宫格。外围撤销/重做执行引擎命令，不输出z/y。通用编辑页本身仍只换键盘布局，不保证切换Helix模式。

专用页只适用于本轮知识卡QA候选：应用默认只显示输入/Esc及真实模式，额外触控九宫格需主动展开。正式知识卡、PC/网页尚未替换。组合键契约为Ctrl+Alt+F12进入、F11返回输入、F1/F2前后词、F3/F4行首尾、F5/F6撤销重做、F10选区（全部带Ctrl+Alt）。裸F4会被Rime方案菜单截走，不能沿用裸功能键。default布局明确import_preset clover_jiugong；输入动作明确选择clover_jiugong，避免初次加载/通用默认页回退全键盘。配置修改后“部署”，若仍显示缓存布局，重新选择当前主题再回QA核对Helix标签；不清应用数据或词库。

底部大块空白：同文默认预留系统手势边衬区，并参考系统导航栏frame高度。此机已在“高级→忽略系统手势边衬区”开启后实测收起额外空白；不改系统导航模式，主题keyboardPaddingBottom保持默认0。想恢复底部避让时关闭该开关即可。

## 验证范围

实际安装、中文候选及知识卡Helix操作的结果以 [TR阶段任务](../specs/010-host-configuration/tasks.md#android-同文中文九宫格阶段-tr2026-11-10) 为准。只在独立无网络知识卡QA中验证，用户既有草稿先私有快照、临时中文提交经撤销后逐字核对恢复；不将私人正文或截图写入仓库。新控制页验收计数仅沿知识卡012/K；本仓结果见[专用页验证](../specs/010-host-configuration/android-trime-helix-results.json)。不自动发布PC/NUC网页、不改正式知识卡数据、不修改电脑Rime。键盘本身的设置与Helix接收系统编辑操作的兼容性分开验证。
