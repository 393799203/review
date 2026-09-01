#!/usr/bin/env python3
r"""
纯 Python 复现 tdx2db 的 update_1min / update_5min（workflow/tasks.go）：

1. 取库内 raw_stocks_1min / raw_stocks_5min 的 MAX(datetime)::date 作为「最新日」（空表则与 Go 一致：视为需从「昨天」开始补）；
2. 自 latest+1 起至「今天」逐日历日下载
   https://www.tdx.com.cn/products/data/data/g4tic/{YYYYMMDD}tic.zip，解压到 <vipdoc>/newdatetick/；
3. 若本批成功下载的交易日数量 >= 30，报错退出（与 Go 一致，防止一次补太多分时）；
4. 若有新数据：在 work 目录写入 datatool.ini（DOCPATH/WORKPATH 指向本机 vipdoc），调用嵌入的 datatool：
     datatool tick create 19901201 <end>
     datatool min create 19901201 <end>
   end 为本批 validDates 的最后一日（与 Go prepareTdxData 一致）；
5. 在 vipdoc 根下递归收集 .01 / .5，按 tdx/kline.go processMinFile 解析，批量 UPSERT 到
   tdx.raw_stocks_1min / tdx.raw_stocks_5min。

分时文件前缀过滤与 Go executeUpdate1Min/5Min 一致：使用 ValidPrefixes（股票+指数+板块前缀）。

依赖: pip install psycopg2-binary

datatool 二进制：Linux 默认为 embed/datatool（常为 32 位 ELF，可能需要 libc6-i386）。
Windows 需使用通达信自带的 datatool.exe（默认 embed/datatool.exe）。
若无法执行，可用通达信客户端生成 vipdoc 后加 --local-vipdoc 跳过下载与 datatool。

用法示例:
  python update_minline_standalone.py --minline 1
  python update_minline_standalone.py --minline 5
  python update_minline_standalone.py --minline 1,5
  python update_minline_standalone.py --local-vipdoc /path/to/vipdoc --minline 1   # 仅扫描导入已有 .01/.5
  python update_minline_standalone.py --minline 1 --today 2026-05-08 --truncate-before --cache-dir /tmp/tdx_demo
       # 演示单日：当作「今天」为 2026-05-08，空表等价从 20260507 补一日 tic（会先清空 1 分钟表）
"""
from __future__ import annotations

import argparse
import struct
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from tdx_config import PACKAGE_ROOT, get_db_url
from tdx_datatool_util import default_embed_datatool_path, ensure_datatool_in_work

DEFAULT_DB_URL = get_db_url()

# cmd/common.go + cmd/convert.go 北交所扩展（convert 对分钟额外带有，cron 的 ValidPrefixes 不含 bj43 等，
# 此处与 tasks.go 的 args.ValidPrefixes 一致：仅 ValidPrefixes）
MARKET_PREFIXES = (
    "sz30",
    "sz00",
    "sh60",
    "sh68",
    "bj920",
)
INDEX_PREFIXES = (
    "sh000300",
    "sh000905",
    "sh000852",
    "sh000001",
    "sz399001",
    "sz399106",
    "sz399006",
    "sh000680",
    "sh000688",
    "bj899050",
)
BLOCK_PREFIXES = ("sh880", "sh881")
VALID_PREFIXES: tuple[str, ...] = MARKET_PREFIXES + INDEX_PREFIXES + BLOCK_PREFIXES

G4TIC_URL = "https://www.tdx.com.cn/products/data/data/g4tic/{date}tic.zip"
DATATOOL_START = "19901201"
# tdx/kline.go：分时与日线共用 recordSize=32；前 28 字节为字段，末 4 字节对齐填充
MIN_RECORD_FMT = "<HHIIIIfI"
MIN_PAYLOAD_SIZE = 28
MIN_RECORD_SIZE = 32

@dataclass
class MinRow:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    amount: float
    volume: int
    dt: datetime


def parse_minline_choice(s: str) -> tuple[bool, bool]:
    t = s.strip().replace(" ", "")
    if t in ("1",):
        return True, False
    if t in ("5",):
        return False, True
    if t in ("1,5", "5,1"):
        return True, True
    raise ValueError("--minline 仅支持 1、5、1,5")


