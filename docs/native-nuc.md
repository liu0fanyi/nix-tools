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

## 启动接入的隔离验收

在真实宿主用户终端运行：

```bash
python3 -m unittest scripts.tests.test_native_nuc_startup deploy.tests.test_render deploy.tests.test_release_pc deploy.tests.test_manage
python3 scripts/check-native-nuc-startup.py
```

门槛使用随机临时用户单元、合成九容器库存，验证七服务各自守卫和保留入口顺序、
namespace/uid、旧writer阻断、transition和新状态回退拒绝，结束仅清理自有单元。
受限命名空间中需用临时systemd-run用户单元运行同一脚本，不能把沙盒自身当宿主namespace。
报告 `.devenv/native-nuc-startup-results.json`。生产startup内部入口需由切换控制器安装，
不要直接创建mode标志或手动启动候选；当前生产尚未接入。剩余工作以013任务清单为准。
