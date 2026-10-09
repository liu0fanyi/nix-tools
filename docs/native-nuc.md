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

## 固定切换入口

```bash
python3 scripts/native-nuc-switch.py                            # 默认只读现网预演
# 仅在重新确认NUC编辑已保存关闭后执行以下动作：
python3 scripts/native-nuc-switch.py --activate --editors-closed
# 仅在需要明确回退且文件安全后执行：
python3 scripts/native-nuc-switch.py --rollback --editors-closed
```

入口从本机准备receipt选择固定远端release，校验manifest/控制文件/源镜像/挂载与配置；
不接受任意主机、路径或候选。切换后立即验证HTTP就绪、双区认证与PC–NUC同步，
不能把target active当成业务成功。失败保留私有transaction.json和快照，不自行重启旧writer。
回退打开两份迁移后的新DB，保留原生期间写入；不能调用旧发布或恢复旧数据库。
快照前失败尚无自动恢复入口，需根据journal检查停止点后明确处理。

本机隔离集成门槛：

```bash
python3 -m unittest discover -s scripts/tests -p 'test_native_nuc_*.py'
python3 scripts/check-native-nuc-switch-compose.py
```

Compose门槛用独立rootless VFS和随机容器项目，真实双版本CLI和合成数据；不接生产数据库。
报告 `.devenv/native-nuc-switch-compose-results.json`；与真实systemd门槛及N3入口契约组合验收。

## 首次失败回退后的再次切换

若当前journal为container-active且九容器已改用新状态，不再运行--activate或再次快照。
重新确认编辑安全后使用最新已核验receipt：

```bash
python3 scripts/native-nuc-switch.py --resume --editors-closed
```

此入口仅重用两份当前core.db，不恢复源DB；失败仍保留journal并明确诊断。
本次守卫修正将precheck委托宿主用户管理器，避免+执行方式与读写BindPaths组合失败。
