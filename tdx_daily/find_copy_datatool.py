#!/usr/bin/env python3
"""
在 Windows 上搜索通达信安装目录中的 datatool.exe（PE），可选复制到本包 embed/datatool.exe。

datatool 为通达信闭源工具，仓库无法自带或「重构」源码；只能从本机安装拷贝。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _is_pe(path: Path) -> bool:
    try:
        return path.read_bytes()[:2] == b"MZ"
    except OSError:
        return False


def _search_roots() -> list[Path]:
    extra: list[str] = []
    for key in ("TDX_HOME", "TDX_INSTALL", "TDX_ROOT"):
        v = os.environ.get(key, "").strip()
        if v:
            extra.append(v)
    roots: list[Path] = []
    for s in extra:
        roots.append(Path(s).expanduser())
    roots.extend(
        [
            Path(r"C:\new_tdx"),
            Path(r"D:\new_tdx"),
            Path(r"C:\tdx"),
            Path(r"D:\tdx"),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Tongdaxin",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tongdaxin",
            Path(r"C:\通达信金融终端"),
        ]
    )
    out: list[Path] = []
    seen: set[str] = set()
    for p in roots:
        try:
            rp = p.resolve()
        except OSError:
            continue
        key = str(rp)
        if key not in seen:
            seen.add(key)
            out.append(rp)
    return out


def _find_under(root: Path, max_depth: int) -> list[Path]:
    found: list[Path] = []

    def walk(d: Path, depth: int) -> None:
        if depth > max_depth:
            return
        for name in ("datatool.exe", "Datatool.exe", "DATATOOL.EXE"):
            p = d / name
            if p.is_file() and _is_pe(p):
                found.append(p)
        try:
            subs = list(d.iterdir())
        except (OSError, PermissionError):
            return
        for sub in subs:
            if sub.is_dir():
                walk(sub, depth + 1)

    if root.is_dir():
        walk(root, 0)
    return found


def main() -> int:
    if sys.platform != "win32":
        print("本脚本仅适用于 Windows。Linux 请将官方 Linux 版 datatool 放到 embed/datatool。", file=sys.stderr)
        return 2

    p = argparse.ArgumentParser(description="查找通达信 datatool.exe 并可选复制到 embed/")
    p.add_argument(
        "--copy",
        action="store_true",
        help="将找到的第一个 datatool.exe 复制到 TDX_daily/embed/datatool.exe",
    )
    p.add_argument(
        "--search-root",
        action="append",
        default=[],
        metavar="DIR",
        help="额外搜索根目录（可多次指定）",
    )
    p.add_argument("--max-depth", type=int, default=6, help="每个根目录下最大递归深度（默认 6）")
    args = p.parse_args()

    roots = _search_roots()
    for s in args.search_root:
        roots.append(Path(s).expanduser().resolve())

    all_found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        all_found.extend(_find_under(root, args.max_depth))

    dedup: list[Path] = []
    seen: set[str] = set()
    for path in all_found:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            dedup.append(path.resolve())

    if not dedup:
        print("未在任何候选目录中找到 datatool.exe。", file=sys.stderr)
        print("请：1) 从桌面通达信快捷方式「打开文件所在位置」确认安装根目录；", file=sys.stderr)
        print("     2) 再执行: python find_copy_datatool.py --search-root \"你的通达信根目录\"", file=sys.stderr)
        print("     或设置环境变量 TDX_HOME 后重试。", file=sys.stderr)
        return 1

    for i, path in enumerate(dedup, 1):
        print(f"{i}. {path}")

    first = dedup[0]
    if args.copy:
        dest = ROOT / "embed" / "datatool.exe"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(first, dest)
        print(f"已复制: {first} -> {dest}")
        print("之后 download_g4day_daily / tdx_daily_bar_job 将默认使用该文件（Windows）。")
    else:
        print(f"\n使用以下之一：")
        print(f"  set TDX_DATATOOL={first}")
        print(f"  python download_g4day_daily.py --datatool \"{first}\" ...")
        print(f"或重新运行: python find_copy_datatool.py --copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
