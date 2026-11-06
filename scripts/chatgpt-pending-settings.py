"""Apply explicitly queued connection changes before the desktop app starts."""
import json
import os
from pathlib import Path
import re
import tempfile


def main():
    home = Path.home()
    state_root = Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")) / "chatgpt"
    pending = state_root / "pending-settings.json"
    if not pending.is_file():
        return
    profile = Path(os.environ.get(
        "CODEX_ELECTRON_USER_DATA_PATH",
        str(Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "Codex"),
    ))
    # Launching a second window must not consume a change that the live app
    # could overwrite from its in-memory settings.
    lock = profile / "SingletonLock"
    if lock.is_symlink():
        pid = int(os.readlink(lock).rsplit("-", 1)[1])
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            return
    request = json.loads(pending.read_text())
    assert set(request) == {"disableAutoConnectHostIds"}
    hosts = request["disableAutoConnectHostIds"]
    assert isinstance(hosts, list) and hosts and all(isinstance(h, str) and h for h in hosts)
    path = Path(os.environ.get("CODEX_HOME", home / ".codex")) / ".codex-global-state.json"
    raw = path.read_text()
    before = json.loads(raw)
    key = "remote-connection-auto-connect-by-host-id"
    match = re.search(r'("' + key + r'"\s*:\s*\{)([^{}]*)(\})', raw)
    assert match is not None
    body = match[2]
    expected = json.loads(raw)
    for host in hosts:
        assert host in before[key]
        expected[key][host] = False
        body, count = re.subn(
            r'("' + re.escape(host) + r'"\s*:\s*)(?:true|false)\b', r'\g<1>false', body
        )
        assert count == 1
    updated = raw[:match.start(2)] + body + raw[match.end(2):]
    assert json.loads(updated) == expected
    fd, backup = tempfile.mkstemp(prefix="connection-settings-backup-", suffix=".json", dir=state_root)
    with os.fdopen(fd, "w") as stream:
        stream.write(raw)
    fd, temporary = tempfile.mkstemp(prefix=".connection-settings-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        assert path.read_text() == raw, "Connection settings changed concurrently"
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    pending.unlink()
    print("Applied queued Codex connection settings; previous settings backed up locally.")


if __name__ == "__main__":
    main()
