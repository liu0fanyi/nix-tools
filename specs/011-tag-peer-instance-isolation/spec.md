# Tag Server 实例同步隔离

## 范围

NUC 5006 私人实例保留既有 peer 同步。NUC 5008 只读实例及阿里云只读实例启动 tag-server 时必须传入 `--disable-sync`，由后端拒绝同步导出、导入、主动同步和通知接口。私人主实例由独立的 `[features].tag_peer_sync` 布尔值控制，不从文件写权限、镜像 profile 或主机名推断。只读附加实例固定禁用同步。Tag Server 的功能契约见 `/data/project/tag-all/specs/016-private-peer-discovery/`。

## 验收

- 本机渲染 `home` 配置：私人 `tag-server` 命令无该参数，`tag-server-readonly` 命令有该参数。
- 本机渲染 `aliyun` 配置：唯一的只读 `tag-server` 命令有该参数。
- Tag Server 禁用同步时，`/v1/sync/*` 与 `/tag-api/v1/sync/*` 返回 403，普通位置读取仍可用。
- 生产验收需分别核对 NUC 5006、5008 与阿里云实例；仅渲染测试通过不能宣称已部署。
