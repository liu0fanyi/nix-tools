{ config, pkgs, ... }:
{
  # sakura 终端（X11 兼容，适用于 VMware 等无 GPU 环境）
  home.packages = with pkgs; [
    sakura
  ];

  # sakura 配置文件 ~/.config/sakura/sakura.conf
  home.file.".config/sakura/sakura.conf".text = ''
    [sakura]
    font=BigBlueTermPlus Nerd Font Mono 12
    colorset1_back=rgb(40,40,40)
    colorset1_fore=rgb(235,219,178)
    scroll_lines=10000
    audible_bell=No
    visible_bell=No
    blinking_cursor=No
    tabs_on_bottom=No
    less_questions=Yes
    scrollbar=false
  '';

  # 自定义启动器：Sakura + Zellij（点击直接启动终端复用器）
  xdg.desktopEntries.sakura-zellij = {
    name = "Sakura Zellij";
    comment = "Terminal with Zellij";
    exec = "sakura -e zellij";
    icon = "utilities-terminal";
    terminal = false;
    categories = [ "System" "TerminalEmulator" ];
  };
}
