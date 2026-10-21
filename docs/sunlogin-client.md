# 向日葵远程控制

仅 `liu-bigpc` 安装向日葵个人版 Linux x86_64 客户端 15.2.0.63062，
来源为[向日葵官网](https://sunlogin.oray.com/download/linux)的 UOS 图形版。
官方版本接口为 `https://client-webapi.oray.com/softwares/SL_X_LINUX_UOS_AMD?x64=1&versiontype=stable`。
安装包 SHA256 为 `f0cb0295795a0e5c32ddcfd569aa668c2a1d66850b70a3929c1840cfdb5a6347`。

`packages/sunlogin.nix` 通过 FHS 环境提供官方程序所需的绝对路径与依赖，
复用锁定的 `nixpkgs-gtkmm2` 提供已从 unstable 移除的 GConf。
`nixos/modules/sunlogin.nix` 管理客户端所需的 `sunlogin.service`；不运行 `.deb` 的安装脚本。
账号和配置存于 `/var/lib/sunlogin/orayconfig.conf`，日志存于 `/var/log/sunlogin`，不进入 Nix store。

## 应用与使用

Agent 只构建验证配置，用户在普通终端手动执行：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```

完成后从桌面启动器打开“向日葵远程控制”，或运行 `sunloginclient`，自行登录账号。
本次用途是从这台 PC 控制其他电脑：输入远端设备识别码与验证码，或选择账号下的设备发起连接。
服务检查：

```bash
systemctl status sunlogin
journalctl -u sunlogin -b --no-pager -n 50
```

当前桌面为 Niri/Wayland，客户端以 X11 模式通过现有 XWayland 运行。
官方安装包面向 UOS；构建成功并不代表 Niri 桌面捕获与输入注入可用。
启动、登录、连接远端和被控桌面均需实机验证，不能把 XWayland 窗口显示当成被控支持。
本次不修改桌面会话或防火墙，不设置账号、访问密码或无人值守策略。

## 验证状态（2026-10-09）

完整 `liu-bigpc` system toplevel 和 Home Manager generation 构建通过，
Home Manager 非破坏性备份选项与系统服务 ExecStart、持久化目录规则已核对。
FHS 临时环境中的动态链接器检查通过，覆盖主客户端、桌面辅助进程、守护进程和 `libcef.so`；
检查没有启动远控应用或系统服务。
剩余实机安装步骤为用户手动 switch，然后启动登录并连接远端验收。
