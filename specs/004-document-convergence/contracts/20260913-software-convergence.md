# 软件资料迁移收尾（2026-09-13）

## 当前结论

本轮软件工程规格归纳已完成，包含 signature-server。核验快照中 30 个规格源的
路径集合与文件 SHA256 均与正确目的地一致，见
[完整核验](20260913-final-mirror-verification.json)。此结论不代替产品构建或实机验收。

一般工程镜像到 dufs-lan/todos，各 xiaoqiang 工程只镜像到既有 dufs 项目目录。
误放的 10 个 todos 目录、225 个文件已逐项核对 dufs 副本后清理，sip_old 的失效
跨项目入口已移除。400m 原下载首页保留，规格入口为 SPECIFICATIONS.md。

## 归纳与保留

- 初轮 18 个工程各自维护 specs；clipboard-sync 按用户约定归属 nix-tools。
- CMT/400m 共用一仓两分支；sip 与 sip_old 独立。SDK/image/ZIP 默认原格式、SHA256
  与源码补丁，不因体积或私有标签一律加密；已完成归档不自动重做。
- 小智父仓库和固件各有私有远程，历史 roadmap 已提炼为 7 组规格；源和固件可恢复。
  容器构建仍受 UID/GID 映射问题阻塞。
- xiaoqiang 根部 6 份 Markdown/Word 要点归入 sip/demo、sip_old、device-common。
  示例账号密码未复制到文档镜像。
- hardware-relation-studio 归入 bevy-project-planner；独立画板 origin 延后需求归入
  bevy-sketch。camera.md 两条误放的软件性能记录已提炼并移除，硬件记录保留。
- signature-server 的接口契约、长期约束、手册和 dufs 镜像已完成。
  暂缓的是私钥注入、额度/事务修复、容器与生产改造；整库推送待历史敏感信息处理。
- 个人购物、学习、写作、未归属软件工程的硬件探索、运行画布与固件、厂商原件和
  SDK 私有归档保留，不强行转为 spec。活跃项目的未提交代码不随本次文档整理提交。

## 备份位置

NUC /home/liou/.local/state/xiaoqiang-repo-audit/ 下保留 planner-document-backups-20260913、
planner-final-cleanup-20260913 与 xiaozhi-cleanup-20260913/remote-documents 原件。
本机同级 loose-documents-20260913 保存根部 Word/Markdown 原件，
xiaozhi-cleanup-20260913 保存原 Git bundle 和修改备份。它们不作为第二套计划。

## 规则与 Git 收尾

根 AGENTS 和 work-progress 技能现由 nix-tools/config/agent-rules 管理，原位置用
符号链接引用；操作见 [本机规则管理](../../../docs/local-agent-rules.md)。
Tauri main 跟踪已确认最新的 origin/main；签名服务 .password 忽略规则已本地提交，
未因此上传含未处理敏感历史的整库。无产品部署、重启、烧录、数据库迁移或签名请求。

## 核验记录的效力

旧 document-audit/inventory、29/30 及目标纠正 JSON 仅作当时快照，不代表当前待办。
本页和完整核验文件为本轮最终结论；signature-server 不再是文档例外。
后续代码和规格变化仍须通过各仓库 sync-todos 更新，不以本快照证明未来状态。
