{ config, pkgs, lib, ... }:

# autossh 反向隧道：让 nuc（家庭 NAT，无公网 IPv4）能被外网 SSH。
# nuc 主动连 aliyun VPS，建立反向隧道 aliyun:2222 → nuc:22。
# 外网访问：ssh -J root@47.93.153.102 -p 2222 liou@localhost
#
# 前提（一次性手动配置，不进 git）：
#   1. nuc 的公钥已加到 aliyun 的 root authorized_keys（免密连 aliyun）
#   2. aliyun 的 sshd 允许 root 登录（公钥）
{
  # autossh：SSH 隧道守护（断线自动重连）
  home.packages = with pkgs; [
    autossh
  ];

  # 反向隧道 user service。nuc 登录用户运行（不需要 root）。
  # -R 2222:localhost:22：aliyun 上开 2222，转发到 nuc 本机 22
  # -N 不执行远程命令；-M 0 关闭监控端口（新版 autossh 用 -o ServerAliveInterval 检测）
  systemd.user.services.autossh-tunnel = {
    Unit = {
      Description = "autossh reverse tunnel nuc:22 -> aliyun:2222";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };
    Service = {
      # 写死 aliyun 地址与端口（systemd 的 ExecStart 不支持 ${VAR:-default} 语法，
      # 那是 shell 的；这里配置固定，无需环境变量覆盖）
      ExecStart = "${pkgs.autossh}/bin/autossh -M 0 -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -R 2222:localhost:22 root@47.93.153.102";
      Restart = "on-failure";
      RestartSec = "5";
      Environment = [ "HOME=%h" ];
    };
    Install.WantedBy = [ "default.target" ];
  };

  # standalone Home Manager 会声明式 enable；若需要用户未登录时也常驻，
  # 宿主机还需一次性执行：loginctl enable-linger liou。
  # 2222 > 1024，aliyun 侧普通用户即可绑定，无需 root。
}
