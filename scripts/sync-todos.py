#!/usr/bin/env python3
"""Sync nix-tools specs and documentation to NUC dufs-lan."""
from __future__ import annotations

import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTE_HOST = "liou@nuc.local"
REMOTE_DIR = "/home/liou/dufs-lan/todos/nix-tools"


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + shlex.join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def collect_specs() -> list[dict]:
    specs_dir = ROOT / "specs"
    if not specs_dir.is_dir():
        return []

    specs = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        spec_file = entry / "spec.md"
        tasks_file = entry / "tasks.md"

        title = entry.name
        if spec_file.is_file():
            for line in spec_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line.removeprefix("# ").strip()
                    break

        tasks = []
        if tasks_file.is_file():
            for line in tasks_file.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$", line)
                if m:
                    done = m.group(1).lower() == "x"
                    tasks.append({"title": m.group(2).strip(), "done": done})

        total = len(tasks)
        done_count = sum(1 for t in tasks if t["done"])
        pct = int(done_count / total * 100) if total > 0 else 0
        state = "已完成" if total > 0 and done_count == total else ("实施中" if done_count > 0 else "待实施")

        specs.append({
            "dir_name": entry.name,
            "title": title,
            "total": total,
            "done": done_count,
            "pct": pct,
            "state": state,
        })
    return specs


def render_readme(specs: list[dict]) -> str:
    lines = [
        "# nix-tools 状态看板与工程文档",
        "",
        "> 本目录由 PC `nix-tools` 通过 `just sync-todos` 自动同步镜像，只读查阅，请勿在远端手动编辑。",
        "",
        "## 一、特异规格与进展 (Specs)",
        "",
    ]

    if not specs:
        lines.append("暂无特异规格。")
    else:
        lines.append("| 编号与标识 | 特性名称 | 完成进度 | 状态 | 规格文档 | 任务清单 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for s in specs:
            dir_name = s["dir_name"]
            progress = f"{s['pct']}% ({s['done']}/{s['total']})"
            spec_link = f"[spec.md](specs/{dir_name}/spec.md)"
            tasks_link = f"[tasks.md](specs/{dir_name}/tasks.md)"
            lines.append(f"| `{dir_name}` | {s['title']} | {progress} | {s['state']} | {spec_link} | {tasks_link} |")

    lines.extend([
        "",
        "## 二、工程权威文档 (Documentation)",
        "",
        "- [构建发布命令与工程约束（AGENTS.md）](docs/build-agent-guide.md)",
        "- [两端生产发布与三个访问场景验收](docs/production-verification.md)",
        "- [PC 发起的 NUC 管理和阿里云发布](docs/pc-release.md)",
        "- [设备结构与 NUC 重装适用性审查](docs/host-structure-review.md)",
        "- [NUC 重装准备、备份与业务恢复](docs/nuc-migration.md)",
        "",
        "---",
        "权威源码与构建入口：PC `liu-bigpc:/home/liou/nix-tools`",
    ])
    return "\n".join(lines) + "\n"


def main():
    print(f"[*] Scanning specs from {ROOT / 'specs'}...")
    specs = collect_specs()
    readme_content = render_readme(specs)

    print(f"[*] Ensuring remote directories exist at {REMOTE_HOST}:{REMOTE_DIR}...")
    run_cmd(["ssh", REMOTE_HOST, f"mkdir -p {shlex.quote(REMOTE_DIR + '/specs')} {shlex.quote(REMOTE_DIR + '/docs')}"])

    # Normalize permissions: source files may be created under a restrictive
    # umask (e.g. 077 by some agents), which would mirror 700/600 to the NUC
    # and make the planner/DUFS readers unable to serve them. Force the
    # conventional 755/644 regardless of the local umask.
    chmod = ["--chmod=D755,F644"]

    # 1. Sync specs/
    if (ROOT / "specs").is_dir():
        print("[*] Mirroring specs/...")
        run_cmd(["rsync", "-avz", "--delete", *chmod, f"{ROOT}/specs/", f"{REMOTE_HOST}:{REMOTE_DIR}/specs/"])

    # 2. Sync docs/ and deploy/docs/
    print("[*] Mirroring docs/...")
    if (ROOT / "docs").is_dir():
        run_cmd(["rsync", "-avz", *chmod, f"{ROOT}/docs/", f"{REMOTE_HOST}:{REMOTE_DIR}/docs/"])
    if (ROOT / "deploy/docs").is_dir():
        run_cmd(["rsync", "-avz", *chmod, f"{ROOT}/deploy/docs/", f"{REMOTE_HOST}:{REMOTE_DIR}/docs/"])

    # 3. Sync README.md dashboard
    print("[*] Syncing README.md index...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(readme_content)
        temp_name = f.name

    try:
        run_cmd(["rsync", "-avz", *chmod, temp_name, f"{REMOTE_HOST}:{REMOTE_DIR}/README.md"])
    finally:
        Path(temp_name).unlink(missing_ok=True)

    print("[✓] Successfully synced specs, docs, and index dashboard to NUC!")


if __name__ == "__main__":
    main()
