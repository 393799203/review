#!/usr/bin/env python3
r"""
纯 Python 复现 tdx2db 的 calc_basic：依赖 raw_stocks_daily + raw_gbbq，
计算基础行情并写入 tdx.raw_stocks_basic（与 tdx2db/calc/basic.go 对齐）。

不依赖 Go。需: pip install psycopg2-binary

逻辑来源:
  - tdx2db/calc/basic.go: ExportStockBasicToCSV, processStockBasic, CalculateStockBasic,
    mergeXdxrFromGbbq, calculatePreClosePrice, isShareCategory, buildGbbqIndex, buildStateIndex

用法:
  python calc_basic_standalone.py                    # 增量（默认）
  python calc_basic_standalone.py --full             # 清空 raw_stocks_basic 后全量重算
  python calc_basic_standalone.py --db-url "postgresql://..."
  python calc_basic_standalone.py --limit-symbols 50 # 仅处理前 N 个标的（调试）

注意: 若 basic 表里已有数据、但仅为部分标的，增量模式无法为「从未写入的标的」补全历史
（与 tdx2db 行为一致）。此时请使用 --full 清空后重算。
"""
from __future__ import annotations

import argparse
import bisect
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()


@dataclass
class StockData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    amount: float
    volume: int
    d: date


@dataclass
class GbbqData:
    category: int
    symbol: str
    d: date
    c1: float
    c2: float
    c3: float
    c4: float


@dataclass
class StockBasic:
    d: date
    symbol: str
    close: float
    preclose: float
    change_pct: float
    amplitude: float
    turnover: float
    floatmv: float
    totalmv: float


@dataclass
class IncrementState:
    prev_close: float
    last_post_float: float
    last_post_total: float


@dataclass
class XdxrInfo:
    fenhong: float = 0.0
    peigu: float = 0.0
    peigujia: float = 0.0
    songzhuangu: float = 0.0


def is_share_category(cat: int) -> bool:
    return cat in (2, 3, 5, 7, 8, 9, 10)


def build_gbbq_index(rows: list[GbbqData]) -> dict[str, list[GbbqData]]:
    index: dict[str, list[GbbqData]] = {}
    for r in rows:
        index.setdefault(r.symbol, []).append(r)
    return index


def get_gbbq_by_symbol(index: dict[str, list[GbbqData]], symbol: str) -> list[GbbqData]:
    return index.get(symbol, [])


def merge_xdxr_from_gbbq(m: dict[int, XdxrInfo], idx: int, data: GbbqData) -> None:
    if idx not in m:
        m[idx] = XdxrInfo()
    info = m[idx]
    info.fenhong += data.c1
    info.peigu += data.c2
    info.songzhuangu += data.c3
    if data.c4 > 0:
        info.peigujia = data.c4


def calculate_pre_close_price(prev_close: float, info: XdxrInfo | None) -> float:
    if info is None:
        return prev_close
    denominator = 10 + info.peigu + info.songzhuangu
    if denominator == 0:
        return prev_close
    numerator = (prev_close * 10 - info.fenhong) + (info.peigu * info.peigujia)
    return numerator / denominator


def build_state_index(rows: list[tuple]) -> dict[str, IncrementState]:
    """rows: (symbol, date, close, floatmv, totalmv) 已按 symbol, date 升序。"""
    index: dict[str, IncrementState] = {}
    for symbol, _d, close, floatmv, totalmv in rows:
        if close == 0:
            continue
        last_post_float = floatmv / close / 10000
        last_post_total = totalmv / close / 10000
        index[symbol] = IncrementState(
            prev_close=close,
            last_post_float=last_post_float,
            last_post_total=last_post_total,
        )
    return index


