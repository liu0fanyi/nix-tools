{ config, pkgs, lib, inputs, isNixOS ? false, osConfig ? null, ... }:

let
  cfg = config.features.niri;
  isNuc = isNixOS && osConfig != null && osConfig.networking.hostName == "nuc";
  cpuTemperature = pkgs.writeShellScript "nuc-cpu-temperature" ''
    for device in /sys/class/hwmon/hwmon*; do
      [ "$(cat "$device/name" 2>/dev/null)" = coretemp ] || continue
      for label in "$device"/temp*_label; do
        [ "$(cat "$label" 2>/dev/null)" = "Package id 0" ] || continue
        value=$(cat "''${label%_label}_input" 2>/dev/null) || continue
        case "$value" in ""|*[!0-9]*) continue ;; esac
        [ "$value" -le 125000 ] || continue
        printf '{"text":" %s°C","tooltip":"CPU Package","class":"normal"}\n' "$((value / 1000))"
        exit 0
      done
    done
    printf '{"text":" N/A","tooltip":"CPU temperature unavailable"}\n'
  '';
  isLiuBigpc =
    isNixOS && osConfig != null && osConfig.networking.hostName == "liu-bigpc";
  nixGL = inputs.nix-gl.packages.${pkgs.stdenv.hostPlatform.system}.nixGLDefault;
  niriPackage = inputs.niri.packages.${pkgs.stdenv.hostPlatform.system}.niri;

  # Waybar 没有通用风扇模块；只在存在 hwmon fan*_input 时输出转速，
  # 没有风扇（或硬件不暴露转速）时保持空模块，不污染状态栏。
  fanScript = pkgs.writeShellScriptBin "waybar-fan" ''
    set -eu
    fan_input="$(find /sys/class/hwmon -type f -name 'fan*_input' -readable 2>/dev/null | sort | head -n 1)"
    if [ -z "$fan_input" ]; then
      printf '{"text":"","class":"unavailable"}\n'
      exit 0
    fi
    rpm="$(cat "$fan_input")"
    printf '{"text":"󰈐 %s RPM","tooltip":"风扇转速: %s RPM"}\n' "$rpm" "$rpm"
  '';

  # Mako 勿扰模式切换与 Waybar 状态输出。
  makoDndScript = pkgs.writeShellScriptBin "mako-dnd" ''
    set -eu
    makoctl=${lib.getExe' pkgs.mako "makoctl"}

    if [ "''${1:-status}" = "toggle" ]; then
      "$makoctl" mode -t do-not-disturb
      "$makoctl" dismiss --all
      ${pkgs.procps}/bin/pkill -RTMIN+8 waybar || true
      exit 0
    fi

    if "$makoctl" mode | ${pkgs.gnugrep}/bin/grep -Fxq do-not-disturb; then
      printf '{"text":"󰂛","class":"dnd","tooltip":"勿扰模式：已开启（点击恢复通知）"}\n'
    else
      printf '{"text":"󰂚","class":"enabled","tooltip":"通知：已开启（点击进入勿扰）"}\n'
    fi
  '';

  # 设备豆 Wi-Fi 音箱状态感知与推流切换脚本
  deviceBeanScript = pkgs.writeShellScriptBin "waybar-device-bean" ''
    export PATH="${lib.makeBinPath [ pkgs.iproute2 pkgs.iputils pkgs.libnotify pkgs.pipewire pkgs.wireplumber pkgs.procps pkgs.python3 ]}:$PATH"
    if [ -f /data/project/esp32-device-bean/scripts/waybar-device-bean.py ]; then
      exec ${pkgs.python3}/bin/python3 /data/project/esp32-device-bean/scripts/waybar-device-bean.py "$@"
    else
      printf '{"text":"","class":"offline"}\n'
      exit 0
    fi
  '';

  # 智能系统挂起守卫：检测是否有活跃的 Agent、构建任务或阻止锁；
  # 若有活跃工作或 Agent 运行中，立即取消休眠，保证屏幕熄灭节能的同时，后台任务不受任何中断。
  safeSuspendScript = pkgs.writeShellScriptBin "safe-idle-suspend" ''
    set -eu

    check_busy() {
      # 1. Antigravity IDE / Agent（只要主进程或任一组件存活，即视为处于工作会话，严禁休眠打断）
      if ${pkgs.procps}/bin/pgrep -f "antigravity" >/dev/null 2>&1; then
        echo "Antigravity Agent/IDE 正在运行"
        return 0
      fi

      # 2. 其它 Agent 与 CLI 工具进程
      for tool in "dsh" "specify" "claude" "aider" "open-interpreter" "codex"; do
        if ${pkgs.procps}/bin/pgrep -f "$tool" >/dev/null 2>&1; then
          echo "Agent 工具 $tool 运行中"
          return 0
        fi
      done

      # 3. 常见编译构建与部署任务
      for build_cmd in "cargo" "rustc" "buildah" "nix-build" "podman" "podman-remote" "just" "devenv"; do
        if ${pkgs.procps}/bin/pgrep -x "$build_cmd" >/dev/null 2>&1; then
          echo "构建/部署任务 $build_cmd 进行中"
          return 0
        fi
      done

      # nix-daemon 活跃构建子进程
      local nd_pids
      nd_pids=$(${pkgs.procps}/bin/pgrep -x "nix-daemon" 2>/dev/null || true)
      if [ -n "$nd_pids" ]; then
        for pid in $nd_pids; do
          local workers
          workers=$(${pkgs.procps}/bin/pgrep -P "$pid" 2>/dev/null || true)
          if [ -n "$workers" ]; then
            echo "nix-daemon 正在构建 (工作进程 PID: $workers)"
            return 0
          fi
        done
      fi

      # 4. 手动免休眠标记文件（Waybar 按钮切换）
      if [ -f "$HOME/.config/no-suspend" ]; then
        echo "存在手动免休眠标记 (~/.config/no-suspend)"
        return 0
      fi

      # 5. systemd-inhibit 阻止锁
      if ${pkgs.systemd}/bin/systemd-inhibit --list --no-legend 2>/dev/null | grep -E "block.*sleep|sleep.*block" >/dev/null 2>&1; then
        echo "系统存在活跃的 sleep 阻止锁 (systemd-inhibit)"
        return 0
      fi

      return 1
    }

    if reason=$(check_busy); then
      ${pkgs.util-linux}/bin/logger -t safe-idle-suspend "检测到活跃任务或 Agent ($reason)，取消系统休眠，保持屏幕熄灭节能。"
      exit 0
    fi

    ${pkgs.util-linux}/bin/logger -t safe-idle-suspend "系统空闲且无后台任务与 Agent，执行安全挂起。"
    ${pkgs.systemd}/bin/systemctl suspend
  '';

  screenshotEdit = pkgs.writeShellApplication {
    name = "screenshot-edit";
    runtimeInputs = with pkgs; [ coreutils grim slurp satty wl-clipboard util-linux ];
    text = ''
      # 防止重复快捷键同时启动多个选区/编辑器。
      exec 9>"$XDG_RUNTIME_DIR/screenshot-edit.lock"
      flock -n 9 || exit 0
      region=$(slurp) || exit 0
      image=$(mktemp --suffix=.png)
      trap 'rm -f "$image"' EXIT
      grim -g "$region" "$image"
      directory="$HOME/Pictures/Screenshots"
      mkdir -p "$directory"
      satty --filename "$image" \
        --copy-command wl-copy \
        --output-filename "$directory/Edited-$(date +%Y-%m-%d_%H-%M-%S-%N).png"
    '';
  };

  screenRecordAudio = pkgs.writeShellApplication {
    name = "screen-record-audio";
    runtimeInputs = with pkgs; [ python3 pulseaudio fuzzel libnotify systemd ];
    text = ''
      exec python3 ${../../scripts/screen-record-audio.py} "$@"
    '';
  };

  screenCut = import ../../packages/screen-cut.nix { inherit pkgs; };
  screenRecordEdit = pkgs.writeShellApplication {
    name = "screen-record-edit";
    text = ''
      exec ${screenCut}/bin/screen-cut "$@"
    '';
  };

  screenRecordFinished = pkgs.writeShellApplication {
    name = "screen-record-finished";
    runtimeInputs = with pkgs; [ coreutils libnotify python3 systemd ];
    text = ''
      ${screenRecordAudio}/bin/screen-record-audio cleanup || true
      if [[ "$SERVICE_RESULT" == success && -s "$SCREEN_RECORD_FILE" ]]; then
        uri=$(python3 -c 'import pathlib, sys; print(pathlib.Path(sys.argv[1]).as_uri(), end="")' "$SCREEN_RECORD_FILE")
        # Wayland 剪贴板需要存活的 owner。独立单元避免录屏单元收尾时杀掉 wl-copy。
        # wl-copy 默认 fork；Type=forking 等待取得剪贴板后才报告启动成功。
        if systemd-run --user --quiet --collect --service-type=forking \
          --unit="nix-tools-recording-clipboard-$(date +%s%N)" \
          --setenv="WAYLAND_DISPLAY=$WAYLAND_DISPLAY" \
          --setenv="XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" \
          ${pkgs.wl-clipboard}/bin/wl-copy --type text/uri-list "$uri"$'\r\n'; then
          notify-send --replace-id="$SCREEN_RECORD_NOTIFICATION" --expire-time=5000 \
            "录屏已保存并复制" "支持文件粘贴的应用中按 Ctrl+V。$SCREEN_RECORD_FILE" || true
        else
          notify-send --replace-id="$SCREEN_RECORD_NOTIFICATION" --expire-time=5000 \
            "录屏已保存，复制失败" "$SCREEN_RECORD_FILE" || true
        fi
      else
        notify-send --replace-id="$SCREEN_RECORD_NOTIFICATION" --urgency=critical \
          "录屏失败或中断" "文件可能不完整。用 journalctl --user -u nix-tools-screen-record 查看原因。" || true
      fi
      if [[ "$SERVICE_RESULT" == success && -s "$SCREEN_RECORD_FILE" && "$SCREEN_RECORD_EDIT" == 1 ]]; then
        if ! systemd-run --user --quiet --collect --service-type=exec \
          --setenv="WAYLAND_DISPLAY=$WAYLAND_DISPLAY" \
          --setenv="XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" \
          --setenv="DISPLAY=''${DISPLAY:-}" \
          ${screenRecordEdit}/bin/screen-record-edit "$SCREEN_RECORD_FILE"; then
          notify-send "无法打开录屏编辑器" "$SCREEN_RECORD_FILE" || true
        fi
      fi
    '';
  };

  screenRecordToggle = pkgs.writeShellApplication {
    name = "screen-record-toggle";
    runtimeInputs = with pkgs; [ coreutils slurp systemd libnotify util-linux ];
    text = ''
      # 只控制自己的 transient unit；不按进程名终止其他录屏。
      exec 9>"$XDG_RUNTIME_DIR/screen-record-toggle.lock"
      flock -n 9 || exit 0
      unit=nix-tools-screen-record.service
      state=$(systemctl --user show "$unit" --property=ActiveState --value 2>/dev/null) || state=inactive
      case "$state" in
        active|activating|reloading)
          systemctl --user stop "$unit"
          exit 0
          ;;
        deactivating) exit 0 ;;
      esac
      edit=0
      case "''${1:-}" in
        "") ;;
        --edit) edit=1 ;;
        *) exit 2 ;;
      esac
      region=$(slurp) || exit 0
      audio_source=$(${screenRecordAudio}/bin/screen-record-audio prepare) || exit 1
      # 启动失败也清理；成功后由录屏单元 ExecStopPost 负责收尾。
      trap '${screenRecordAudio}/bin/screen-record-audio cleanup || true' EXIT
      audio_options=()
      if [[ -n "$audio_source" ]]; then
        audio_options=("--audio=$audio_source" --audio-backend=pulse \
          --audio-codec aac --audio-codec-param b=128000 --sample-rate 48000)
      fi
      directory="$HOME/Videos/Screencasts"
      mkdir -p "$directory"
      file="$directory/Recording-$(date +%Y-%m-%d_%H-%M-%S-%N).mp4"
      notification=$(notify-send --print-id --expire-time=0 "正在录屏" \
        "再次按 Ctrl+Shift+Fn+I 停止；保存为 $file") || notification=0
      if ! systemd-run --user --quiet --collect --unit="$unit" \
        --service-type=exec --property=KillSignal=SIGINT --property=TimeoutStopSec=30s \
        --property="ExecStopPost=${screenRecordFinished}/bin/screen-record-finished" \
        --setenv="WAYLAND_DISPLAY=$WAYLAND_DISPLAY" \
        --setenv="XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" \
        --setenv="DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus" \
        --setenv="SCREEN_RECORD_FILE=$file" \
        --setenv="SCREEN_RECORD_NOTIFICATION=$notification" \
        --setenv="SCREEN_RECORD_EDIT=$edit" \
        --setenv="DISPLAY=''${DISPLAY:-}" \
        ${pkgs.systemd}/bin/systemd-inhibit --what=idle:sleep --mode=block \
        --why="快捷键录屏" \
        ${pkgs.wf-recorder}/bin/wf-recorder --geometry "$region" --file "$file" \
        --framerate 24 --codec libx264 --pixel-format yuv420p \
        --codec-param preset=veryfast --codec-param crf=24 \
        --codec-param maxrate=4000000 --codec-param bufsize=8000000 \
        --codec-param g=48 \
        --filter "pad=ceil(iw/2)*2:ceil(ih/2)*2" "''${audio_options[@]}"; then
        notify-send --replace-id="$notification" --urgency=critical \
          "无法启动录屏" "用 journalctl --user -u nix-tools-screen-record 查看原因。" || true
        exit 1
      fi
      trap - EXIT
    '';
  };

  # Wrapper script to run niri-session with necessary environment variables
  niri-session-wrapped = pkgs.writeShellScriptBin "niri-session-wrapped" ''
    export GBM_BACKENDS_PATH="${pkgs.mesa}/lib/gbm"
    exec ${nixGL}/bin/nixGL ${niriPackage}/bin/niri-session "$@"
  '';

  # 官方默认配置（完整键位/音量/媒体/亮度键/截图等基础）+ 本机追加段。
  # 注：官方默认已含 XF86 音量/媒体/亮度键绑定，无需重复。
  # binds 节点只能出现一次，自定义键位注入官方 binds 块开头。
  # 用户只使用 1-6 工作区，移除官方默认的 Mod+7/8/9 绑定（避免切出动态工作区）。
  # 移除官方默认的 numlock 启动项（NumLock 状态应完全由键盘控制）。
  niriConfig =
    builtins.replaceStrings
      (
        [
          "binds {"
          "    Mod+7 { focus-workspace 7; }\n    Mod+8 { focus-workspace 8; }\n    Mod+9 { focus-workspace 9; }\n"
          "        // Enable numlock on startup, omitting this setting disables it.\n        numlock\n"
        ]
        ++ lib.optional isLiuBigpc "input {"
      )
      (
        [
          ''
            binds {
                // ===== homebox 追加键位 =====
                // WiFi 选择（fuzzel 界面）
                Mod+N { spawn "networkmanager_dmenu" "--dmenu" "fuzzel"; }
                // 一键切换 Mako 勿扰模式，并清除当前可见通知。
                Mod+Shift+N { spawn "mako-dnd" "toggle"; }
            ${lib.optionalString isLiuBigpc ''
                // 截图沿用 Fn+I (Print)，录屏用 Fn+O (Scroll_Lock)；Shift统一表示结束后编辑。
                Shift+Print hotkey-overlay-title="截图后编辑 (Satty)" { spawn "${screenshotEdit}/bin/screenshot-edit"; }
                Scroll_Lock cooldown-ms=1000 hotkey-overlay-title="开始/停止录屏" { spawn "${screenRecordToggle}/bin/screen-record-toggle"; }
                Shift+Scroll_Lock cooldown-ms=1000 hotkey-overlay-title="录屏后编辑" { spawn "${screenRecordToggle}/bin/screen-record-toggle" "--edit"; }
            ''}
          ''
          ""
          ""
        ]
        ++ lib.optional isLiuBigpc ''
          input {
              // 数位板跟随当前获得焦点的输出，避免绝对坐标铺满双屏。
              tablet {
                  map-to-focused-output
              }
        ''
      )
      (builtins.readFile ./default-config.kdl)
    + lib.optionalString isLiuBigpc ''
      // ===== liu-bigpc 双屏输出 =====

      // 左侧 Philips 竖屏，右侧 Dell 主屏保持原生分辨率并放大界面。
      // 使用显示器 EDID 名称而非接口名，避免换接口或多 GPU 时名称漂移。
      output "Dell Inc. DELL U2520D B465923" {
          mode "2560x1440@59.951"
          scale ${toString cfg.primaryOutputScale}
          transform "normal"
          position x=1080 y=0
      }

      output "Philips Consumer Electronics Company Philips 241E AU51048025954" {
          mode "1920x1080@60.000"
          scale 1
          transform "90"
          position x=0 y=0
      }

      // 同一块 Philips 经当前 HDMI 转接器热插拔后会暴露这个 EDID 名称。
      output "AlgolTek, Inc. 0x0001 0x434E3031" {
          mode "1920x1080@60.000"
          scale 1
          transform "90"
          position x=0 y=0
      }

      // NVIDIA 显卡从睡眠恢复时，强制重新初始化所有显示连接器，避免黑屏/掉信号
      debug {
          force-disable-connectors-on-resume
      }
    ''
    + ''
      // ===== homebox 追加（参考官方 wiki 与社区配置）=====

      // 命名工作区：仅 1-6（waybar 按数字显示，niri 0.1.6+ 声明式）
      workspace "1"
      workspace "2"
      workspace "3"
      workspace "4"
      workspace "5"
      workspace "6"

      // 鼠标光标主题（Nordzy，避免 waybar/niri 的 cursor theme 警告）
      cursor {
          xcursor-theme "Nordzy-cursors"
          xcursor-size 24
      }

      // 通知、壁纸（纯色）
      spawn-at-startup "mako"
      spawn-at-startup "swaybg" "-c" "#1e1e2e"
      // 剪贴板历史（cliphist，配合 fuzzel 可搜索历史）
      spawn-sh-at-startup "wl-paste --watch cliphist store"
      // 空闲自动锁屏、DPMS 熄屏与智能挂起守卫。
      //
      // 1. 10 分钟（600秒）：锁屏（swaylock -f）并由 niri 关闭显示器 DPMS 输出。
      //    有输入时 resume 触发 niri power-on-monitors 恢复显示。
      // 2. 60 分钟（3600秒）：执行 safe-idle-suspend 守卫：
      //    - 若检测到 Agent 活跃（Antigravity、dsh、claude 等）、构建部署任务或阻止锁，
      //      立即取消挂起，屏幕保持熄灭节能但主机全速工作；
      //    - 只有当无任何 Agent 与任务、且系统真正空闲时，才安全调用 systemctl suspend；
      // 3. 休眠唤醒与显示恢复联动：
      //    - swayidle 配置 after-resume 钩子：当系统唤醒时立即通知 niri 重新点亮屏幕；
      //    - 配合 niri 的 force-disable-connectors-on-resume 与 s2idle 供电，彻底杜绝唤醒黑屏与死锁。
      spawn-sh-at-startup "swayidle -w timeout 600 'swaylock -f; niri msg action power-off-monitors' resume 'niri msg action power-on-monitors' timeout 3600 '${safeSuspendScript}/bin/safe-idle-suspend' after-resume 'niri msg action power-on-monitors' before-sleep 'swaylock -f'"
    '';
in
{
  options.features.niri = {
    primaryOutputScale = lib.mkOption {
      type = lib.types.float;
      default = if isLiuBigpc then 1.5 else 1.0;
      description = "Scale factor shared by the primary Niri output and XWayland application wrappers";
    };

    enable = lib.mkOption {
      type = lib.types.bool;
      # 仅在 NixOS 默认启用（非 NixOS 分支需要 nixGL，其求值含 impure
      # builtins.currentTime，会导致 standalone 的 home-manager switch 失败）
      default = config.features.full.enable && isNixOS;
      description = "Enable Niri window manager with NixGL support";
    };
  };

  config = lib.mkIf cfg.enable {
    # NixOS 上由系统模块 programs.niri 提供 niri 包与登录会话，
    # home 这里只负责配置文件；非 NixOS 才装包和 nixGL 包装。
    home.packages =
      lib.optionals isNixOS [
        fanScript
        makoDndScript
        safeSuspendScript
        # Wayland 图形化显示器布局、缩放与旋转工具（Niri 支持其输出协议）。
        pkgs.wdisplays
        # Niri starts this on demand and exports DISPLAY for X11-only apps
        # such as the official Linux WeChat client.
        pkgs.xwayland-satellite
      ]
      ++ lib.optionals isLiuBigpc [ pkgs.satty screenshotEdit pkgs.wf-recorder screenRecordToggle screenRecordAudio screenRecordEdit ]
      ++ lib.optionals (pkgs.stdenv.hostPlatform.system == "x86_64-linux") [ screenCut ]
      ++ lib.optionals (!isNixOS) [
        niriPackage
        niri-session-wrapped
      ];

    # 配置 = 官方默认（全部键位）+ 追加段
    xdg.configFile."niri/config.kdl".text = niriConfig;

    # networkmanager-dmenu 配置（Mod+N WiFi 选择；fuzzel + alacritty）
    xdg.configFile."networkmanager-dmenu/config.ini" = lib.mkIf isNixOS {
      text = ''
        [dmenu]
        dmenu_command = fuzzel
        prompt = Networks

        [editor]
        terminal = alacritty
      '';
    };

    # Waybar 状态栏配置（参考 0xNiri/社区：图标化 + 数字工作区）
    xdg.configFile."waybar/config.jsonc" = lib.mkIf isNixOS {
      text = ''
        {
          "layer": "top",
          "position": "top",
          "height": 30,
          "spacing": 8,
          "modules-left": ["niri/workspaces"],
          "modules-center": ["clock"],
          "modules-right": ["idle_inhibitor", ${lib.optionalString isLiuBigpc ''"custom/screen-record", ''}"custom/mako-dnd", "${if isNuc then "custom/cpu-temperature" else "temperature"}", "custom/fan", "mpris", "pulseaudio", ${lib.optionalString isLiuBigpc ''"custom/device-bean", ''}${lib.optionalString isLiuBigpc ''"bluetooth", ''}"network", "cpu", "memory", "battery", "tray"],
          "idle_inhibitor": {
            "format": "{icon}",
            "format-icons": {
              "activated": "󰅶",
              "deactivated": "󰾪"
            },
            "tooltip": true,
            "tooltip-format-activated": "防休眠已激活 (系统保持清醒)",
            "tooltip-format-deactivated": "防休眠已关闭 (遵循空闲策略)"
          },
          "custom/cpu-temperature": {
            "exec": "${cpuTemperature}",
            "return-type": "json",
            "interval": 5
          },

          "niri/workspaces": {
            "format": "{name}",
            "tooltip": false
          },
          "clock": {
            "format": "󰥔 {:%H:%M  %m-%d}",
            "tooltip-format": "<tt><small>{calendar}</small></tt>",
            "interval": 60
          },
          "cpu": {
            "format": " {usage}%",
            "tooltip": true,
            "tooltip-format": "负载: {load}",
            "interval": 5
          },
          "memory": {
            "format": "󰍛 {percentage}%",
            "tooltip": true,
            "tooltip-format": "已用: {used}\n总量: {total}",
            "interval": 10
          },
          "temperature": {
            "thermal-zone": 0,
            "format": " {temperatureC}°C",
            "format-critical": " {temperatureC}°C",
            "critical-threshold": 80,
            "tooltip-format": "温度: {temperatureC}°C",
            "interval": 5
          },
          "custom/fan": {
            "exec": "${fanScript}/bin/waybar-fan",
            "return-type": "json",
            "interval": 5,
            "format": "{}"
          },
          ${lib.optionalString isLiuBigpc ''
          "custom/screen-record": {
            "exec": "${screenRecordAudio}/bin/screen-record-audio status",
            "return-type": "json",
            "format": "{}",
            "interval": 2,
            "on-click": "${screenRecordAudio}/bin/screen-record-audio choose",
            "on-click-right": "${screenRecordToggle}/bin/screen-record-toggle"
          },
          ''}
          "custom/mako-dnd": {
            "exec": "${makoDndScript}/bin/mako-dnd status",
            "return-type": "json",
            "format": "{}",
            "interval": 5,
            "signal": 8,
            "on-click": "${makoDndScript}/bin/mako-dnd toggle"
          },
          "custom/device-bean": {
            "exec": "${deviceBeanScript}/bin/waybar-device-bean status",
            "return-type": "json",
            "format": "{}",
            "interval": 3,
            "signal": 9,
            "on-click": "${deviceBeanScript}/bin/waybar-device-bean toggle"
          },
          "mpris": {
            "format": "{player_icon} {dynamic}",
            "format-paused": "⏸ {dynamic}",
            "format-stopped": "",
            "player-icons": {
              "default": "▶",
              "firefox": "",
              "zen": ""
            },
            "status-icons": {
              "playing": "▶",
              "paused": "⏸"
            },
            "tooltip-format": "{player}: {title} — {artist}",
            "max-length": 48,
            "interval": 2
          },
          ${lib.optionalString isLiuBigpc ''
          "bluetooth": {
            "format": "󰂯",
            "format-disabled": "󰂲",
            "format-off": "󰂲",
            "format-connected": "󰂱 {num_connections}",
            "tooltip-format": "蓝牙：{status}\n点击管理设备",
            "tooltip-format-connected": "蓝牙：{status}\n{device_enumerate}",
            "tooltip-format-enumerate-connected": "{device_alias}",
            "on-click": "${pkgs.blueman}/bin/blueman-manager"
          },
          ''}
          "network": {
            "format-wifi": "󰤨",
            "format-ethernet": "󰈀",
            "format-disconnected": "󰤮",
            "tooltip": true,
            "tooltip-format": "{ifname}\n{essid} 信号 {signalStrength}%\nIP: {ipaddr}",
            "interval": 15
          },
          "battery": {
            "format": "{icon} {capacity}%",
            "format-charging": "󰂄 {capacity}%",
            "format-icons": ["", "", "", "", ""],
            "interval": 30
          },
          "pulseaudio": {
            "format": "{icon} {volume}%",
            "format-muted": "󰝟",
            "format-icons": ["󰕿", "󰖀", "󰕾"],
            "on-click": "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle",
            "tooltip-format": "{desc}"
          },
          "tray": { "spacing": 8 }
        }
      '';
    };
    xdg.configFile."waybar/style.css" = lib.mkIf isNixOS {
      text = ''
        * {
          font-family: "BigBlueTermPlus Nerd Font Mono";
          font-size: 13px;
          border: none;
          border-radius: 0;
          min-height: 0;
        }
        window#waybar {
          background: rgba(30, 30, 46, 0.9);
          color: #ebdbb2;
        }
        /* 工作区按钮：数字居中，激活高亮 */
        #workspaces button {
          padding: 0 7px;
          margin: 3px 1px;
          color: #928374;
          background: #282828;
          border-radius: 4px;
        }
        #workspaces button.active {
          color: #1d2021;
          background: #ebdbb2;
        }
        #workspaces button:hover {
          color: #ebdbb2;
          background: #3c3836;
        }
        #clock, #tray, #cpu, #memory, #temperature, #custom-fan, #custom-mako-dnd, #custom-device-bean, #custom-screen-record, #idle_inhibitor, #mpris, #network, #battery, #pulseaudio, #bluetooth {
          padding: 0 8px;
        }
        #custom-screen-record.idle { color: #83a598; }
        #custom-screen-record.recording { color: #fb4934; }
        #idle_inhibitor.activated { color: #fabd2f; }
        #custom-fan.unavailable { padding: 0; }
        #custom-mako-dnd.enabled { color: #b8bb26; }
        #custom-mako-dnd.dnd { color: #fb4934; }
        #custom-device-bean.offline { color: #928374; }
        #custom-device-bean.ready { color: #83a598; }
        #custom-device-bean.streaming { color: #b8bb26; }
        #battery.charging { color: #b8bb26; }
        #battery.warning { color: #fb4934; }
        #pulseaudio.muted { color: #fb4934; }
        #network.disconnected { color: #928374; }
        #bluetooth.off, #bluetooth.disabled { color: #928374; }
        #bluetooth.connected { color: #b8bb26; }
      '';
    };
    
    # Create the custom .desktop file in the user's profile
    # (NixOS 的 niri 系统模块已提供 session 文件，这里仅非 NixOS 需要)
    home.file.".local/share/wayland-sessions/niri.desktop" = lib.mkIf (!isNixOS) {
      text = ''
        [Desktop Entry]
        Name=Niri (NixGL)
        Comment=Niri Window Manager with NixGL
        Exec=${niri-session-wrapped}/bin/niri-session-wrapped
        Type=Application
        DesktopNames=niri
      '';
    };

    # DeepSeek Harness Web GUI 快捷启动。
    # 生成 home-path/share/applications/dsh-web.desktop（NixOS 集成下为
    # ~/.local/state/home-manager 的 profile 内），fuzzel（Mod+D）自动索引
    # 该目录，输入 "dsh" 即可启动。
    # Exec 调用 dsh-web-toggle：未运行则 start，已运行则 restart，
    # 完成后 notify-send 弹 toast（见 home.nix 的 systemd.user.services.dsh-web
    # 与 home.file.".local/bin/dsh-web-toggle"）。
    xdg.desktopEntries.dsh-web = {
      name = "DSH Web";
      comment = "DeepSeek Harness Web GUI";
      exec = "/home/liou/.local/bin/dsh-web-toggle";
      icon = "applications-internet";
      terminal = false;
      categories = [ "Development" "WebDevelopment" ];
    };

    # 覆盖 Nautilus 自带的中文本地化名称，让 fuzzel 显示名与命令一致。
    # desktop 文件 ID 保持不变，因此不会出现中英文两个重复入口。
    xdg.desktopEntries."org.gnome.Nautilus" = {
      name = "Nautilus";
      genericName = "File Manager";
      comment = "Access and organize files";
      exec = "nautilus --new-window %U";
      icon = "org.gnome.Nautilus";
      terminal = false;
      startupNotify = true;
      categories = [ "GNOME" "GTK" "Utility" "Core" "FileManager" ];
      mimeType = [ "inode/directory" "application/x-gnome-saved-search" ];
      settings = {
        DBusActivatable = "true";
        StartupWMClass = "org.gnome.Nautilus";
      };
    };
  };
}
