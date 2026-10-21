{ config, pkgs, lib, ... }:
let
  copyActionsScript = ''
    local mp = require 'mp'
    local msg = require 'mp.msg'

    local function trim(s)
        if not s then return "" end
        return (s:gsub("^%s*(.-)%s*$", "%1"))
    end

    local function copy_text(text)
        local cmd = [[
            if command -v wl-copy >/dev/null 2>&1; then
                printf "%s" "$1" | wl-copy >/dev/null 2>&1 && exit 0
            elif command -v xclip >/dev/null 2>&1; then
                printf "%s" "$1" | xclip -selection clipboard >/dev/null 2>&1 && exit 0
            else
                exit 127
            fi
        ]]
        local res = mp.command_native({
            name = "subprocess",
            playback_only = false,
            capture_stdout = false,
            capture_stderr = false,
            args = { "sh", "-c", cmd, "copy-text", text }
        })
        return res and res.status == 0
    end

    local function copy_image_file(image_path)
        local cmd = [[
            if command -v wl-copy >/dev/null 2>&1; then
                wl-copy -t image/png < "$1" >/dev/null 2>&1 && rm -f "$1" && exit 0
            elif command -v xclip >/dev/null 2>&1; then
                xclip -selection clipboard -t image/png -i "$1" >/dev/null 2>&1 && rm -f "$1" && exit 0
            else
                rm -f "$1"
                exit 127
            fi
        ]]
        local res = mp.command_native({
            name = "subprocess",
            playback_only = false,
            capture_stdout = false,
            capture_stderr = false,
            args = { "sh", "-c", cmd, "copy-image", image_path }
        })
        return res and res.status == 0
    end

    local function copy_subtitle()
        local text = mp.get_property("sub-text")
        text = trim(text)
        if not text or text == "" then
            mp.osd_message("当前无字幕显示", 2)
            return
        end

        if copy_text(text) then
            mp.osd_message("已复制字幕: " .. text, 3)
            msg.info("已复制字幕到剪贴板: " .. text)
        else
            mp.osd_message("复制字幕失败", 2)
            msg.error("复制字幕失败")
        end
    end

    local function copy_screenshot()
        local tmp_file = string.format("/tmp/mpv-shot-%d-%d.png", os.time(), math.random(1000, 9999))

        local success, err = pcall(function()
            mp.commandv("screenshot-to-file", tmp_file, "subtitles")
        end)

        if not success then
            mp.osd_message("截图失败: " .. tostring(err), 2)
            msg.error("截图执行失败: " .. tostring(err))
            return
        end

        local f = io.open(tmp_file, "r")
        if not f then
            mp.osd_message("截图生成失败", 2)
            msg.error("截图文件未能生成: " .. tmp_file)
            return
        end
        f:close()

        if copy_image_file(tmp_file) then
            mp.osd_message("截图已复制到剪贴板", 2)
            msg.info("截图已成功复制到剪贴板")
        else
            mp.osd_message("截图复制到剪贴板失败", 2)
            msg.error("未能将截图放入剪贴板")
        end
    end

    mp.add_key_binding("Ctrl+c", "copy-subtitle", copy_subtitle)
    mp.add_key_binding("Ctrl+s", "copy-screenshot", copy_screenshot)
  '';

  inputConfig = ''
    # Ctrl+c 复制当前显示的字幕到系统剪贴板
    Ctrl+c script-binding copy_actions/copy-subtitle

    # Ctrl+s 截取当前画面（含字幕）并直接复制到系统剪贴板（原版 s 键仍为保存本地文件）
    Ctrl+s script-binding copy_actions/copy-screenshot
  '';
in
{
  xdg.configFile."mpv/input.conf" = {
    text = inputConfig;
    force = true;
  };

  xdg.configFile."mpv/scripts/copy_actions.lua" = {
    text = copyActionsScript;
    force = true;
  };
}