def calculate_stock_basic(
    stock_data: list[StockData],
    gbbq_data: list[GbbqData],
    initial_state: IncrementState | None,
) -> list[StockBasic]:
    if not stock_data:
        return []

    date_fmt = "%Y-%m-%d"
    date_map = {sd.d.strftime(date_fmt): i for i, sd in enumerate(stock_data)}
    dates_sorted = [sd.d for sd in stock_data]

    xdxr_map: dict[int, XdxrInfo] = {}
    shares_list: list[GbbqData] = []

    for item in gbbq_data:
        if item.category == 1:
            ds = item.d.strftime(date_fmt)
            if ds in date_map:
                merge_xdxr_from_gbbq(xdxr_map, date_map[ds], item)
            else:
                idx = bisect.bisect_left(dates_sorted, item.d)
                if idx < len(stock_data):
                    merge_xdxr_from_gbbq(xdxr_map, idx, item)
        elif is_share_category(item.category):
            shares_list.append(item)

    shares_list.sort(key=lambda x: x.d)

    current_float = 0.0
    current_total = 0.0
    if initial_state is not None:
        current_float = initial_state.last_post_float
        current_total = initial_state.last_post_total

    share_idx = 0
    share_len = len(shares_list)
    results: list[StockBasic] = []

    for i, sd in enumerate(stock_data):
        basic_close = sd.close
        if i == 0:
            if initial_state is not None:
                prev_close = initial_state.prev_close
            else:
                prev_close = sd.close
        else:
            prev_close = stock_data[i - 1].close

        info = xdxr_map.get(i)
        preclose = calculate_pre_close_price(prev_close, info)

        change_pct = 0.0
        amplitude = 0.0
        if preclose > 0:
            change_pct = math.floor((sd.close - preclose) / preclose * 100 * 100 + 0.5) / 100
            amplitude = math.floor((sd.high - sd.low) / preclose * 100 * 100 + 0.5) / 100

        while share_idx < share_len and not (shares_list[share_idx].d > sd.d):
            current_float = shares_list[share_idx].c3
            current_total = shares_list[share_idx].c4
            share_idx += 1

        turnover = 0.0
        floatmv = 0.0
        totalmv = 0.0
        if current_float > 0:
            # TDX .day 的 volume 单位是「手」（1 手 = 100 股），GBBQ c3 单位是万股，
            # 换手率(%) = 手数 * 100 / (万股 * 10000)
            vol_float = float(sd.volume) * 100
            val = vol_float / (current_float * 10000)
            turnover = math.floor(val * 1000000 + 0.5) / 1000000
            fmv = current_float * 10000 * sd.close
            floatmv = math.floor(fmv * 100 + 0.5) / 100
        if current_total > 0:
            tmv = current_total * 10000 * sd.close
            totalmv = math.floor(tmv * 100 + 0.5) / 100

        results.append(
            StockBasic(
                d=sd.d,
                symbol=sd.symbol,
                close=basic_close,
                preclose=preclose,
                change_pct=change_pct,
                amplitude=amplitude,
                turnover=turnover,
                floatmv=floatmv,
                totalmv=totalmv,
            )
        )

    return results


def _to_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return v


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tdx.raw_stocks_basic (
                "date" DATE NOT NULL,
                symbol TEXT NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                preclose DOUBLE PRECISION NOT NULL,
                change_pct DOUBLE PRECISION NOT NULL,
                amplitude DOUBLE PRECISION NOT NULL,
                turnover DOUBLE PRECISION NOT NULL,
                floatmv DOUBLE PRECISION NOT NULL,
                totalmv DOUBLE PRECISION NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_stocks_basic_symbol_date
            ON tdx.raw_stocks_basic (symbol, date);
            """
        )
    conn.commit()


def load_all_gbbq(conn) -> list[GbbqData]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT category, symbol, date, c1, c2, c3, c4
            FROM tdx.raw_gbbq
            ORDER BY symbol, date
            """
        )
        rows = cur.fetchall()
    out: list[GbbqData] = []
    for r in rows:
        out.append(
            GbbqData(
                category=int(r[0]),
                symbol=str(r[1]),
                d=_to_date(r[2]),
                c1=float(r[3] or 0),
                c2=float(r[4] or 0),
                c3=float(r[5] or 0),
                c4=float(r[6] or 0),
            )
        )
    return out


def get_distinct_symbols(conn, limit: int | None) -> list[str]:
    sql = "SELECT DISTINCT symbol FROM tdx.raw_stocks_daily ORDER BY symbol"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    with conn.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]


def get_max_basic_date(conn) -> date | None:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(date) FROM tdx.raw_stocks_basic")
        r = cur.fetchone()
    if not r or r[0] is None:
        return None
    return _to_date(r[0])


def query_stock_data(conn, symbol: str, start_date: date | None) -> list[StockData]:
    if start_date is None:
        sql = """
            SELECT symbol, open, high, low, close, amount, volume, date
            FROM tdx.raw_stocks_daily
            WHERE symbol = %s
            ORDER BY date ASC
        """
        args = (symbol,)
    else:
        sql = """
            SELECT symbol, open, high, low, close, amount, volume, date
            FROM tdx.raw_stocks_daily
            WHERE symbol = %s AND date >= %s
            ORDER BY date ASC
        """
        args = (symbol, start_date)
    with conn.cursor() as cur:
        cur.execute(sql, args)
        rows = cur.fetchall()
    out: list[StockData] = []
    for r in rows:
        out.append(
            StockData(
                symbol=str(r[0]),
                open=float(r[1]),
                high=float(r[2]),
                low=float(r[3]),
                close=float(r[4]),
                amount=float(r[5]),
                volume=int(r[6]),
                d=_to_date(r[7]),
            )
        )
    return out


def get_basics_since(conn, since: date) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, date, close, floatmv, totalmv
            FROM tdx.raw_stocks_basic
            WHERE date >= %s
            ORDER BY symbol, date
            """,
            (since,),
        )
        return [
            (str(r[0]), _to_date(r[1]), float(r[2]), float(r[3]), float(r[4]))
            for r in cur.fetchall()
        ]


def get_latest_basic_by_symbol(conn, symbol: str) -> StockBasic | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date, symbol, close, preclose, change_pct, amplitude, turnover, floatmv, totalmv
            FROM tdx.raw_stocks_basic
            WHERE symbol = %s
            ORDER BY date DESC
            LIMIT 1
            """,
            (symbol,),
        )
        r = cur.fetchone()
    if not r:
        return None
    return StockBasic(
        d=_to_date(r[0]),
        symbol=str(r[1]),
        close=float(r[2]),
        preclose=float(r[3]),
        change_pct=float(r[4]),
        amplitude=float(r[5]),
        turnover=float(r[6]),
        floatmv=float(r[7]),
        totalmv=float(r[8]),
    )


