#!/usr/bin/env python3
r"""
通达信官网日线下载 → 解压 → 内置 Python NativeDayMerge 生成 .day → 导入 ``tdx.raw_stocks_daily``。

与 **`run_daily_tdx_daily_bar_download.bat`**（同目录）配套；等价于依次执行本目录下的
**`download_g4day_daily.py`** 与 **`tdx_import_daily_bar.py`**。

``--table-name tdx.daily_bar`` 仅为兼容旧计划任务参数；实际写入 **``tdx.raw_stocks_daily``**。

默认 **无需** ``embed/datatool``；若需通达信 ``day create``，请对 ``download_g4day_daily.py`` 传入 ``--use-external-datatool``。

用法::

    cd /path/to/TDX_daily
    python tdx_daily_bar_job.py --trade-date 2026-05-09 [--cache-dir DIR] [--db-url URL]

依赖：本目录 **内置** ``tdx_native_day_merge``（默认）；可选 **``embed/datatool``**、**`.env`** 中 **`DB_URL`**（或环境变量）。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    p = argparse.ArgumentParser(
        description="官网 g4day 下载并导入 raw_stocks_daily（本目录自包含）"
    )
    p.add_argument(
        "--trade-date",
        required=True,
        help="YYYY-MM-DD：传给 download --today 与 import --max-date",
    )
    p.add_argument(
        "--table-name",
        default="tdx.raw_stocks_daily",
        help="兼容旧参数（如 tdx.daily_bar）；实际写入 tdx.raw_stocks_daily",
    )
    p.add_argument(
        "--cache-dir",
        default=str(ROOT / ".cache" / "web_daily"),
        help="与 download_g4day_daily --cache-dir 一致",
    )
    p.add_argument("--db-url", default=None, help="覆盖 DB_URL（写入子进程环境）")
    args = p.parse_args()

    tn = args.table_name.replace(" ", "").lower()
    if "daily_bar" in tn and "raw_stocks" not in tn:
        print(
            "提示: 已指定 legacy --table-name；数据仍写入 tdx.raw_stocks_daily。",
            file=sys.stderr,
        )

    env = os.environ.copy()
    if args.db_url:
        env["DB_URL"] = args.db_url

    cache = str(Path(args.cache_dir).expanduser().resolve())
    py = sys.executable

    dl_cmd = [
        py,
        "-u",
        str(ROOT / "download_g4day_daily.py"),
        "--cache-dir",
        cache,
        "--today",
        args.trade_date,
    ]
    print("→", " ".join(dl_cmd), flush=True)
    r = subprocess.run(dl_cmd, cwd=str(ROOT), env=env)
    if r.returncode != 0:
        return r.returncode

    vipdoc = Path(cache) / "vipdoc"
    imp_cmd = [
        py,
        "-u",
        str(ROOT / "tdx_import_daily_bar.py"),
        "--lday-path",
        str(vipdoc),
        "--max-date",
        args.trade_date,
    ]
    print("→", " ".join(imp_cmd), flush=True)
    r = subprocess.run(imp_cmd, cwd=str(ROOT), env=env)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
