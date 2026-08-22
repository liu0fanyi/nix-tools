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
  # aliyun 地址/用户/端口可经环境变量覆盖（见下方注释）
  systemd.user.services.autossh-tunnel = {
    Unit = {
      Description = "autossh reverse tunnel nuc:22 -> aliyun:2222";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };
    Service = {
      # 覆盖项（在 nuc 上 export 或改这里）：
      #   TUNNEL_ALIYUN_HOST=47.93.153.102
      #   TUNNEL_ALIYUN_USER=root
      #   TUNNEL_REMOTE_PORT=2222
      ExecStart = "${pkgs.autossh}/bin/autossh -M 0 -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -R \${TUNNEL_REMOTE_PORT:-2222}:localhost:22 \${TUNNEL_ALIYUN_USER:-root}@\${TUNNEL_ALIYUN_HOST:-47.93.153.102}";
      Restart = "on-failure";
      RestartSec = "5";
      # 需要能读到 nuc 的 ssh key（~/.ssh/）与 known_hosts
      Environment = [ "HOME=%h" ];
    };
    Install = { };
  };

  # 说明：如需开机自启（常驻隧道），执行
  #   systemctl --user enable autossh-tunnel
  # 需要 root 权限写 aliyun 的 2222 端口时（普通用户绑 <1024 才需），
  # 2222 > 1024 无需 root，aliyun 侧 sshd 默认即可。
}
