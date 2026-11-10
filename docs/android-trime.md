# Android 同文中文九宫格

本配置针对用户选择的 Trime + 四叶草九宫格。APK和配置原包版本、URL、SHA256、官方签名指纹在 [sources.json](../config/android/trime/sources.json)，本地默认方案补丁在 [default.custom.yaml](../config/android/trime/default.custom.yaml)。官方正式APK与第三方词库/主题分开，不安装配置项目提供的debug整合APK。

手机包名 `com.osfans.trime`，已选应用专属数据目录 `/sdcard/Android/data/com.osfans.trime/files/rime`；主题 `tongwenfeng_plus`，方案 `clover_jiugong`。输入方案与键盘布局需同时匹配，单改九宫格外观不能替代方案。

## 配置与恢复

先核对包身份/签名及现有资料；已有Trime时备份它的数据目录，初次安装也保留初始化的installation.yaml和user.yaml。按sources.json下载原始APK与trime.7z，逐项校验SHA256；7z解压到临时目录。导入方案时排除installation.yaml、user.yaml、用户学习数据库、sync和build，不将上游作者的运行身份覆盖到本机。将本仓default.custom.yaml作为默认方案补丁覆盖，然后在同文主界面点“部署”，在“键盘样式→主题”选tongwenfeng_plus；“方案”应显示四叶草九宫格。后续修改先备份同名文件，不删除已有学习数据库。

本轮初始化备份在本机 `/tmp/trime-install-20261110/before-rime`，权限仅当前用户；它是临时回退备份，不是长期词库同步。上游原始安装包也只暂存在该临时目录；本仓不纳入私人词库。

回退输入法时在Android系统输入法选择器启用并选择原有搜狗；不要先卸载同文或清除数据。同文卸载前先导出资料，否则应用专属目录可能随卸载删除。

## 使用

九宫格右侧“编辑”切入同文自带的方向键面板，右下区域的Esc由本仓小补丁把Clear替换而来；不需要另造输入法或维护同文源码分支。中文候选、编辑页左右键、Esc已在知识卡QA实测；Shift加方向键在当前Helix中未形成选区，仍属于应用兼容缺口。Esc回普通模式后系统键盘会隐藏，当前QA可通过“触控按键→输入”重新进入Insert；应用仍是先前试用包，本轮未发行精简后的手机UI。

底部大块空白：同文默认预留系统手势边衬区，并参考系统导航栏frame高度。此机已在“高级→忽略系统手势边衬区”开启后实测收起额外空白；不改系统导航模式，主题keyboardPaddingBottom保持默认0。想恢复底部避让时关闭该开关即可。

## 验证范围

实际安装、中文候选及知识卡Helix操作的结果以 [TR阶段任务](../specs/010-host-configuration/tasks.md#android-同文中文九宫格阶段-tr2026-11-10) 为准。只在独立无网络知识卡QA中使用合成文字，不自动发布PC/NUC网页、不改正式知识卡数据、不修改电脑Rime。键盘本身的设置与Helix接收系统编辑操作的兼容性分开验证。
