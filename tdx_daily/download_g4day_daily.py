#!/usr/bin/env python3
"""
从通达信官网下载日线压缩包（g4day）、解压到 vipdoc/refmhq，并生成 vipdoc/{sh,sz,bj}/lday/*.day。

默认使用内置 **Python 版 NativeDayMerge**（与原 tdx2db 日线合并逻辑等价），**无需** embed/datatool。
可选 ``--use-external-datatool`` 改为调用通达信 ``datatool day create``。

对齐 tdx2db prepareTdxData(..., "day")：下载 zip → refmhq → 合并至 .day。

用法:
  python download_g4day_daily.py [--cache-dir DIR] [--db-url URL] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # type: ignore

from tdx_config import get_db_url
from tdx_datatool_util import default_embed_datatool_path, ensure_datatool_in_work
from tdx_native_day_merge import native_day_merge

PACKAGE_ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger("download_g4day_daily")

G4DAY_URL_TMPL = "https://www.tdx.com.cn/products/data/data/g4day/%s.zip"
DOWNLOAD_TIMEOUT_SEC = 120
DATATOOL_START = "19901201"  # 仅 --use-external-datatool 时使用


def _ensure_logger(verbose: bool) -> None:
    if LOG.handlers:
        return
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def _dates_to_download(latest_in_db: date | None, today: date) -> List[date]:
    """从 latest_in_db 的下一自然日到 today（含）。"""
    if latest_in_db is None:
        start = today - timedelta(days=1)
    else:
        start = latest_in_db + timedelta(days=1)
    out: List[date] = []
    d = start
    while d <= today:
        out.append(d)
        d += timedelta(days=1)
    return out


def _fetch_latest_daily_date(db_url: str) -> date | None:
    if psycopg2 is None:
        raise RuntimeError("需要 psycopg2：pip install psycopg2-binary")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT MAX("date")::date FROM tdx.raw_stocks_daily')
            row = cur.fetchone()
            if row and row[0] is not None:
                return row[0]
    finally:
        conn.close()
    return None


def download_file(url: str, dest: Path, timeout: int = DOWNLOAD_TIMEOUT_SEC) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; TDXDaily/1.0)"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                return False
            data = resp.read()
        dest.write_bytes(data)
        return True
    except (HTTPError, URLError, OSError, TimeoutError) as e:
        LOG.debug("download fail %s: %s", url, e)
        return False


def unzip_to(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)


def write_datatool_ini_day(work_dir: Path, vipdoc_dir: Path) -> None:
    """日线：WORKPATH 指向 vipdoc/refmhq（下载解压目录），DOCPATH 为 vipdoc 根。"""
    doc = str(vipdoc_dir.resolve()).replace("\\", "/") + "/"
    work = str((vipdoc_dir / "refmhq").resolve()).replace("\\", "/") + "/"
    ini = work_dir / "datatool.ini"
    ini.write_text(
        "\n".join(
            [
                "[WSCFG]",
                f"WORKPATH={work}",
                f"DOCPATH={doc}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_datatool_day(datatool_bin: Path, work_dir: Path, end_date: date) -> None:
    end_s = end_date.strftime("%Y%m%d")
    cmd = [str(datatool_bin), "day", "create", DATATOOL_START, end_s]
    LOG.info("运行: %s (cwd=%s)", " ".join(cmd), work_dir)
    try:
        subprocess.run(cmd, cwd=str(work_dir), check=True)
    except OSError as e:
        # Windows: WinError 193 非有效 Win32 应用（常为 Linux ELF）
        if getattr(e, "winerror", None) == 193:
            raise RuntimeError(
                "无法启动 datatool：当前文件不是 Windows 可执行程序（多为误用 Linux 版 embed/datatool）。"
                "请放置通达信 Windows 版 datatool.exe，见 embed/README.txt。"
            ) from e
        raise


def prepare_tdx_data_day(
    vipdoc_dir: Path,
    today: date,
    latest_in_db: date | None,
    dry_run: bool,
) -> List[date]:
    """
    下载并解压到 vipdoc/refmhq；返回成功下载的日期列表（与 Go 一致：逐自然日尝试，失败则跳过）。
    """
    refmhq = vipdoc_dir / "refmhq"
    refmhq.mkdir(parents=True, exist_ok=True)

    candidates = _dates_to_download(latest_in_db, today)
    valid: List[date] = []
    for d in candidates:
        ds = d.strftime("%Y%m%d")
        url = G4DAY_URL_TMPL % ds
        zip_name = f"{ds}day.zip"
        zip_path = refmhq / zip_name
        if dry_run:
            LOG.info("[dry-run] 将下载 %s -> %s", url, zip_path)
            valid.append(d)
            continue
        if download_file(url, zip_path):
            try:
                unzip_to(zip_path, refmhq)
                valid.append(d)
                LOG.info("已下载并解压 %s", zip_name)
            except zipfile.BadZipFile:
                LOG.warning("损坏 zip，跳过: %s", zip_path)
                try:
                    zip_path.unlink(missing_ok=True)
                except OSError:
                    pass
        else:
            LOG.debug("无数据或失败: %s", ds)
    return valid


def main() -> int:
    parser = argparse.ArgumentParser(
        description="官网日线下载 + refmhq→lday（默认内置 NativeDayMerge，无需 datatool）"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=str(PACKAGE_ROOT / ".cache" / "web_daily"),
        help="缓存根目录，其下含 vipdoc/ 与 work/",
    )
    parser.add_argument("--db-url", type=str, default=None, help="覆盖 DB_URL")
    parser.add_argument("--today", type=str, default=None, help="调试：YYYY-MM-DD，默认今天")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要下载的日期")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--use-external-datatool",
        action="store_true",
        help="使用通达信 datatool day create 替代内置 Python 合并",
    )
    parser.add_argument(
        "--datatool",
        type=str,
        default=str(default_embed_datatool_path(PACKAGE_ROOT)),
        help="仅与 --use-external-datatool 合用：datatool 可执行文件路径",
    )
    parser.add_argument(
        "--skip-datatool",
        action="store_true",
        help="仅下载解压，不合并 .day（调试用）",
    )
    args = parser.parse_args()
    _ensure_logger(args.verbose)

    today = date.today()
    if args.today:
        today = date.fromisoformat(args.today)

    cache = Path(args.cache_dir).expanduser().resolve()
    vipdoc = cache / "vipdoc"
    work_dir = cache / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    vipdoc.mkdir(parents=True, exist_ok=True)

    db_url = args.db_url or get_db_url()
    latest = None
    if not args.dry_run:
        latest = _fetch_latest_daily_date(db_url)
        if latest:
            LOG.info("库中日线最新日期: %s", latest)
        else:
            LOG.info("库中无日线或 MAX(date) 为空，将从昨日起尝试下载窗口")

    valid_dates = prepare_tdx_data_day(vipdoc, today, latest, dry_run=args.dry_run)
    if not valid_dates:
        LOG.info("无需更新（无新工作日数据或未下载到 zip）")
        return 0

    if args.dry_run:
        return 0

    if args.skip_datatool:
        LOG.info("已跳过日线合并，vipdoc=%s", vipdoc)
        return 0

    if args.use_external_datatool:
        end_date = max(valid_dates)
        embed_bin = Path(args.datatool)
        try:
            dt = ensure_datatool_in_work(work_dir, embed_bin)
        except FileNotFoundError as e:
            LOG.error("%s", e)
            return 1
        except RuntimeError as e:
            LOG.error("%s", e)
            return 1

        write_datatool_ini_day(work_dir, vipdoc)
        try:
            run_datatool_day(dt, work_dir, end_date)
        except RuntimeError as e:
            LOG.error("%s", e)
            return 1
        except subprocess.CalledProcessError as e:
            LOG.error("datatool 失败: %s", e)
            return e.returncode or 1
    else:
        try:
            native_day_merge(vipdoc)
        except RuntimeError as e:
            LOG.error("%s", e)
            return 1

    LOG.info("完成。导入请使用: python tdx_import_daily_bar.py --lday-path %s ...", vipdoc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
