# NUC 原生候选准备工具

规格与验收边界见 [013](../specs/013-native-nuc-rollout/spec.md) 和
[任务清单](../specs/013-native-nuc-rollout/tasks.md)。此页只说明操作。

在本机 nix-tools 仓库、具备 Nix/OpenSSH/Python 的环境执行：

```bash
python3 scripts/native-nuc-prepare.py            # 默认只读预演，不写远端
python3 scripts/native-nuc-prepare.py --prepare  # 明确传输，不停服务
```

工具只支持 liou@nuc.local、home.toml 和 N3 已验收的固定制品。
它核对源拓扑、复制闭包，并向 `/home/liou/.local/share/tag-all/nuc-native-release/<manifest摘要>/`
精确传输 manifest、实例配置与内部控制模块；不传目录树或使用 --delete。
文件摘要核验后注册候选 GC root，不安装/启用用户单元、不访问生产数据库。
报告在本机 `.devenv/native-nuc-preparation-results.json`；其中 activated 始终为 false。

本机自建制品目前未附缓存签名；仅在 NUC 已配置 trusted-users liou 时使用本次复制显式导入，
并比对全部 NAR 哈希与大小。工具不会修改系统信任配置或 SSH 主机密钥策略。

目的地必须是新的私有目录，已有目录不覆盖；失败保持原生产运行，不自动启动旧writer或恢复DB。
不要用候选准备成功代替停服/切换授权。snapshot/guard 是内部模块，生产接入状态以任务清单为准。
