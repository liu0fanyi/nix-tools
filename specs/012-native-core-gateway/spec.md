# 012 — 原生核心的同源认证文件入口

## 范围

在两个独立 loopback TCP 端口和私有 Unix 文件 socket组合 Caddy、原生 core 与 DUFS；保持 /tag-api 和静态/文件入口。Home Manager 默认停用，不 import 到当前配置，不激活 PC/NUC。

## 固定验收边界

1. 同源根入口与 /tag-api 通过真实原生服务。
2. 匿名与错误凭证拒绝；已登录可以受控操作自己的临时文件/标签；不给页面任意指定 API 的能力。
3. 核心缺媒体能力反馈准确，原文件仍能读取；已通过的窗口/节点隔离保留。
4. 实际结果、限制、提交推送与所属固定 todos 镜像收尾。

本规格属于 tag-all 024 T004 的配套关卡；真实 PC 迁移、生产同步/配对、全部工具容器与其他平台不在本步。

## 结果与复验

实际原生核心 + Caddy + DUFS Unix socket 通过：匿名/错误凭证及匿名写入拒绝、认证标签/文本/上传/列表/原文件/流读取、私有应用入口拒绝，合成 PDF 未改变，自有进程/目录已清理。Home Manager 启用/停用求值、全部断言、依赖关系与特殊字符参数转义通过；模块未激活。

在 nix-tools 的 devenv shell 中执行 `just check-native-workspace /data/project/tag-all /data/project/dufs-plus /data/project/tag-browser`。需既有 core 原生 gate 报告、dufs-plus dist、Playwright 的 NODE_PATH 和实际 CHROMIUM_PATH；无 API/静态 HTTP mock。模块复验见 nix-tools 的 tests/native-workspace-module.nix。生产安装、实际开机和迁移/回退属于 tag-all 024 T005。
