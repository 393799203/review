#!/usr/bin/env python3
r"""
通达信 .day 二进制文件解析并导入 tdx.raw_stocks_daily（tdx2db 兼容）

数据来源可为：**本地客户端 vipdoc**，或先用 **`download_g4day_daily.py`**（官网 **`g4day`** 压缩包 + 内置 **`NativeDayMerge`** 或 **`datatool day`**）生成 **`vipdoc/sh|sz|bj/lday/*.day`** 再指定同一 **`vipdoc` 根目录**。

遍历 lday_path 下 sh/lday、sz/lday、bj/lday（如存在）
所有 .day 文件，解析后写入 PostgreSQL tdx.raw_stocks_daily 表。
volume 使用原始股数（与 tdx2db 一致）。

用法:
    python tdx_import_daily_bar.py [--lday-path PATH] [--db-url URL] [--recent-days N|--min-date YYYY-MM-DD] [--max-date YYYY-MM-DD]
    
依赖: pip install psycopg2-binary
"""
from __future__ import annotations

import argparse
import struct
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()

# 通达信 .day 格式：每 32 字节一条
# 0-3: date(int), 4-7: open, 8-11: high, 12-15: low, 16-19: close
# 20-23: amount(float), 24-27: volume, 28-31: reserved
DAY_RECORD_FMT = "IIIIIfII"
DAY_RECORD_SIZE = 32


def parse_day_file(path: Path, code: str) -> list[dict]:
    """解析单个 .day 文件，返回记录列表"""
    with open(path, "rb") as f:
        buf = f.read()
    n = len(buf) // DAY_RECORD_SIZE
    rows = []
    for i in range(n):
        raw = struct.unpack(DAY_RECORD_FMT, buf[i * DAY_RECORD_SIZE : (i + 1) * DAY_RECORD_SIZE])
        dt, o, h, l, c, amt, vol, _ = raw
        y, m, d = dt // 10000, (dt % 10000) // 100, dt % 100
        rows.append({
            "code": code,
            "trade_date": date(y, m, d),
            "open": o / 100.0,
            "high": h / 100.0,
            "low": l / 100.0,
            "close": c / 100.0,
            "amount": float(amt),
            "volume": vol,  # 股数，与 tdx2db 一致（原 vol/100 为手数，已废弃）
        })
    return rows


def iter_day_files(lday_root: Path) -> Iterator[tuple[Path, str]]:
    """遍历 .day 文件，yield (path, code)。

    1) 标准通达信 vipdoc：lday_path/sh/lday/*.day（sz、bj 同理）
    2) 兼容「扁平」布局：解压/拷贝错误时，根目录下出现名为 ``bj\\lday\\bj430017.day``
       的单文件（反斜杠是文件名的一部分，不是子目录）
    """
    markets = {"sh", "sz", "bj"}
    for mkt in sorted(markets):
        d = lday_root / mkt / "lday"
        if not d.is_dir():
            continue
        for f in d.glob("*.day"):
            yield f, f.stem.lower()

    for f in lday_root.iterdir():
        if not f.is_file():
            continue
        name = f.name
        if not name.endswith(".day"):
            continue
        if "\\" not in name and "/" not in name:
            continue
        normalized = name.replace("\\", "/")
        parts = normalized.split("/")
        if len(parts) < 3 or parts[-2].lower() != "lday":
            continue
        if parts[0].lower() not in markets:
            continue
        code = Path(parts[-1]).stem.lower()
        if code:
            yield f, code


