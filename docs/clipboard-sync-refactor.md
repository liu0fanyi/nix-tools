# Clip 开发与回归入口

规格由本仓库统一管理：[传输](../specs/005-clipboard-core/spec.md)、[限额与恢复](../specs/006-clipboard-reliability/spec.md)、[发布](../specs/007-clipboard-release/spec.md)。实现位于 clipboard-sync 子模块。

在子模块 devenv 中执行 cargo test、cargo clippy --all-targets -- -D warnings；Windows 程序与测试交叉编译，Android 在对应目标检查。纯元数据策略可独立宿主测试；Android-only 插件不能以宿主编译替代真机验收。

人工回归覆盖双向文字/图片/多文件、重名保存、中断重试、配对开关、Windows 通知、Linux 通知替换及 Android 升级返回。待验收项只在上述 specs/tasks.md 维护。
