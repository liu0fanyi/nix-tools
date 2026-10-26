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


REGISTRY = Path(__file__).resolve().parents[3] / "project/projects.json"
PROJECTS_ROOT = "/home/liou/dufs-lan/todos/projects"


def registrations():
    data = __import__("json").loads(REGISTRY.read_text())
    if data["remote_host"] != "liou@nuc.local" or data["remote_root"] != PROJECTS_ROOT:
        raise ValueError("Unexpected project publication registry")
    names = [p["name"] for p in data["projects"]]
    if len(names) != len(set(names)) or any(not re.fullmatch(r"[a-zA-Z0-9_-]+", n) for n in names):
        raise ValueError("Unique safe project names required")
    return data["projects"]


def registered(root):
    for project in registrations():
        if str(root) == project["root"]:
            return project
        if str(root) in project.get("aliases", []):
            raise ValueError("Update and publish the owning project at " + project["root"] + "; do not overwrite it from a worktree")
    raise ValueError("Register the owning project centrally before publication")


def source_url(root):
    remotes = subprocess.check_output(["git", "-C", str(root), "remote"], text=True).splitlines()
    remote = "product" if "product" in remotes else "origin" if "origin" in remotes else None
    if not remote:
        return None
    raw = subprocess.check_output(["git", "-C", str(root), "remote", "get-url", remote], text=True).strip()
    match = re.fullmatch(r"git@(github.com|gitee.com):([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+?)(?:\.git)?", raw)
    if not match:
        match = re.fullmatch(r"(?:https://|ssh://git@)(github.com|ssh.github.com|gitee.com)(?::443)?/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+?)(?:\.git)?", raw)
    if not match:
        return None
    host = match[1].replace("ssh.github.com", "github.com")
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    published = subprocess.check_output(["git", "-C", str(root), "for-each-ref", "--format=%(refname)", "--contains", sha, "refs/remotes/" + remote + "/"], text=True).strip()
    if not published:
        return None  # Local-only or failed pushes must not produce broken source links.
    return "https://" + host + "/" + match[2] + "/blob/" + sha + "/"


def project_entry(root, text):
    # Keep source links local in Git, but publish only the concise Markdown overview.
    # Details link to the exact existing Git commit; no spec tree or source is uploaded.
    reading_entry(root, text)  # Validate local references and repository containment.
    base = source_url(root)
    def link(match):
        label, target = match[1], match[2]
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith(("#", "/")):
            return match[0]
        path, sep, anchor = target.partition("#")
        relocated = posixpath.normpath("specs/" + path)
        if not base:
            return label  # No invented remote or broken links for local-only repositories.
        tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", relocated], capture_output=True)
        changed = subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", relocated], capture_output=True)
        if tracked.returncode or changed.returncode:
            return label + "（本地记录待提交）"
        from urllib.parse import quote
        return "[" + label + "](" + base + quote(relocated, safe="/") + (sep + anchor if sep else "") + ")"
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)


def index_entry():
    lines = ["# 工程总纲", "", "每个项目一份 Markdown；项目名称可打开当前情况、后续计划、待处理问题与最近变化。", ""]
    projects = registrations()
    for category in dict.fromkeys(p["category"] for p in projects):
        lines += ["## " + category, "", "| 项目 | 当前情况 |", "| --- | --- |"]
        for project in projects:
            if project["category"] != category:
                continue
            root = Path(project["root"])
            text = (root / "specs/README.md").read_text()
            section = text.partition("## 当前情况")[2].split("\n## ")[0]
            first = next((l[2:].strip() for l in section.splitlines() if l.startswith("- ")), "暂无已确认状态")
            first = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first).replace("|", "\\|")
            lines.append("| [" + project["name"] + "](" + project["name"] + ".md) | " + first + " |")
        lines.append("")
    return "\n".join(lines)


def publish(root, text, destination=None, dry_run=False):
    project = registered(root)
    if destination is not None and destination.rstrip("/") != PROJECTS_ROOT:
        raise ValueError("Project summaries publish only to " + PROJECTS_ROOT)
    entries = {project["name"] + ".md": project_entry(root, text), "README.md": index_entry()}
    with tempfile.TemporaryDirectory(prefix="project-overview-") as temp:
        stage = Path(temp)
        for name, body in entries.items():
            (stage / name).write_text(body)
            (stage / name).chmod(0o644)
        mkdir = ["ssh", "liou@nuc.local", "mkdir -p -m 755 " + shlex.quote(PROJECTS_ROOT)]
        # Explicit files only; never --delete on the shared projects directory.
        transfer = ["rsync", "-ptz", "--checksum", "--chmod=F644", *[str(stage/name) for name in entries], "liou@nuc.local:" + PROJECTS_ROOT + "/"]
        if dry_run:
            print(entries[project["name"] + ".md"], end="")
            print(shlex.join(mkdir)); print(shlex.join(transfer))
            return
        subprocess.run(mkdir, check=True)
        subprocess.run(transfer, check=True)
        result = subprocess.run(transfer[:1] + ["--dry-run", "--itemize-changes"] + transfer[1:], check=True, capture_output=True, text=True)
        if result.stdout.strip():
            raise ValueError("Overview mirror mismatch: " + result.stdout)
        print("Verified project overview: " + PROJECTS_ROOT + "/" + project["name"] + ".md")


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
            print(project_entry(root, text), end="")
        elif args.publish:
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
