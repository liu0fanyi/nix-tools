# 技术方案

复用 Clip CI、父仓库 update-clipboard-sync.nu 和 android-app-kit。操作说明留在 clipboard-sync/docs/android-app-kit.md。

历史文档记录 Android 0.1.18（54dce2c）正式发布，并有用户候选确认；本轮只归档需求，不重新发布，也不推断手机当前已更新。

## 宪法检查

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。

## 最新版 Pin 方案

沿用本应用现有发布入口，固定缓存 `liu0fanyi-nix`、固定应用名、只保留一条 revision。先上传完整运行闭包和核验，再 Pin；CI 串行并核对当前发布版本/分支头，避免迟到旧任务覆盖新 Pin。本机补齐当前固定输出，匿名 API 核验远端目标及保留设置。Constitution Check：继承工作区/本仓规则；无新外部参考或依赖，不切换系统、不改用户数据，镜像限本仓白名单。
