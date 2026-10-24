# Nix 应用缓存保留

现有缓存为 `liu0fanyi-nix`。每个应用发布成功并核验后更新一个固定 Pin，均使用 `--keep-revisions 1`。只保护最新一版及其运行依赖；旧版允许缓存自动回收，不主动删除，也不改变本机安装。

| 应用 | Pin | 自动更新入口 |
| --- | --- | --- |
| Tag Browser | `tag-browser-latest` | 产品 `Nix release` CI；旧发行恢复不会覆盖最新版 |
| Clip | `clipboard-sync-latest` | 产品 Linux CI；仅当前 master 头可更新 |
| Screen Cut | `screen-cut-latest` | 产品 `python3 scripts/push-cache.py` |
| Screen Mark | `screen-mark-latest` | 产品 `python3 scripts/push-cache.py` |

上传或校验失败保留旧 Pin；Pin 更新失败则发布报错。上传凭据仅在运行时读取，不写入 Nix store、Git 或资料镜像。

Nix 安装版本锁和 Cachix Pin 分别管理：前者固定安装内容，后者防止远端回收。较旧安装版本若需要重新下载，可能仍需从其归档/固定源码恢复缓存。

## 查询

可在 [Cachix Pins](https://app.cachix.org/cache/liu0fanyi-nix/pins) 查看；[官方保留策略](https://docs.cachix.org/pins)。新增其他应用时由该产品规格管理发布入口，不上传整个开发闭包。

本轮不执行系统 switch。以后确有应用安装更新时，由用户在普通终端执行：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```
