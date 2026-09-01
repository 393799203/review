"""
通达信 datatool 路径解析与复制到 work 目录（跨平台）。

Windows 上常见错误：embed/datatool 为 Linux ELF → WinError 193。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_WINDOWS_EXE_HINT = (
    "请将通达信安装目录中的 datatool.exe 放到本包 embed/datatool.exe "
    "（或 embed/datatool 并确保为 Windows 版）；也可设置环境变量 TDX_DATATOOL 指向该 exe，"
    "或在命令行使用 --datatool；在 Windows 上可运行 python find_copy_datatool.py 尝试自动查找并复制。"
    "详见 embed/README.txt。"
)


def is_elf(path: Path) -> bool:
    try:
        return path.read_bytes()[:4] == b"\x7fELF"
    except OSError:
        return False


def default_embed_datatool_path(package_root: Path) -> Path:
    """默认 datatool 路径：优先环境变量 TDX_DATATOOL，否则 Windows 下 embed/datatool.exe，最后 embed/datatool。"""
    env = os.environ.get("TDX_DATATOOL", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()
    embed = package_root / "embed"
    if sys.platform == "win32":
        exe = embed / "datatool.exe"
        if exe.is_file():
            return exe
    return embed / "datatool"


def resolve_datatool_source(path: Path) -> Path:
    """
    解析为本机可调用的 datatool 文件路径。
    Windows 若指向 ELF，则尝试同目录 datatool.exe。
    """
    if path.is_file():
        if sys.platform == "win32" and is_elf(path):
            alt = path.with_suffix(".exe")
            if alt.is_file():
                return alt
            raise RuntimeError(
                f"{path} 为 Linux 版 datatool（ELF），无法在 Windows 上执行。\n{_WINDOWS_EXE_HINT}"
            )
        return path

    if sys.platform == "win32" and path.suffix.lower() != ".exe":
        alt = path.with_suffix(".exe")
        if alt.is_file():
            return alt
    return path


def ensure_datatool_in_work(work_dir: Path, source_path: Path) -> Path:
    """将 embed 侧的 datatool 复制到 work_dir，保留文件名（datatool / datatool.exe）。"""
    src = resolve_datatool_source(source_path)
    if not src.is_file():
        msg = f"未找到 datatool 可执行文件: {source_path}"
        if sys.platform == "win32":
            msg += f"\n{_WINDOWS_EXE_HINT}"
        raise FileNotFoundError(msg)
    work_dir.mkdir(parents=True, exist_ok=True)
    dest = work_dir / src.name
    shutil.copy2(src, dest)
    if sys.platform != "win32":
        dest.chmod(dest.stat().st_mode | 0o111)
    return dest
