# 发布控制

完整命令、profile、infra 含义及预演方式以仓库根部 `../AGENTS.md` 为准。
在 `/home/liou/nix-tools` 执行 `devenv shell -- just test` 验证发布实现；
`devenv shell -- just -- deploy nuc all --dry-run` 预演，不进行生产切换。

源码在 PC `/home/liou/nix-tools/deploy` 维护。just deploy nuc infra 通过 SSH
管理 NUC 的基础镜像和配置；两端 frontend/tag-server 只调用 PC 产品构建入口，
NUC 使用 private、阿里云使用 public。传输、备份、激活、回滚、验收统一由 nix-tools
实现，不能调用产品的 deploy/redeploy 快捷入口，以免反向调用形成递归。
不把 PC 当生产 home 实例，不复制目标机密钥，不跳过 SSH 主机密钥验证。

工程文档同步至 `liou@nuc.local:/home/liou/dufs/nix-tools/`，README.md 为入口，
正文放在 docs/。跨工程待办仍使用远端 todos 三份文件。
