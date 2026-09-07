{ pkgs, lib, config, ... }:
let
  cfg = config.features.fcitx5;
  rimeDefaultConfig = pkgs.writeText "rime-default.custom.yaml" ''
    patch:
      __include: rime_ice_suggestion:/
      schema_list:
        - schema: rime_ice
      "key_binder/bindings/+":
        - { accept: comma, send: Page_Up, when: paging }
        - { accept: period, send: Page_Down, when: has_menu }
  '';
  rimeDeploy = pkgs.writeShellScript "rime-deploy" ''
    set -eu

    rime_dir="''${XDG_DATA_HOME:-$HOME/.local/share}/fcitx5/rime"
    config_file="$rime_dir/default.custom.yaml"
    config_tmp="$rime_dir/.default.custom.yaml.tmp"

    ${pkgs.coreutils}/bin/install -d -m 700 "$rime_dir"
    if [ -L "$config_file" ] \
      || [ ! -f "$config_file" ] \
      || ! ${pkgs.diffutils}/bin/cmp -s ${rimeDefaultConfig} "$config_file"; then
      ${pkgs.coreutils}/bin/rm -f -- "$config_tmp"
      ${pkgs.coreutils}/bin/install -m 600 ${rimeDefaultConfig} "$config_tmp"
      ${pkgs.coreutils}/bin/mv -f -- "$config_tmp" "$config_file"
    fi

    ${pkgs.librime}/bin/rime_deployer \
      --build \
      "$rime_dir" \
      "${config.i18n.inputMethod.package}/share/rime-data" \
      "$rime_dir/build"
  '';
in
{
  options.features.fcitx5 = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Enable Fcitx5 input method with Rime engine";
    };
  };

  config = lib.mkIf cfg.enable {
    i18n.inputMethod = {
      enable = true;
      type = "fcitx5";
      fcitx5.addons = with pkgs; [
        fcitx5-rime
        fcitx5-gtk
        qt6Packages.fcitx5-chinese-addons
        rime-data
        # 雾凇拼音大词库；版本随 flake.lock 中固定的 nixpkgs 版本锁定。
        rime-ice
      ];
    };

    # Essential environment variables for generic Linux
    home.sessionVariables = {
      # GTK_IM_MODULE = "fcitx";
      QT_IM_MODULE = "fcitx";
      XMODIFIERS = "@im=fcitx";
      SDL_IM_MODULE = "fcitx";
      GLFW_IM_MODULE = "ibus"; # GLFW doesn't support fcitx directly often
    };

    # fcitx5-rime 的运行时搜索路径不会包含 addons 合成目录。将雾凇拼音的
    # Lua 过滤器、OpenCC 配置和默认短语表放到用户 Rime 目录，避免主词表
    # 虽已启用但日期、金额、Emoji 等扩展持续报 module not found。
    home.file = {
      ".local/share/fcitx5/rime/lua".source =
        "${pkgs.rime-ice}/share/rime-data/lua";
      ".local/share/fcitx5/rime/opencc".source =
        "${pkgs.rime-ice}/share/rime-data/opencc";
      ".local/share/fcitx5/rime/custom_phrase.txt".source =
        "${pkgs.rime-ice}/share/rime-data/custom_phrase.txt";
    };

    # Fcitx5-Rime 依靠配置文件时间判断是否需要重新部署；Nix store 文件的
    # 固定时间戳会让它错误复用旧 build。服务启动前将配置物化为普通文件，
    # 再使用当前 addons 合成目录进行增量部署。
    systemd.user.services.fcitx5-daemon.Service.ExecStartPre = [ rimeDeploy ];

    # i18n.inputMethod 已生成 fcitx5-daemon.service；屏蔽包内 XDG autostart，
    # 避免登录时两个实例争抢 org.fcitx.Fcitx5，导致新配置无法加载。
    xdg.configFile."autostart/org.fcitx.Fcitx5.desktop".text = ''
      [Desktop Entry]
      Hidden=true
    '';
  };
}