def ensure_schema_and_table(conn):
    """创建 tdx schema 和 raw_stocks_daily 表（tdx2db 兼容）"""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tdx.raw_stocks_daily (
                symbol TEXT NOT NULL,
                "date" DATE NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                volume BIGINT NOT NULL,
                UNIQUE (symbol, date)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_stocks_daily_symbol ON tdx.raw_stocks_daily (symbol);
            CREATE INDEX IF NOT EXISTS idx_raw_stocks_daily_date ON tdx.raw_stocks_daily (date);
        """)
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="通达信 .day → tdx.daily_bar")
    parser.add_argument(
        "--lday-path",
        type=str,
        default=str(Path(__file__).resolve().parent),
        help="日K线根目录（含 sh/lday、sz/lday 等）",
    )
    parser.add_argument("--db-url", type=str, default=DEFAULT_DB_URL, help="PostgreSQL 连接 URL")
    parser.add_argument("--batch", type=int, default=50000, help="每批插入条数")
    parser.add_argument(
        "--min-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="只导入该交易日及之后的记录（与 --recent-days 二选一）",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=None,
        metavar="N",
        help="只导入最近 N 个自然日内的记录（含今天；与 --min-date 二选一）",
    )
    parser.add_argument(
        "--max-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="只导入该交易日及之前的记录（可与 --min-date / --recent-days 合用，用于补历史边界前的数据）",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="显示每个文件的解析进度")
    args = parser.parse_args()

    if args.min_date is not None and args.recent_days is not None:
        parser.error("请只指定 --min-date 或 --recent-days 之一")
    min_trade_date: date | None = None
    if args.min_date:
        min_trade_date = date.fromisoformat(args.min_date)
    elif args.recent_days is not None:
        if args.recent_days < 0:
            parser.error("--recent-days 须为非负整数")
        min_trade_date = date.today() - timedelta(days=args.recent_days)

    max_trade_date: date | None = None
    if args.max_date:
        max_trade_date = date.fromisoformat(args.max_date)
    if min_trade_date is not None and max_trade_date is not None and min_trade_date > max_trade_date:
        parser.error("--min-date 不能晚于 --max-date")

    import psycopg2
    from psycopg2.extras import execute_values

    lday_root = Path(args.lday_path)
    if not lday_root.is_dir():
        print(f"错误：目录不存在 {lday_root}")
        sys.exit(1)

    files = list(iter_day_files(lday_root))
    # 按市场统计
    mkt_count = {}
    for _, code in files:
        mkt = code[:2].lower() if len(code) >= 2 else "?"
        mkt_count[mkt] = mkt_count.get(mkt, 0) + 1
    print(f"发现 {len(files)} 个 .day 文件")
    for mkt in ["sh", "sz", "bj"]:
        if mkt in mkt_count:
            print(f"  - {mkt}/lday: {mkt_count[mkt]} 个文件")
    print(f"数据库: {args.db_url.split('@')[-1] if '@' in args.db_url else 'localhost'}")
    if min_trade_date:
        print(f"日期过滤: trade_date >= {min_trade_date.isoformat()}")
    if max_trade_date:
        print(f"日期过滤: trade_date <= {max_trade_date.isoformat()}")
    print("-" * 50)

    conn = psycopg2.connect(args.db_url)
    ensure_schema_and_table(conn)

    total = 0
    batch_rows = []
    fail_count = 0
    for idx, (path, code) in enumerate(files, 1):
        try:
            rows = parse_day_file(path, code)
        except Exception as e:
            print(f"[{idx}/{len(files)}] 解析失败 {path.name}: {e}")
            fail_count += 1
            continue
        if args.verbose:
            print(f"[{idx}/{len(files)}] {code} {len(rows)} 条 <- {path.relative_to(lday_root)}")
        for r in rows:
            if min_trade_date is not None and r["trade_date"] < min_trade_date:
                continue
            if max_trade_date is not None and r["trade_date"] > max_trade_date:
                continue
            batch_rows.append((
                r["code"],
                r["trade_date"],
                r["open"],
                r["high"],
                r["low"],
                r["close"],
                r["amount"],
                int(r["volume"]),
            ))
        # 按 (symbol, date) 去重
        seen = {}
        for t in batch_rows:
            key = (t[0], t[1])
            seen[key] = t
        batch_rows = list(seen.values())
        if len(batch_rows) >= args.batch:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO tdx.raw_stocks_daily (symbol, date, open, high, low, close, amount, volume)
                    VALUES %s
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        amount = EXCLUDED.amount,
                        volume = EXCLUDED.volume
                    """,
                    batch_rows,
                )
            total += len(batch_rows)
            print(f"  [{idx}/{len(files)}] 已导入 {total:,} 条 (当前: {path.name})")
            batch_rows = []

    if batch_rows:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO tdx.raw_stocks_daily (symbol, date, open, high, low, close, amount, volume)
                VALUES %s
                ON CONFLICT (symbol, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    amount = EXCLUDED.amount,
                    volume = EXCLUDED.volume
                """,
                batch_rows,
            )
        total += len(batch_rows)

    conn.commit()
    conn.close()
    print("-" * 50)
    print(f"完成 | 处理 {len(files) - fail_count}/{len(files)} 个文件 | 导入 {total:,} 条 | 失败 {fail_count} 个")


if __name__ == "__main__":
    main()
