# 数位笔"侧键+划动=滚轮"手势守护进程的 systemd **系统**服务。
#
# 为什么是系统服务而不是 home-manager 用户服务（2026-09-17 实测结论）：
#   1. /dev/uinput 是 0660 root:uinput，进程必须带上 uinput 组；
#   2. 本机启用了 linger（nixos/configuration.nix 创建 /var/lib/systemd/linger/liou），
#      `user@1000.service` **不随注销停止**，会一直持有首次启动时的组快照，
#      因此"重新登录"并不能让用户服务看到新加入的组；
#   3. 用户服务上也无法用 SupplementaryGroups 补救——systemd --user 没有
#      CAP_SETGID，setgroups() 失败并以 216/GROUP 退出（systemd issue #15659）。
#   4. 系统服务由 PID 1 启动，具备 CAP_SETGID，SupplementaryGroups 正常工作，
#      且完全不依赖登录会话与组快照：一次 switch 立即生效，无需注销。
#
# 读 /dev/input/event* 需要 input 组，写 /dev/uinput 需要 uinput 组，两者都在
# SupplementaryGroups 中声明，不依赖用户的附加组。
{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.features.penScroll;

  # 源码在仓库 scripts/pen-scroll.py。
  # 必须用 writePython3Bin（而非 writePython3）：后者产出单个可执行文件，
  # 无法安装进 profile；Bin 变体产出标准 $out/bin/ 目录。两者都在构建期做
  # flake8 校验并保证运行期具备 evdev 依赖。
  penScroll = pkgs.writers.writePython3Bin "pen-scroll" {
    libraries = [ pkgs.python3Packages.evdev ];
    flakeIgnore = [ "E501" ];
  } (builtins.readFile ../../scripts/pen-scroll.py);
in
{
  options.features.penScroll = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable the pen barrel-button scroll gesture daemon";
    };

    pixelsPerTick = lib.mkOption {
      type = lib.types.nullOr lib.types.numbers.positive;
      default = null;
      description = ''
        Axis units per wheel notch. Null derives it from the tablet's ABS_X
        resolution (recommended); set a number to override.
      '';
    };

    deadzonePixels = lib.mkOption {
      type = lib.types.numbers.positive;
      default = 20.0;
      description = "Pen travel in axis units before a drag becomes a scroll.";
    };

    natural = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Dragging the pen down scrolls towards earlier content.";
    };

    horizontal = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Scroll horizontally (REL_HWHEEL) instead of vertically.";
    };

    barrelButton = lib.mkOption {
      type = lib.types.enum [ "lower" "upper" ];
      default = "lower";
      description = "Which pen barrel button starts a scroll gesture.";
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "liou";
      description = "User the daemon runs as (needs input + uinput groups).";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.pen-scroll = {
      description = "Pen barrel-button scroll gesture (evdev -> uinput)";
      # 图形会话存在与否都不影响：守护进程只依赖 evdev/uinput，能独立于
      # niri 启动，且比图形会话更早可用。
      wantedBy = [ "multi-user.target" ];

      serviceConfig = {
        Type = "simple";
        ExecStart = "${penScroll}/bin/pen-scroll";
        User = cfg.user;
        # 关键：由 PID 1 设置附加组，绕开用户会话/linger 的陈旧组快照。
        SupplementaryGroups = [ "input" "uinput" ];

        Environment = [
          "PEN_SCROLL_DEADZONE_PIXELS=${toString cfg.deadzonePixels}"
          "PEN_SCROLL_NATURAL=${if cfg.natural then "1" else "0"}"
          "PEN_SCROLL_HORIZONTAL=${if cfg.horizontal then "1" else "0"}"
          "PEN_SCROLL_BARREL=${cfg.barrelButton}"
        ]
        ++ lib.optional (cfg.pixelsPerTick != null) (
          "PEN_SCROLL_UNITS_PER_TICK=${toString cfg.pixelsPerTick}"
        );

        # 平板热插拔：脚本自身会等待设备/权限并重试，这里只兜底真崩溃。
        Restart = "on-failure";
        RestartSec = "5";
      };
    };
  };
}
