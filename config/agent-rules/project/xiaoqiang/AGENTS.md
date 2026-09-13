# xiaoqiang 工程约束

## 文档与跟踪资料发布（仅本目录及其子工程）

NUC `liou@nuc.local:/home/liou/dufs/` 是 xiaoqiang 专用发布区。
本规则仅适用于 `/data/project/xiaoqiang/`，不得复制到工作区根部或其他工程。

本目录内面向用户阅读的工程文档、接线说明、测试记录、调查结论和阶段状态，除在
各自 Git 仓库保留权威源文件外，还应在同一任务内同步到 NUC 的对应发布目录：

```text
liou@nuc.local:/home/liou/dufs/<工程发布目录>/
```

具体目录以各子工程 AGENTS.md 或既有发布配置为准，不改变已有固件下载路径。
发布目录以 README.md 为预览入口，整理后的 Markdown 放 docs/，适合网页预览的
PDF 等参考资料放 references/。文档有实质变化时同步更新索引和发布副本。
源码压缩包、安装包、构建目录和临时解包内容默认不放发布页，除非用户明确要求；
已经约定的固件/镜像发布流程仍按各子工程规则执行。

本目录所有工程（含子仓库、共享应用与固件）的 specs、任务和文档 **仅同步到 dufs**，
禁止写入 `/home/liou/dufs-lan/todos/`，不得以“状态镜像”为由建立第二份副本。
本地各仓库 specs 是唯一权威源；此规则优先于通用 work-progress 的 todos 示例。
AGENTS/constitution 保留 Git，不作为阅读文档上传。同步前核对精确目标及白名单，
回读校验摘要；禁止宽泛删除其他工程固件、资料或运行数据。
