#!/usr/bin/env python3
"""
sync-mimeapps.py
检查并同步 ~/.config/mimeapps.list 中的外部应用改动到 Home Manager 配置中。

核心原则：
1. 关键协议强力劫持保护（Anchor）：
   - http/https/html/xhtml 当前 PC 锁定为 tag-browser.desktop（防止其它浏览器或第三方应用篡改）
   - magnet/bittorrent 绝对锁定为 org.qbittorrent.qBittorrent.desktop
   - codex:// 锁定为 chatgpt.desktop
   - baiduyunguanjia:// 锁定为 baidunetdisk.desktop
2. 动态关联吸收（Ingest）：
   - 外部应用或用户在桌面/文件管理器右键设置的新文件类型关联（如 video/*, image/*, pdf 等），
     自动识别并提供反哺更新到 home-manager/home.nix 的能力。
"""

import sys
import os
import re
import argparse
import configparser
from pathlib import Path

# 不可篡改的核心锚点映射（绝对防劫持）
LOCKED_ANCHORS = {
    "x-scheme-handler/http": "tag-browser.desktop",
    "x-scheme-handler/https": "tag-browser.desktop",
    "text/html": "tag-browser.desktop",
    "application/xhtml+xml": "tag-browser.desktop",
    "x-scheme-handler/magnet": "org.qbittorrent.qBittorrent.desktop",
    "application/x-bittorrent": "org.qbittorrent.qBittorrent.desktop",
    "x-scheme-handler/codex": "chatgpt.desktop",
    "x-scheme-handler/baiduyunguanjia": "baidunetdisk.desktop",
}

REPO_ROOT = Path(__file__).resolve().parent.parent
HOME_NIX = REPO_ROOT / "home-manager" / "home.nix"
MIMEAPPS_PATH = Path(os.path.expanduser("~/.config/mimeapps.list"))


def parse_home_nix_defaults() -> dict[str, str]:
    """从 home-manager/home.nix 中解析当前声明的 defaultApplications"""
    if not HOME_NIX.exists():
        return {}
    content = HOME_NIX.read_text(encoding="utf-8")
    match = re.search(r"xdg\.mimeApps\s*=\s*\{.*?defaultApplications\s*=\s*\{(.*?)\};", content, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    mapping = {}
    for line in block.splitlines():
        line = line.strip()
        m = re.match(r'["\']([^"\']+)["\']\s*=\s*\[\s*["\']([^"\']+)["\']\s*\];', line)
        if m:
            mapping[m.group(1)] = m.group(2)
    return mapping


def parse_system_mimeapps() -> dict[str, str]:
    """解析当前 ~/.config/mimeapps.list 中的 Default Applications"""
    if not MIMEAPPS_PATH.exists():
        return {}
    cp = configparser.ConfigParser()
    try:
        cp.read(MIMEAPPS_PATH, encoding="utf-8")
    except Exception as e:
        print(f"解析 ~/.config/mimeapps.list 失败: {e}", file=sys.stderr)
        return {}
    res = {}
    if "Default Applications" in cp:
        for k, v in cp["Default Applications"].items():
            # 取分号分隔的第一个 desktop
            target = v.split(";")[0].strip()
            if target:
                res[k.strip()] = target
    return res


def update_home_nix_defaults(merged: dict[str, str]):
    """将合并后的 defaultApplications 格式化写回 home-manager/home.nix"""
    content = HOME_NIX.read_text(encoding="utf-8")

    # 构建新的 defaultApplications 代码块
    lines = ["    defaultApplications = {"]
    for k in sorted(merged.keys()):
        lines.append(f'      "{k}" = [ "{merged[k]}" ];')
    lines.append("    };")
    new_block = "\n".join(lines)

    pattern = r"defaultApplications\s*=\s*\{.*?\};"
    updated, count = re.subn(pattern, new_block, content, count=1, flags=re.DOTALL)
    if count == 0:
        print("未能在 home.nix 中找到 defaultApplications 块，请手动更新。", file=sys.stderr)
        sys.exit(1)
    HOME_NIX.write_text(updated, encoding="utf-8")
    print(f"✓ 成功更新 {HOME_NIX} 中的 xdg.mimeApps 关联！")


def main():
    parser = argparse.ArgumentParser(description="核对与同步外部 MIME 关联改动至 Home Manager")
    parser.add_argument("--apply", action="store_true", help="将外部新增的合法关联自动写入 home-manager/home.nix")
    parser.add_argument("--check", action="store_true", help="仅做检查，若发现未同步的外部改动则退出码为 1")
    args = parser.parse_args()

    print(f"正在核对 MIME 关联状态...")
    nix_defaults = parse_home_nix_defaults()

    is_symlink = MIMEAPPS_PATH.is_symlink()
    if is_symlink:
        target = MIMEAPPS_PATH.resolve()
        print(f"✓ ~/.config/mimeapps.list 是指向 Nix store 的软链接 ({target.name})，无脱离改动。")
        sys.exit(0)

    print(f"! ~/.config/mimeapps.list 当前为普通文件，外部应用曾修改过此文件。")
    sys_defaults = parse_system_mimeapps()

    new_associations = {}
    hijack_attempts = {}

    for mime_type, target_app in sys_defaults.items():
        if mime_type in LOCKED_ANCHORS:
            expected = LOCKED_ANCHORS[mime_type]
            if target_app != expected:
                hijack_attempts[mime_type] = (target_app, expected)
        else:
            if nix_defaults.get(mime_type) != target_app:
                new_associations[mime_type] = target_app

    if hijack_attempts:
        print("\n[拦截提醒] 检测到外部试图修改核心锚点协议（已自动拒绝吸收并强制维持预设）：")
        for k, (actual, expected) in hijack_attempts.items():
            print(f"  - {k}: 外部修改为 '{actual}' -> 坚决保持 '{expected}'")

    if new_associations:
        print("\n[增量发现] 检测到外部应用/用户新增了以下合法关联：")
        for k, v in new_associations.items():
            print(f"  + {k} = {v}")
    else:
        print("\n✓ 未发现需要反哺的新增合法关联（外部文件与 Nix 声明一致或差异已被锚点拦截）。")

    if new_associations:
        if args.apply:
            merged = dict(nix_defaults)
            # 确保锚点绝对正确
            merged.update(LOCKED_ANCHORS)
            # 合并新增合法项
            merged.update(new_associations)
            update_home_nix_defaults(merged)
        else:
            print("\n提示：若需将这些新增关联持久化保存到 Home Manager 配置中，可运行：")
            print("  python3 scripts/sync-mimeapps.py --apply")
            if args.check:
                sys.exit(1)


if __name__ == "__main__":
    main()
