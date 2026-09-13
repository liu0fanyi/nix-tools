# 软件资料迁移收尾（2026-09-13）

## 已核对的归属与处理

- 初轮 18 个工程及 nix-tools/clipboard-sync 的规格仍以各自已确定权威源维护。
- xiaoqiang 的 CMT/400m 共用一仓两分支；其他已整理工程独立管理，sip 与 sip_old
  不合并。SDK/大镜像采用原格式归档、SHA256 与源码补丁，不能因体积大而一律加密。
- 小智父仓库与独立固件已建立 xiaoqiang-xiaozhi / xiaoqiang-xiaozhi-firmware 私有远程；
  历史 roadmap 提炼为 7 组规格，参考依赖固定 SHA，真实未提交修改已保存。
  新 clone 已恢复父仓库和固件提交；容器解包因 UID/GID 映射失败，构建验收未通过。
- xiaoqiang 根部 6 份 Markdown/Word 已提取关键需求和契约至 sip/demo、sip_old、
  device-common。Word 示例账号密码未复制到规格；原件先私有备份再移除。
- device-common 的 main 已经 NUC 既有凭据正常推送 Gitee，远端核对
  449a7fa8186aea9af1228e6cfbaad9fa8d001549；本机 SSH 凭据问题没有通过跳过校验解决。
- hardware-relation-studio 旧入口归入 bevy-project-planner/specs/001-bevy-planner；
  旧 Leptos MVP 结论不等同当前 Bevy 版验收。旧 DUFS trial 里的独立画板 origin 需求
  归入 bevy-sketch/specs/004-input-and-performance，保持延后。
- camera.md 中两条误放的画板性能记录已有 Sketch 对应规格，只移除此两条软件记录。
- tag-all、device-bean-mobile、esp32-focus-writer、dufs-plus 的本轮规格快照已同步；
  正在开发的未提交代码不随文档整理提交。

## 清理与备份边界

已按摘要核对后移除旧计划。NUC project-planner 的 6 个历史备份目录转入
`/home/liou/.local/state/xiaoqiang-repo-audit/planner-document-backups-20260913/`；
本轮 trial 原件保存在同级 `planner-final-cleanup-20260913/`，不作为第二套计划。
小智旧远端资料保存在同级 `xiaozhi-cleanup-20260913/remote-documents/`。
根部 Word/Markdown 原件在本机同级 `loose-documents-20260913/`，含敏感示例，不发布。
小智 Git bundle 与修改原件在本机同级 `xiaozhi-cleanup-20260913/`。

## 明确保留与未完成项

- signature-server：用户明确暂缓；本地草案不计入已推送/已镜像清单。
- 个人购物、学习、写作，以及尚未归属软件工程的相机/XIAO 等硬件探索保留原文件。
- 生产 document.json、下载固件、厂商原始资料、SDK 归档和私有备份属于运行数据或参考，
  不要求转换成 spec，也不因整理文档删除。
- 源码恢复、构建、部署与实机验收分别记录；小智容器复验、各仓库 spec 中未勾选的
  功能/板端验收继续待办。本轮没有部署应用、重启服务、烧录或发起 SIP 通话。

此前 document-audit.md、inventory.json 等是初轮范围的历史证据，不代表本轮新范围。

## 最终镜像核对

[逐项目 SHA256 比较结果](20260913-mirror-verification.json)：工作区审计的 30 个规格源中，29 个路径集合与文件摘要完全一致；唯一差异为明确暂缓的 signature-server 草案。nix-tools 和小智固件规格另由各自同步脚本回读校验。核对反映本次快照，后续开发需继续通过 sync-todos 更新。


## 发布目标纠正（同日用户重申，取代上节目标判定）

此前核对把 xiaoqiang 的 todos 副本当成正确目标，属于审计遗漏；“29/30 一致”只证明
内容相同，不能证明符合发布位置约束。xiaoqiang 的唯一镜像目标是既有 dufs 项目目录。
10 个同步脚本、各仓库 AGENTS/constitution 与工作区入口已纠正，脚本拒绝错误目标。
已按 dufs 副本逐文件 SHA256 核对，清理 todos 下 10 个误放目录、225 个重复文件，
并移除 a-next 的 sip_old 失效入口。400m 下载首页不动，文档入口仍为 SPECIFICATIONS.md。
[纠正后的逐项目核验](20260913-dufs-only-verification.json) 记录完整目标：29 个一致，
signature-server 仍为明确暂缓例外；不再将该例外默认指向 todos。


## signature-server 暂缓范围澄清（同日用户确认）

此前将“下次用到再改”扩大为文档归纳暂停，属于误读。本节取代前文将其列为文档例外
的判定。现已完成 Spec Kit/constitution、接口与签名契约、操作手册和同步入口，
step.md 提炼后删除并保留 Git 历史；规格已本地提交并镜像到 dufs/signature-server。
[本次摘要核验](20260913-signature-document-verification.json) 确认内容一致。
暂缓项是密钥注入、额度/事务修复、容器改造及生产验证；整库 Git 推送等待历史敏感
信息处理，不再作为文档归纳前置条件。没有实施产品代码改造、运行服务或部署。
