# Todo（nix-tools）

## 💤 电源与合盖策略

- [x] suspend-then-hibernate：合盖先挂起，1h 后自动休眠到磁盘
      （远程 homebox 使用 16 GiB swapfile；需保持 swap ≥ 内存）
- [x] 挂起时 DPMS off（swayidle before-sleep 配合 wlopm，恢复后重新打开）
- [x] 合盖行为集中可选：修改 `nixos/configuration.nix` 的 `lidSwitchAction`
      （支持 lock / suspend / hibernate / suspend-then-hibernate；外接显示器默认 ignore）

## 其他候选

- [x] mihomo 分流规则细化（GeoSite/GeoIP 国内直连 + 国外代理）
- [x] Rime 词库同步（加密快照 + `scripts/sync-rime-userdb.sh` 远程恢复）
- [x] waybar 更多模块（温度、hwmon 风扇转速、MPRIS 媒体控制）