def insert_basics(conn, basics: list[StockBasic], batch: int) -> int:
    from psycopg2.extras import execute_values

    if not basics:
        return 0
    tuples = [
        (
            b.d,
            b.symbol,
            b.close,
            b.preclose,
            b.change_pct,
            b.amplitude,
            b.turnover,
            b.floatmv,
            b.totalmv,
        )
        for b in basics
    ]
    total = 0
    for i in range(0, len(tuples), batch):
        chunk = tuples[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO tdx.raw_stocks_basic
                (date, symbol, close, preclose, change_pct, amplitude, turnover, floatmv, totalmv)
                VALUES %s
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def process_symbol(
    conn,
    symbol: str,
    gbbq_index: dict[str, list[GbbqData]],
    is_incremental: bool,
    start_date: date | None,
    state_index: dict[str, IncrementState],
) -> list[StockBasic]:
    query_start: date | None = None
    if is_incremental and start_date is not None:
        query_start = start_date + timedelta(days=1)

    stock_data = query_stock_data(conn, symbol, query_start)
    if not stock_data:
        return []

    gbbqs = list(get_gbbq_by_symbol(gbbq_index, symbol))
    if is_incremental and start_date is not None:
        gbbqs = [g for g in gbbqs if g.d > start_date]

    init_state: IncrementState | None = None
    if is_incremental:
        if symbol in state_index:
            init_state = state_index[symbol]
        else:
            last = get_latest_basic_by_symbol(conn, symbol)
            if last is not None and last.close > 0:
                init_state = IncrementState(
                    prev_close=last.close,
                    last_post_float=last.floatmv / last.close / 10000,
                    last_post_total=last.totalmv / last.close / 10000,
                )

    return calculate_stock_basic(stock_data, gbbqs, init_state)


def main() -> None:
    parser = argparse.ArgumentParser(description="calc_basic → tdx.raw_stocks_basic（纯 Python）")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--full", action="store_true", help="TRUNCATE raw_stocks_basic 后全量重算")
    parser.add_argument("--batch", type=int, default=5000, help="每批插入行数")
    parser.add_argument("--limit-symbols", type=int, default=0, metavar="N", help="仅处理前 N 个 symbol（0=全部）")
    args = parser.parse_args()

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        ensure_table(conn)

        if args.full:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE tdx.raw_stocks_basic;")
            conn.commit()
            start_date: date | None = None
            is_incremental = False
            state_index: dict[str, IncrementState] = {}
            print("模式: 全量（已 TRUNCATE raw_stocks_basic）")
        else:
            raw_max = None
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(date) FROM tdx.raw_stocks_daily")
                r = cur.fetchone()
                if r and r[0] is not None:
                    raw_max = _to_date(r[0])
            start_date = get_max_basic_date(conn)
            is_incremental = start_date is not None and start_date.year > 1900
            if is_incremental and raw_max is not None and start_date >= raw_max:
                print("raw_stocks_basic 已追平日线最新日，无需增量。")
                return
            state_index = {}
            if is_incremental and start_date is not None:
                since_rows = get_basics_since(conn, start_date)
                state_index = build_state_index(since_rows)
            print(
                f"模式: {'增量' if is_incremental else '全量(空表)'} | "
                f"basic.max(date)={start_date} | 日线最新={raw_max}"
            )

        print("加载 raw_gbbq …")
        gbbq_rows = load_all_gbbq(conn)
        if not gbbq_rows:
            print("错误: tdx.raw_gbbq 为空，请先运行 import_gbbq_standalone.py", file=sys.stderr)
            sys.exit(1)
        gbbq_index = build_gbbq_index(gbbq_rows)
        print(f"  GBBQ {len(gbbq_rows):,} 条, {len(gbbq_index):,} 个 symbol")

        limit = args.limit_symbols if args.limit_symbols > 0 else None
        symbols = get_distinct_symbols(conn, limit)
        print(f"处理 {len(symbols):,} 个标的 …")

        total_rows = 0
        buf: list[StockBasic] = []
        for idx, sym in enumerate(symbols, 1):
            rows = process_symbol(conn, sym, gbbq_index, is_incremental, start_date, state_index)
            buf.extend(rows)
            if len(buf) >= args.batch:
                total_rows += insert_basics(conn, buf, args.batch)
                buf = []
            if idx % 500 == 0:
                print(f"  … {idx}/{len(symbols)} 标的, 已写入 {total_rows:,} 行")
        if buf:
            total_rows += insert_basics(conn, buf, args.batch)

        print(f"完成: 共写入 tdx.raw_stocks_basic {total_rows:,} 行")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
