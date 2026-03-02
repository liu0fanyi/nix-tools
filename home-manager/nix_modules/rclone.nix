{ pkgs, ... }:
{
  home.packages = [ pkgs.rclone ];

  systemd.user.services.rclone-mount = {
    Unit = {
      Description = "Rclone mount for R2 storage";
      After = [ "network-online.target" ];
      Wants = [ "network-online.target" ];
    };

    Service = {
      Type = "simple";
      # 注意：挂载目录 ~/dufs-lan/s3-data 如果不存在，rclone 可能会报错。
      # 建议使用绝对路径或在启动前创建。
      # 关键：如果上次挂载没卸载干净会导致“传输端点尚未连接”
      # 使用 - 前缀忽略失败（如果目录没被挂载过）
      ExecStartPre = [
        "-/usr/bin/fusermount3 -uz %h/dufs-lan/s3-data"
        "/bin/mkdir -p %h/dufs-lan/s3-data"
      ];
      ExecStart = ''
        %h/.nix-profile/bin/rclone mount r2:repo %h/dufs-lan/s3-data \
          --vfs-cache-mode full \
          --vfs-cache-max-age 24h \
          --vfs-cache-max-size 10G \
          --vfs-read-chunk-size 128M \
          --log-level INFO
      '';
      ExecStop = "/usr/bin/fusermount3 -uz %h/dufs-lan/s3-data";
      Restart = "on-failure";
      RestartSec = "10s";
      # 显式包含宿主机常用路径，确保能找到带 SUID 权限的 fusermount3
      Environment = [ "PATH=/usr/bin:/bin:/usr/sbin:/sbin:%h/.nix-profile/bin" ];
    };

    Install = {
      WantedBy = [ "default.target" ];
    };
  };
}
