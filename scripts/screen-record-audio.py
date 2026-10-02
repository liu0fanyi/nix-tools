"""Audio selection and owned temporary mixing for shortcut recordings."""
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import time

LABELS = {"system": "系统声音", "mic": "麦克风", "both": "系统+麦克风", "none": "无声"}
UNIT = "nix-tools-screen-record.service"


def config_path():
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "nix-tools/screen-record-audio"


def ledger_path():
    return Path(os.environ["XDG_RUNTIME_DIR"]) / "nix-tools-screen-record-modules.json"


def command(*args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, check=True, **kwargs).stdout.strip()


def selected_mode():
    try:
        mode = config_path().read_text().strip()
    except FileNotFoundError:
        mode = "system"
    return mode if mode in LABELS else "system"


def active():
    try:
        return command("systemctl", "--user", "show", UNIT, "--property=ActiveState", "--value") in {"active", "activating", "deactivating", "reloading"}
    except subprocess.CalledProcessError:
        return False


def notify(title, message):
    subprocess.run(["notify-send", title, message], check=False)


def choose():
    # Serialize against starting/stopping a recording, including region selection.
    import fcntl
    lock_path = Path(os.environ["XDG_RUNTIME_DIR"]) / "screen-record-toggle.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if active():
            notify("录屏声音", "请先结束当前录屏，再选择下一次的声音来源。")
            return
        try:
            label = command("fuzzel", "--dmenu", "--prompt=录屏声音：", input="\n".join(LABELS.values()) + "\n")
        except subprocess.CalledProcessError:
            return
        mode = next((key for key, value in LABELS.items() if value == label), None)
        if mode is None:
            return
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(mode + "\n")
        temp.replace(path)


def status():
    mode = selected_mode()
    recording = active()
    print(json.dumps({"text": ("● " if recording else " ") + LABELS[mode], "class": "recording" if recording else "idle", "tooltip": "录屏声音：" + LABELS[mode] + "\n左键选择声音；右键开始/停止\nCtrl+Shift+Fn+I 直接录屏\nAlt+Shift+Fn+I 录完打开编辑器"}, ensure_ascii=False))


def sources():
    return json.loads(command("pactl", "--format=json", "list", "sources"))


def microphone(available):
    # A default monitor is system audio, never a microphone.
    candidates = [item["name"] for item in available if not item["name"].endswith(".monitor")]
    if not candidates:
        raise RuntimeError("没有可用麦克风，请选择系统声音或无声。")
    default = command("pactl", "get-default-source")
    return default if default in candidates else candidates[0]


def cleanup():
    path = ledger_path()
    if not path.exists():
        return
    ledger = json.loads(path.read_text())
    current = {int(item["index"]): item for item in json.loads(command("pactl", "--format=json", "list", "modules"))}
    remaining = []
    for owned in reversed(ledger):
        item = current.get(owned["id"])
        # IDs may have been reused after an audio server restart. Match identity too.
        if item is None or item["name"] != owned["name"] or ledger_sink(owned) not in shlex.split(item.get("argument", "")):
            continue
        try:
            command("pactl", "unload-module", str(owned["id"]))
        except subprocess.CalledProcessError:
            remaining.insert(0, owned)
    if remaining:
        path.write_text(json.dumps(remaining))
        raise RuntimeError("未能释放录屏混音模块，保留清理凭据；请查看录屏日志。")
    path.unlink(missing_ok=True)


def ledger_sink(owned):
    return "sink_name=" + owned["sink"] if owned["name"] == "module-null-sink" else "sink=" + owned["sink"]


def prepare():
    cleanup()
    mode = selected_mode()
    if mode == "none":
        return ""
    available = sources()
    monitor = None
    mic = None
    if mode in {"system", "both"}:
        monitor = command("pactl", "get-default-sink") + ".monitor"
        if monitor not in {item["name"] for item in available}:
            raise RuntimeError("默认输出没有可用 monitor，无法录制系统声音。")
    if mode in {"mic", "both"}:
        mic = microphone(available)
    if mode != "both":
        return monitor if mode == "system" else mic
    sink = "nix_tools_record_mix_" + str(time.time_ns())
    ledger = []

    def load(name, *arguments):
        module = int(command("pactl", "load-module", name, *arguments))
        ledger.append({"id": module, "name": name, "sink": sink})
        ledger_path().write_text(json.dumps(ledger))

    try:
        load("module-null-sink", "sink_name=" + sink, "rate=48000", "channels=2", "sink_properties=device.description=NixToolsRecording node.virtual=true priority.session=0")
        for source in (monitor, mic):
            load("module-loopback", "source=" + source, "sink=" + sink, "latency_msec=50", "source_dont_move=true", "sink_dont_move=true")
    except Exception:
        cleanup()
        raise
    return sink + ".monitor"


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "choose"
    try:
        if action == "choose":
            choose()
        elif action == "status":
            status()
        elif action == "mode":
            print(selected_mode())
        elif action == "prepare":
            print(prepare())
        elif action == "cleanup":
            cleanup()
        else:
            raise RuntimeError("未知录屏声音操作")
    except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError) as error:
        if action != "cleanup":
            notify("录屏声音不可用", str(error))
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
