{ pkgs, lib, config, ... }:
let
  cfg = config.features.anydesk;
in
{
  options.features.anydesk = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable AnyDesk remote desktop client (unfree)";
    };
  };

  config = lib.mkIf cfg.enable {
    # nixpkgs 打包的是 AnyDesk 官方 Linux 二进制（unfree，8.0.4），
    # 依赖 allowUnfree：NixOS 侧见 nixos/configuration.nix，
    # standalone 侧见 home-manager/home.nix（两侧都已开启）。
    #
    # 说明：
    # - 客户端主程序即 anydesk。上游 Linux 包内的 systemd 单元
    #   （.../lib/systemd/system/anydesk.service，ExecStart="anydesk --service"，
    #   User=root）用于无人值守/被控访问，属系统服务，需 root 权限，
    #   因此不在这里声明；需要时手动 `sudo anydesk --service` 或另行声明系统单元。
    # - 上游 wrapper 固定 GDK_BACKEND=x11：Niri 上由 xwayland-satellite 按需
    #   起 XWayland 并导出 DISPLAY，从桌面启动器/终端启动即可正常出窗口。
    # - 首次启动会创建 ~/.anydesk（配置与 AnyDesk ID 都在这里，属运行时状态，
    #   不进 Nix store，也不随 rebuild 删除）。
    home.packages = [ pkgs.anydesk ];
  };
}
