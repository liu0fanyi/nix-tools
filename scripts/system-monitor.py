#!/usr/bin/env python3
"""Open a floating process and system-disk monitor in the current Niri session."""

import curses
import json
import os
from pathlib import Path
import subprocess
import sys
import time


APP_ID = "nix-tools-system-monitor"
MIB = 1024**2
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")


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
    return time.monotonic(), list(map(int, (disk / "stat").read_text().split())), processes


def disk_summary(disk, before, after, elapsed):
    delta = [new - old for old, new in zip(before, after)]
    read, write = (delta[index] / 2048 / elapsed for index in (2, 6))
    read_ms = f"{delta[3] / delta[0]:.1f}" if delta[0] else "--"
    write_ms = f"{delta[7] / delta[4]:.1f}" if delta[4] else "--"
    try:
        pressure = Path("/proc/pressure/io").read_text().splitlines()[0].split()[1].split("=")[1]
    except (OSError, IndexError):
        pressure = "--"
    return (f"{disk.name}  R {read:.1f} W {write:.1f} MiB/s  "
            f"wait R/W {read_ms}/{write_ms} ms  I/O PSI(10s) {pressure}%")


def process_rows(before, after, elapsed):
    for key, (name, state, cpu, rss, io) in after.items():
        _, _, old_cpu, _, old_io = before.get(key, (name, state, cpu, rss, None))
        read, write = (
            tuple(max(0, new - old) / MIB / elapsed for old, new in zip(old_io, io))
            if old_io is not None and io is not None else (-1, -1)
        )
        yield key[0], name, state, max(0, cpu - old_cpu) * 100 / CLOCK_TICKS / elapsed, rss / MIB, read, write


def display(screen, disk):
    curses.curs_set(0)
    screen.timeout(1000)
    sort_keys = {ord("c"): (3, "CPU"), ord("m"): (4, "RAM"),
                 ord("r"): (5, "read"), ord("w"): (6, "write")}
    sort_index, sort_name = sort_keys[ord("w")]
    before = after = snapshot(disk)
    summary = f"{disk.name}  Sampling system disk…"
    rows = []
    while True:
        elapsed = after[0] - before[0]
        if elapsed > 0:
            summary = disk_summary(disk, before[1], after[1], elapsed)
            rows = list(process_rows(before[2], after[2], elapsed))
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
        if time.monotonic() - after[0] >= 0.95:
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
         "-T", "System disk / Processes", "-w", "790x310",
         "-o", "colors-dark.alpha=0.68", "-o", "colors-light.alpha=0.68",
         sys.executable, str(Path(__file__).resolve()), "--display")
    for _ in range(25):
        time.sleep(0.1)
        window = monitor_window()
        if window:
            window_id = str(window["id"])
            niri("action", "move-window-to-floating", "--id", window_id)
            niri("action", "set-window-width", "--id", window_id, "790")
            niri("action", "set-window-height", "--id", window_id, "310")
            return
    raise SystemExit("The system monitor window did not open.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--display"]:
        curses.wrapper(display, system_disk())
    else:
        launch()