def daterange_inclusive(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def parse_min_datetime(date_raw: int, time_raw: int, tz) -> datetime | None:
    """tdx/kline.go parseDateTime"""
    year = date_raw // 2048 + 2004
    month = (date_raw % 2048) // 100
    day = (date_raw % 2048) % 100
    hour = time_raw // 60
    minute = time_raw % 60
    if month < 1 or month > 12 or day < 1 or day > 31:
        return None
    return datetime(year, month, day, hour, minute, 0, tzinfo=tz)


def process_min_file(path: Path, symbol: str, tz) -> list[MinRow]:
    """tdx/kline.go processMinFile"""
    data = path.read_bytes()
    if len(data) % MIN_RECORD_SIZE != 0:
        raise ValueError(f"invalid file size {len(data)}: {path}")
    n = len(data) // MIN_RECORD_SIZE
    rows: list[MinRow] = []
    for i in range(n):
        chunk = data[i * MIN_RECORD_SIZE : (i + 1) * MIN_RECORD_SIZE]
        dr, tr, o, h, lo, c, amt, vol = struct.unpack(MIN_RECORD_FMT, chunk[:MIN_PAYLOAD_SIZE])
        t = parse_min_datetime(int(dr), int(tr), tz)
        if t is None:
            continue
        rows.append(
            MinRow(
                symbol=symbol,
                open=o / 100.0,
                high=h / 100.0,
                low=lo / 100.0,
                close=c / 100.0,
                amount=float(amt),
                volume=int(vol),
                dt=t,
            )
        )
    return rows


def collect_min_files(vipdoc_root: Path, suffix: str, prefixes: tuple[str, ...]) -> list[Path]:
    """tdx/kline.go collectFiles"""
    out: list[Path] = []
    for p in vipdoc_root.rglob(f"*{suffix}"):
        if not p.is_file():
            continue
        if not p.name.endswith(suffix):
            continue
        sym = p.name[: -len(suffix)]
        if not prefixes or any(sym.startswith(pre) for pre in prefixes):
            out.append(p)
    return sorted(out)


def download_file(url: str, dest: Path) -> int:
    """返回 HTTP 状态码；404 返回 404。"""
    req = urllib.request.Request(url, headers={"User-Agent": "tdx2db-python/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            code = resp.getcode()
            if code != 200:
                return code
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(resp.read())
            return 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 404
        raise


def unzip_to(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)


def prepare_tdx_data_tic(vipdoc_dir: Path, today: date, latest: date) -> list[date]:
    """
    workflow/tasks.go prepareTdxData(..., "tic")：下载并解压；返回 HTTP 200 的日历日列表。
    不在此调用 datatool（由调用方在 validDates 非空时统一调用，与 Go 一致）。
    """
    newdatetick = vipdoc_dir / "newdatetick"
    newdatetick.mkdir(parents=True, exist_ok=True)

    valid_dates: list[date] = []
    start = latest + timedelta(days=1)
    for d in daterange_inclusive(start, today):
        ds = d.strftime("%Y%m%d")
        url = G4TIC_URL.format(date=ds)
        zip_name = f"{ds}tic.zip"
        zip_path = newdatetick / zip_name
        code = download_file(url, zip_path)
        if code == 200:
            print(f"✅ 已下载 {ds} 的分时压缩包")
            try:
                unzip_to(zip_path, newdatetick)
            except Exception as e:
                print(f"⚠️ 解压 {zip_path} 失败: {e}")
                continue
            valid_dates.append(d)
        elif code == 404:
            print(f"🟡 {ds} 非交易日或数据尚未更新")
        else:
            raise RuntimeError(f"下载 {url} 意外状态码 {code}")

    return valid_dates


def write_datatool_ini(work_dir: Path, vipdoc_dir: Path) -> None:
    """覆盖写入 datatool.ini，使 DOCPATH/WORKPATH 指向本机缓存（修正 embed 内硬编码路径）。"""
    doc = str(vipdoc_dir.resolve()).replace("\\", "/")
    if not doc.endswith("/"):
        doc += "/"
    work = str((vipdoc_dir / "newdatetick").resolve()).replace("\\", "/")
    if not work.endswith("/"):
        work += "/"
    ini = work_dir / "datatool.ini"
    ini.write_text(f"[WSCFG]\nWORKPATH={work}\nDOCPATH={doc}\n", encoding="utf-8")


def run_datatool(datatool_bin: Path, work_dir: Path, end_date: date) -> None:
    """tdx/datatool.go DatatoolCreate"""
    end_s = end_date.strftime("%Y%m%d")
    for sub in ("tick", "min"):
        cmd = [str(datatool_bin), sub, "create", DATATOOL_START, end_s]
        print(f"🐢 执行: {' '.join(cmd)} (cwd={work_dir})")
        try:
            r = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True, errors="replace")
        except OSError as e:
            if getattr(e, "winerror", None) == 193:
                raise RuntimeError(
                    "无法启动 datatool：不是有效的 Windows 可执行文件（常为 Linux ELF）。"
                    "请放置 embed/datatool.exe，见 embed/README.txt。"
                ) from e
            raise
        if r.returncode != 0:
            raise RuntimeError(
                f"datatool {sub} 失败 exit={r.returncode}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
            )


def ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        for name in ("raw_stocks_1min", "raw_stocks_5min"):
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS tdx.{name} (
                    symbol TEXT NOT NULL,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    amount DOUBLE PRECISION NOT NULL,
                    volume BIGINT NOT NULL,
                    datetime TIMESTAMPTZ NOT NULL
                );
                """
            )
            cur.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_{name}_symbol_dt
                ON tdx.{name} (symbol, datetime);
                """
            )
    conn.commit()


def get_latest_table_date(conn, table: str):
    """对齐 database/postgresql GetLatestDate(..., 'datetime') — MAX(datetime)::date"""
    with conn.cursor() as cur:
        cur.execute(f"SELECT MAX(datetime)::date FROM tdx.{table}")
        row = cur.fetchone()
        return row[0]


def insert_min_rows(conn, table: str, rows: list[MinRow], batch: int) -> int:
    from psycopg2.extras import execute_values

    if not rows:
        return 0
    tuples = [(r.symbol, r.open, r.high, r.low, r.close, r.amount, r.volume, r.dt) for r in rows]
    total = 0
    for i in range(0, len(tuples), batch):
        chunk = tuples[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO tdx.{table}
                    (symbol, open, high, low, close, amount, volume, datetime)
                VALUES %s
                ON CONFLICT (symbol, datetime) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    amount = EXCLUDED.amount,
                    volume = EXCLUDED.volume
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def scan_and_import(
    conn,
    table: str,
    suffix: str,
    vipdoc_root: Path,
    prefixes: tuple[str, ...],
    batch: int,
    tz,
) -> int:
    paths = collect_min_files(vipdoc_root, suffix, prefixes)
    print(f"📂 {suffix}: 匹配到 {len(paths):,} 个文件")
    buf: list[MinRow] = []
    total = 0
    for idx, p in enumerate(paths, 1):
        sym = p.name[: -len(suffix)]
        buf.extend(process_min_file(p, sym, tz))
        if len(buf) >= batch:
            total += insert_min_rows(conn, table, buf, batch)
            buf = []
        if idx % 2000 == 0:
            print(f"   … 已解析 {idx}/{len(paths)} 文件, 累计写入 {total:,} 行")
    if buf:
        total += insert_min_rows(conn, table, buf, batch)
    return total


def run_one_kind(
    *,
    conn,
    table: str,
    suffix: str,
    need_prepare: bool,
    vipdoc_dir: Path,
    work_dir: Path,
    datatool_bin: Path,
    today: date,
    batch: int,
    prefixes: tuple[str, ...],
    tz,
) -> None:
    latest = get_latest_table_date(conn, table)
    if latest is None:
        print(f"🛑 警告：数据库中没有 {table} 数据")
        print("🚧 将处理今天的数据，历史请自行导入（与 Go getMinLineLatestDate 一致）")
        latest = today - timedelta(days=1)

    print(f"📅 {table} 最新日期为 {latest}")

    valid_dates: list[date] = []
    if need_prepare:
        valid_dates = prepare_tdx_data_tic(vipdoc_dir, today, latest)
        if len(valid_dates) >= 30:
            raise RuntimeError("分时数据超过30天未更新，请手动补齐后继续（与 Go 一致）")
        if valid_dates:
            write_datatool_ini(work_dir, vipdoc_dir)
            tool = ensure_datatool_in_work(work_dir, datatool_bin)
            run_datatool(tool, work_dir, valid_dates[-1])
    else:
        print("📌 --local-vipdoc：跳过下载与 datatool，直接扫描目录")

    if need_prepare and not valid_dates:
        print(f"🌲 {suffix} 分时数据无需更新（本区间无新 tic zip 或非交易日/404）")
        return

    n = scan_and_import(conn, table, suffix, vipdoc_dir, prefixes, batch, tz)
    print(f"🔢 {table}: 本跑写入/更新 {n:,} 行")


def main() -> None:
    parser = argparse.ArgumentParser(description="update_1min / update_5min → PostgreSQL（对齐 tdx2db）")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--minline", required=True, help="1 | 5 | 1,5")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="缓存根目录；默认 ~/.cache/tdx_minline",
    )
    parser.add_argument(
        "--local-vipdoc",
        type=Path,
        default=None,
        help="已有 vipdoc 根目录（含 minute 结构），跳过下载与 datatool",
    )
    parser.add_argument(
        "--datatool",
        type=Path,
        default=default_embed_datatool_path(PACKAGE_ROOT),
        help="datatool 可执行文件路径（Windows 常为 embed/datatool.exe）",
    )
    parser.add_argument("--batch", type=int, default=5000, help="插入批大小")
    parser.add_argument(
        "--today",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="覆盖「今天」日历日（用于调试或补历史）；默认系统当天。决定增量区间上界及空表时的起始推算",
    )
    parser.add_argument(
        "--truncate-before",
        action="store_true",
        help="运行前 TRUNCATE 本次涉及的 raw_stocks_1min / raw_stocks_5min（慎用；演示时可配合 --today）",
    )
    args = parser.parse_args()

    try:
        do1, do5 = parse_minline_choice(args.minline)
    except ValueError as e:
        parser.error(str(e))

    cache_dir = args.cache_dir or (Path.home() / ".cache" / "tdx_minline")
    cache_dir = cache_dir.expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    work_dir = cache_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    if args.local_vipdoc:
        vipdoc_dir = args.local_vipdoc.expanduser().resolve()
        need_prepare = False
    else:
        vipdoc_dir = cache_dir / "vipdoc"
        vipdoc_dir.mkdir(parents=True, exist_ok=True)
        need_prepare = True

    import psycopg2
    from datetime import timezone

    local_tz = datetime.now().astimezone().tzinfo or timezone.utc

    today = date.fromisoformat(args.today) if args.today else date.today()
    conn = psycopg2.connect(args.db_url)
    try:
        ensure_tables(conn)
        truncated = False
        if args.truncate_before:
            with conn.cursor() as cur:
                if do1:
                    cur.execute("TRUNCATE TABLE tdx.raw_stocks_1min;")
                    print("已 TRUNCATE tdx.raw_stocks_1min")
                    truncated = True
                if do5:
                    cur.execute("TRUNCATE TABLE tdx.raw_stocks_5min;")
                    print("已 TRUNCATE tdx.raw_stocks_5min")
                    truncated = True
            conn.commit()
            if truncated:
                print("⚠️ 若后续下载全日为空，分时表将保持为空；演示请勿在生产库随意 --truncate-before")
        if do1:
            run_one_kind(
                conn=conn,
                table="raw_stocks_1min",
                suffix=".01",
                need_prepare=need_prepare,
                vipdoc_dir=vipdoc_dir,
                work_dir=work_dir,
                datatool_bin=args.datatool,
                today=today,
                batch=args.batch,
                prefixes=VALID_PREFIXES,
                tz=local_tz,
            )
        if do5:
            run_one_kind(
                conn=conn,
                table="raw_stocks_5min",
                suffix=".5",
                need_prepare=need_prepare,
                vipdoc_dir=vipdoc_dir,
                work_dir=work_dir,
                datatool_bin=args.datatool,
                today=today,
                batch=args.batch,
                prefixes=VALID_PREFIXES,
                tz=local_tz,
            )
        print("🚀 任务结束")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
