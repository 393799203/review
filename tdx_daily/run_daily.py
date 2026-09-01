#!/usr/bin/env python3
"""
TDX_daily 每日更新统一入口（纯 Python，不依赖 Go / tdx2db）。

默认顺序（对齐原项目 cron 主干）：日线 → GBBQ → calc_basic → calc_factor → 复权视图 →（可选）分时。

用法:
  cd /path/to/TDX_daily && source .venv/bin/activate
  cp .env.example .env   # 编辑 DB_URL
  python run_daily.py --lday-path /你的/vipdoc根目录

  # 从官网自动下载日线 zip → refmhq → datatool → 再导入（无需本地 vipdoc）
  python run_daily.py --download-daily [--cache-dir ~/.cache/tdx_web_daily]

  python run_daily.py --lday-path ... --full-basic --full-factor   # 全量 basic/因子
  python run_daily.py --lday-path ... --recent-days 45             # 仅日线限制最近自然日
  python run_daily.py --lday-path ... --minline 1                 # 含 1 分钟分时（耗时长）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    p = argparse.ArgumentParser(description="TDX_daily 每日更新入口")
    p.add_argument(
        "--lday-path",
        type=str,
        default="",
        help="通达信 vipdoc 日线根目录（含 sh/lday 等）；与 --download-daily 二选一（未 skip-daily 时）",
    )
    p.add_argument(
        "--download-daily",
        action="store_true",
        help="先官网下载 g4day + datatool day create，再导入（--lday-path 指向 cache-dir/vipdoc）",
    )
    p.add_argument(
        "--cache-dir",
        type=str,
        default=str(ROOT / ".cache" / "web_daily"),
        help="官网日线缓存根（含 vipdoc/、work/）；仅在与 --download-daily 或分时 --minline-extra 等配合时有意义",
    )
    p.add_argument("--db-url", type=str, default=None, help="覆盖环境变量 DB_URL")
    p.add_argument("--skip-daily", action="store_true", help="跳过日线导入")
    p.add_argument("--skip-gbbq", action="store_true")
    p.add_argument("--skip-basic", action="store_true")
    p.add_argument("--skip-factor", action="store_true")
    p.add_argument("--skip-views", action="store_true")
    p.add_argument("--full-basic", action="store_true", help="calc_basic --full")
    p.add_argument("--full-factor", action="store_true", help="calc_factor --full")
    p.add_argument("--recent-days", type=int, default=None)
    p.add_argument("--min-date", type=str, default=None)
    p.add_argument("--max-date", type=str, default=None)
    p.add_argument(
        "--minline",
        type=str,
        default=None,
        metavar="1|5|1,5",
        help="导入分时；不设则跳过（需 embed/datatool 或 --local-vipdoc 见子脚本）",
    )
    p.add_argument(
        "--minline-extra",
        type=str,
        default="",
        help="传给 update_minline_standalone.py 的额外参数（引号包裹），如 '--local-vipdoc /path'",
    )
    args = p.parse_args()

    if not args.skip_daily and not args.download_daily and not args.lday_path.strip():
        p.error("未指定 --lday-path 且未使用 --download-daily（或请加 --skip-daily）")

    env = os.environ.copy()
    if args.db_url:
        env["DB_URL"] = args.db_url

    def run(script: str, extra: list[str]) -> int:
        cmd = [sys.executable, "-u", str(ROOT / script)] + extra
        print("→", " ".join(cmd), flush=True)
        r = subprocess.run(cmd, cwd=str(ROOT), env=env)
        return r.returncode

    cache_root = Path(args.cache_dir).expanduser().resolve()

    if args.download_daily:
        dl_args = ["--cache-dir", str(cache_root)]
        if run("download_g4day_daily.py", dl_args) != 0:
            return 1

    if not args.skip_daily:
        lday = str(cache_root / "vipdoc") if args.download_daily else args.lday_path.strip()
        daily_args = ["--lday-path", lday]
        if args.recent_days is not None:
            daily_args += ["--recent-days", str(args.recent_days)]
        if args.min_date:
            daily_args += ["--min-date", args.min_date]
        if args.max_date:
            daily_args += ["--max-date", args.max_date]
        if run("tdx_import_daily_bar.py", daily_args) != 0:
            return 1

    if not args.skip_gbbq:
        if run("import_gbbq_standalone.py", []) != 0:
            return 1

    if not args.skip_basic:
        bargs = ["--full"] if args.full_basic else []
        if run("calc_basic_standalone.py", bargs) != 0:
            return 1

    if not args.skip_factor:
        fargs = ["--full"] if args.full_factor else []
        if run("calc_factor_standalone.py", fargs) != 0:
            return 1

    if not args.skip_views:
        if run("create_adj_views_standalone.py", []) != 0:
            return 1

    if args.minline:
        mex = args.minline_extra.split() if args.minline_extra.strip() else []
        if run("update_minline_standalone.py", ["--minline", args.minline] + mex) != 0:
            return 1

    print("✅ run_daily：流程已全部成功结束", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
