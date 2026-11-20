"""Keep local, bounded CPU history for the Tag Browser process tree."""

import json
import logging
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import time
from typing import NamedTuple


PROC = Path("/proc")
CGROUP = Path("/sys/fs/cgroup")
TICKS = os.sysconf("SC_CLK_TCK")
PAGE_KIB = os.sysconf("SC_PAGE_SIZE") // 1024
INTERVAL = 2
CPU_TRIGGER = 65
MEMORY_STALL_TRIGGER = 10
BASELINE_INTERVAL = 30
CONTEXT_SAMPLES = 5
MAX_BYTES = 4 * 1024 * 1024
BACKUPS = 3


class Stat(NamedTuple):
    name: str
    parent: int
    started: int
    user: int
    system: int
    rss_kib: int
    major_faults: int


def read_stat(path):
    try:
        name, fields = path.read_text(errors="replace").rsplit(")", 1)
    except OSError:
        return None
    f = fields.split()
    return Stat(name.split("(", 1)[1], int(f[1]), int(f[19]), int(f[11]),
                int(f[12]), int(f[21]) * PAGE_KIB, int(f[9]))


def browser_groups():
    groups = set()
    uid = os.getuid()
    for path in PROC.iterdir():
        if not path.name.isdecimal():
            continue
        try:
            if path.stat().st_uid != uid or (path / "comm").read_text().strip() != "tagbrowser":
                continue
            for line in (path / "cgroup").read_text().splitlines():
                if line.startswith("0::"):
                    groups.add(CGROUP / line[3:].lstrip("/"))
        except OSError:
            continue
    return groups


def snapshot(groups):
    processes = {}
    for group in groups:
        try:
            ids = (group / "cgroup.procs").read_text().split()
        except OSError:
            continue
        for pid in ids:
            stat = read_stat(PROC / pid / "stat")
            if stat is not None:
                processes[int(pid)] = stat

    def is_browser(pid):
        while pid in processes:
            stat = processes[pid]
            if stat.name == "tagbrowser":
                return True
            pid = stat.parent
        return False

    browser = {pid: stat for pid, stat in processes.items() if is_browser(pid)}
    threads = {}
    for pid in browser:
        try:
            for task in (PROC / str(pid) / "task").iterdir():
                stat = read_stat(task / "stat")
                if stat is not None:
                    threads[(pid, int(task.name))] = stat
        except OSError:
            continue
    return browser, threads


def deltas(current, previous, seconds):
    for key, stat in current.items():
        old = previous.get(key)
        if old is None or stat.started != old.started:
            continue
        user = round(100 * (stat.user - old.user) / (seconds * TICKS), 1)
        system = round(100 * (stat.system - old.system) / (seconds * TICKS), 1)
        yield key, stat, user, system, stat.major_faults - old.major_faults


def pressure_total(resource, kind):
    try:
        lines = (PROC / "pressure" / resource).read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        if line.startswith(kind + " "):
            return int(line.rsplit("total=", 1)[1])
    return None


def task_rows(changes, limit, id_key):
    ranked = sorted(changes, key=lambda row: (row[2] + row[3], row[1].rss_kib), reverse=True)
    rows = []
    for key, stat, user, system, faults in ranked[:limit]:
        row = {**id_key(key), "name": stat.name, "user_pct": user, "system_pct": system}
        if isinstance(key, int):
            row.update(parent_pid=stat.parent, rss_kib=stat.rss_kib, major_faults=faults)
        rows.append(row)
    return rows


def report(current, previous, seconds, pressure):
    processes, threads = current
    changes = list(deltas(processes, previous[0], seconds))
    cpu = round(sum(row[2] + row[3] for row in changes), 1)
    busy_threads = (row for row in deltas(threads, previous[1], seconds) if row[2] + row[3] > 0)
    reasons = []
    if cpu >= CPU_TRIGGER:
        reasons.append("browser_cpu")
    if pressure.get("memory_full_pct", 0) >= MEMORY_STALL_TRIGGER:
        reasons.append("memory_stall")
    if seconds >= 2 * INTERVAL:
        reasons.append("sample_delay")
    return {
        "time": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "interval_s": round(seconds, 2),
        "browser_cpu_pct": cpu,
        "pressure": pressure,
        "triggers": reasons,
        "processes": task_rows(changes, 8, lambda pid: {"pid": pid}),
        "threads": task_rows(busy_threads, 10, lambda ids: {"pid": ids[0], "tid": ids[1]}),
    }


def run(state_dir):
    handler = RotatingFileHandler(
        state_dir / "samples.jsonl", maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="ascii"
    )
    history = deque(maxlen=CONTEXT_SAMPLES)
    last_saved = float("-inf")
    capture_until = float("-inf")
    refresh_at = 0
    groups = set()
    previous = ({}, {})
    previous_pressure = {}
    previous_at = time.monotonic()

    while True:
        now = time.monotonic()
        if now >= refresh_at:
            groups = browser_groups()
            refresh_at = now + 10
        current = snapshot(groups)
        counters = {
            "cpu_some_pct": pressure_total("cpu", "some"),
            "memory_full_pct": pressure_total("memory", "full"),
        }
        elapsed = now - previous_at
        if current[0] and previous[0]:
            pressure = {
                key: round((value - previous_pressure[key]) / (10_000 * elapsed), 1)
                for key, value in counters.items()
                if value is not None and previous_pressure.get(key) is not None
            }
            sample = report(current, previous, elapsed, pressure)
            history.append((now, sample))
            if sample["triggers"]:
                capture_until = now + INTERVAL * CONTEXT_SAMPLES
            if now <= capture_until:
                pending = list(history)
            elif now - last_saved >= BASELINE_INTERVAL:
                pending = [(now, sample)]
            else:
                pending = []
            for sampled_at, record in pending:
                if sampled_at > last_saved:
                    line = json.dumps(record, separators=(",", ":"))
                    handler.emit(logging.LogRecord("sampler", logging.INFO, "", 0, line, (), None))
                    last_saved = sampled_at
        else:
            history.clear()
            capture_until = float("-inf")
        previous, previous_at, previous_pressure = current, now, counters
        time.sleep(max(0, now + INTERVAL - time.monotonic()))


if __name__ == "__main__":
    run(Path(sys.argv[1]))
