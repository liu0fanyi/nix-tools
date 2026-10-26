#!/usr/bin/env python3
"""Maintain a repository overview and publish only its Markdown reading entry."""
import argparse
from pathlib import Path, PurePosixPath
import posixpath
import re
import shlex
import subprocess
import tempfile

START = "<!-- recent-commits:start -->"
END = "<!-- recent-commits:end -->"


def repository(path):
    root = Path(path).resolve()
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()
    if Path(actual).resolve() != root:
        raise ValueError("--repo must name the repository root")
    source = root / "specs/README.md"
    if source.is_symlink() or source.parent.is_symlink() or not source.is_file():
        raise ValueError("Create a regular specs/README.md from confirmed specs first")
    return root, source


def recent(root):
    output = subprocess.check_output([
        "git", "-C", str(root), "log", "-100", "--no-merges",
        "--format=%cs%x09%h%x09%s"], text=True)
    rows = []
    for line in output.splitlines():
        date, sha, subject = line.split("\t", 2)
        if re.match(r"^(?:docs?|tests?|ci|build|chore)(?:\(|!|:)|^(?:Record|Document) ", subject, re.I):
            continue
        # Display commit subjects as text; do not interpret Markdown or HTML.
        subject = re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", subject)
        rows.append(f"- {date} · {subject} · `{sha}`")
        if len(rows) == 8:
            break
    return "\n".join(rows) or "- 尚无可显示的功能提交。"


def refreshed(root, text):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("specs/README.md needs exactly one recent-commits marker pair")
    before, rest = text.split(START)
    _, after = rest.split(END)
    return before + START + "\n" + recent(root) + "\n" + END + after


def reading_entry(root, text):
    # The source lives in specs/, while the NUC reading entry lives at project root.
    def link(match):
        target = match[1]
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith(("#", "/")):
            return match[0]
        path, sep, anchor = target.partition("#")
        relocated = posixpath.normpath("specs/" + path)
        if relocated == ".." or relocated.startswith("../"):
            raise ValueError("Overview link escapes repository: " + target)
        local = root / relocated
        if not local.exists() or not local.resolve().is_relative_to(root):
            raise ValueError("Missing or external overview link: " + target)
        return "](" + relocated + (sep + anchor if sep else "") + ")"
    return re.sub(r"\]\(([^)\s]+)\)", link, text)


def publish(root, text, destination, dry_run):
    # Ordinary project mirrors and xiaoqiang's separate area are never mixed.
    if not re.fullmatch(r"/home/liou/(?:dufs-lan/todos|dufs)/[^/\s]+", destination):
        raise ValueError("Use the exact project directory from its rules, never a shared root")
    if "/xiaoqiang/" in str(root) + "/" and not destination.startswith("/home/liou/dufs/"):
        raise ValueError("xiaoqiang cannot publish to todos")
    if "/xiaoqiang/" not in str(root) + "/" and destination.startswith("/home/liou/dufs/"):
        raise ValueError("Non-xiaoqiang repositories cannot publish to the xiaoqiang area")
    if PurePosixPath(destination).name in {".", ".."} or any(part in {".", ".."} for part in destination.split("/")):
        raise ValueError("Invalid project directory")
    entry = reading_entry(root, text)
    with tempfile.TemporaryDirectory(prefix="project-overview-") as temp:
        source = Path(temp) / "README.md"
        source.write_text(entry)
        source.chmod(0o644)
        mkdir = ["ssh", "liou@nuc.local", "mkdir -p " + shlex.quote(destination)]
        transfer = ["rsync", "-ptz", "--checksum", "--chmod=F644", str(source), "liou@nuc.local:" + destination + "/README.md"]
        if dry_run:
            print(entry, end="")
            print(shlex.join(mkdir))
            print(shlex.join(transfer))
            return
        subprocess.run(mkdir, check=True)
        subprocess.run(transfer, check=True)
        verify = transfer[:1] + ["--dry-run", "--itemize-changes"] + transfer[1:]
        result = subprocess.run(verify, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            raise ValueError("Overview mirror mismatch: " + result.stdout)
        print("Verified project overview: " + destination + "/README.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--entry", action="store_true", help="Render the current overview with project-root links")
    group.add_argument("--write", action="store_true", help="Refresh only the local recent-commit section")
    group.add_argument("--publish", action="store_true", help="Publish only README.md to an explicit project mirror")
    parser.add_argument("--remote-dir")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        root, source = repository(args.repo)
        text = source.read_text()
        if args.entry:
            print(reading_entry(root, text), end="")
        elif args.publish:
            if not args.remote_dir:
                parser.error("--publish requires --remote-dir confirmed against project rules")
            publish(root, text, args.remote_dir, args.dry_run)
        else:
            result = refreshed(root, text)
            reading_entry(root, result)  # Validate all local overview links before writing.
            if args.write and not args.dry_run:
                source.write_text(result)
                source.chmod(0o644)
            else:
                print(result, end="")
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
