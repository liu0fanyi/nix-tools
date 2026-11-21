#!/usr/bin/env python3
"""Open a floating process and system-disk monitor in the current Niri session."""

import curses
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import NamedTuple


APP_ID = "nix-tools-system-monitor"
MIB = 1024**2
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


class Snapshot(NamedTuple):
    timestamp: float
    disk: list[int]
    processes: dict
    cpu_total: int
    cpu_idle: int


def system_disk():
    device = subprocess.check_output(
        ["findmnt", "-no", "MAJ:MIN", "--target", "/nix/store"], text=True
    ).strip()
    path = Path(f"/sys/dev/block/{device}").resolve(strict=True)
    return path.parent if (path / "partition").exists() else path


def snapshot(disk):
    processes = {}
    for entry in Path("/proc").glob("[0-9]*/stat"):
        try:
            stat = entry.read_text(errors="replace")
            prefix, _, fields = stat.rpartition(") ")
            fields = fields.split()
            name = prefix.split("(", 1)[1]
            state = fields[0]
            cpu = int(fields[11]) + int(fields[12])
            start = int(fields[19])
            rss = int(fields[21]) * PAGE_SIZE
        except (OSError, IndexError, ValueError):
            continue
        try:
            counters = dict(line.split(":", 1) for line in entry.with_name("io").read_text().splitlines())
            io = (int(counters["read_bytes"]), int(counters["write_bytes"]))
        except (OSError, KeyError, ValueError):
            io = None
        processes[(int(entry.parent.name), start)] = (name, state, cpu, rss, io)
    # The first eight fields already include time spent running guests.
    with Path("/proc/stat").open() as stat:
        cpu = list(map(int, stat.readline().split()[1:9]))
    disk_counters = list(map(int, (disk / "stat").read_text().split()))
    return Snapshot(time.monotonic(), disk_counters, processes, sum(cpu), cpu[3] + cpu[4])


def disk_summary(disk, before, after, elapsed):
    delta = [max(0, new - old) for old, new in zip(before, after)]
    read, write = (delta[index] * 512 / MIB / elapsed for index in (2, 6))
    read_ms, write_ms = (f"{delta[index + 3] / delta[index]:.0f}" if delta[index] else "--" for index in (0, 4))
    try:
        pressure = Path("/proc/pressure/io").read_text().splitlines()[0].split()[1].split("=")[1]
    except (OSError, IndexError):
        pressure = "--"
    if pressure != "--":
        pressure = f"{float(pressure):.0f}%"
    return f"{disk.name} {read:.0f}/{write:.0f}MiB/s R/W {read_ms}/{write_ms}ms PSI {pressure}"


def system_summary(cpu_ticks, idle_ticks):
    cpu = 100 * max(0, cpu_ticks - idle_ticks) / cpu_ticks
    memory = {}
    with Path("/proc/meminfo").open() as meminfo:
        for line in meminfo:
            key, value = line.split(":", 1)
            if key in ("MemTotal", "MemAvailable"):
                memory[key] = int(value.split()[0])
    total = memory["MemTotal"] / MIB
    used = (memory["MemTotal"] - memory["MemAvailable"]) / MIB
    return f"CPU {cpu:.0f}% RAM {used:.1f}/{total:.0f}GiB"


def process_rows(before, after, elapsed, cpu_ticks):
    for key, (name, state, cpu, rss, io) in after.items():
        _, _, old_cpu, _, old_io = before.get(key, (name, state, cpu, rss, None))
        read, write = (
            tuple(max(0, new - old) / MIB / elapsed for old, new in zip(old_io, io))
            if old_io is not None and io is not None else (-1, -1)
        )
        cpu_percent = max(0, cpu - old_cpu) * 100 / cpu_ticks
        yield key[0], name, state, cpu_percent, rss / MIB, read, write


def display(screen, disk):
    curses.use_default_colors()
    curses.curs_set(0)
    screen.timeout(1000)
    sort_keys = {ord("c"): (3, "CPU"), ord("m"): (4, "RAM"),
                 ord("r"): (5, "read"), ord("w"): (6, "write")}
    sort_index, sort_name = sort_keys[ord("w")]
    before = after = snapshot(disk)
    summary = f"{disk.name}  Sampling system disk…"
    rows = []
    while True:
        elapsed = after.timestamp - before.timestamp
        cpu_ticks = after.cpu_total - before.cpu_total
        if elapsed > 0 and cpu_ticks > 0:
            idle_ticks = after.cpu_idle - before.cpu_idle
            summary = f"{system_summary(cpu_ticks, idle_ticks)}  {disk_summary(disk, before.disk, after.disk, elapsed)}"
            rows = list(process_rows(before.processes, after.processes, elapsed, cpu_ticks))
        screen.erase()
        height, width = screen.getmaxyx()
        lines = [summary, f"{'PID':>7}  {'PROCESS':<18} {'CPU%':>6} {'RAM MiB':>8} {'R MiB/s':>8} {'W MiB/s':>8} {'ST':>2}"]
        for pid, name, state, cpu, rss, read, write in sorted(rows, key=lambda row: row[sort_index], reverse=True)[:max(0, height - 3)]:
            read_text = f"{read:.2f}" if read >= 0 else "--"
            write_text = f"{write:.2f}" if write >= 0 else "--"
            lines.append(f"{pid:7}  {name[:18]:18} {cpu:6.1f} {rss:8.1f} {read_text:>8} {write_text:>8} {state:>2}")
        for index, line in enumerate(lines[:max(0, height - 1)]):
            screen.addnstr(index, 0, line, width - 1, curses.A_BOLD if index < 2 else curses.A_NORMAL)
        screen.addnstr(height - 1, 0, f"Sort: {sort_name}   c CPU   m RAM   r read   w write   q quit", width - 1)
        screen.refresh()
        key = screen.getch()
        if key == ord("q"):
            return
        if key in sort_keys:
            sort_index, sort_name = sort_keys[key]
        if time.monotonic() - after.timestamp >= 0.95:
            before, after = after, snapshot(disk)


def niri(*args):
    return subprocess.check_output(["niri", "msg", *args], text=True)


def monitor_window():
    return next((window for window in json.loads(niri("--json", "windows"))
                 if window["app_id"] == APP_ID), None)


def launch():
    existing = monitor_window()
    if existing:
        niri("action", "focus-window", "--id", str(existing["id"]))
        return
    niri("action", "spawn", "--", "foot", "-c", "/dev/null", "-a", APP_ID,
         "-T", "System disk / Processes", "-W", "70x14", "-f", "monospace:pixelsize=17",
         "-o", "main.pad=7x5", "-o", "csd.color=80171a1f",
         "-o", "colors-dark.alpha=0.50", "-o", "colors-dark.alpha-mode=all",
         "-o", "colors-light.alpha=0.50", "-o", "colors-light.alpha-mode=all",
         sys.executable, str(Path(__file__).resolve()), "--display")
    for _ in range(25):
        time.sleep(0.1)
        window = monitor_window()
        if window:
            window_id = str(window["id"])
            niri("action", "move-window-to-floating", "--id", window_id)
            niri("action", "set-window-width", "--id", window_id, "720")
            niri("action", "set-window-height", "--id", window_id, "335")
            return
    raise SystemExit("The system monitor window did not open.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--display"]:
        curses.wrapper(display, system_disk())
    else:
        launch()
