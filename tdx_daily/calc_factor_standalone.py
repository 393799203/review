#!/usr/bin/env python3
r"""
纯 Python 复现 tdx2db 的 calc_factor：依赖 raw_stocks_basic（calc_basic）与 raw_gbbq，
计算后复权因子 hfq_factor，写入 tdx.raw_adjust_factor。

算法对齐 tdx2db/calc/fq_quantaxis.go（ExportFactorsToCSV、processFactorSymbol、
calculateFullHfq、calculateIncrementalHfq、updateHfq、buildXdxrDateSet）。

依赖: pip install psycopg2-binary

用法:
  python calc_factor_standalone.py --full    # TRUNCATE 后全标的、全日期的因子（耗时长）
  python calc_factor_standalone.py           # 增量（与 Go 一致的条件跳过）

试跑约一个月（仍按全日 basic 链在内存中推算 hfq，仅写入指定日期区间；可加 --max-symbols 缩小标的）:
  python calc_factor_standalone.py --truncate-before \\
    --export-min-date 2026-04-01 --export-max-date 2026-04-30 \\
    --max-symbols 500
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()


@dataclass
class StockBasic:
    symbol: str
    d: date
    close: float
    preclose: float


@dataclass
class GbbqRow:
    category: int
    symbol: str
    d: date


@dataclass
class FactorRow:
    symbol: str
    d: date
    hfq_factor: float


@dataclass
class FactorState:
    last_hfq: float
    prev_close: float


def _to_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return v


def float_equal(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


def build_gbbq_index(rows: list[GbbqRow]) -> dict[str, list[GbbqRow]]:
    idx: dict[str, list[GbbqRow]] = defaultdict(list)
    for r in rows:
        idx[r.symbol].append(r)
    return dict(idx)


def build_xdxr_date_set(xdxrs: list[GbbqRow]) -> set[date]:
    return {x.d for x in xdxrs if x.category == 1}


def update_hfq(current_hfq: float, prev_close: float, basic: StockBasic, xdxr_dates: set[date]) -> float:
    if basic.d not in xdxr_dates:
        return current_hfq
    if basic.preclose != 0:
        ratio = prev_close / basic.preclose
        if not float_equal(ratio, 1.0):
            return current_hfq * ratio
    return current_hfq


def calculate_full_hfq(basics: list[StockBasic], xdxrs: list[GbbqRow]) -> list[FactorRow]:
    if not basics:
        return []
    xdxr_dates = build_xdxr_date_set(xdxrs)
    results: list[FactorRow] = []
    current_hfq = 1.0
    prev_close = basics[0].close

    results.append(FactorRow(symbol=basics[0].symbol, d=basics[0].d, hfq_factor=current_hfq))

    for i in range(1, len(basics)):
        b = basics[i]
        current_hfq = update_hfq(current_hfq, prev_close, b, xdxr_dates)
        results.append(FactorRow(symbol=b.symbol, d=b.d, hfq_factor=current_hfq))
        prev_close = b.close

    return results


def calculate_incremental_hfq(
    basics: list[StockBasic],
    last_hfq: float,
    prev_close: float,
    xdxrs: list[GbbqRow],
) -> list[FactorRow]:
    if not basics:
        return []
    xdxr_dates = build_xdxr_date_set(xdxrs)
    results: list[FactorRow] = []
    current_hfq = last_hfq
    pc = prev_close

    for b in basics:
        current_hfq = update_hfq(current_hfq, pc, b, xdxr_dates)
        results.append(FactorRow(symbol=b.symbol, d=b.d, hfq_factor=current_hfq))
        pc = b.close

    return results


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tdx.raw_adjust_factor (
                symbol TEXT NOT NULL,
                "date" DATE NOT NULL,
                hfq_factor DOUBLE PRECISION NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_adjust_factor_symbol_date
            ON tdx.raw_adjust_factor (symbol, date);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_raw_adjust_factor_symbol
            ON tdx.raw_adjust_factor (symbol);
            """
        )
    conn.commit()


def load_all_gbbq(conn) -> list[GbbqRow]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT category, symbol, date FROM tdx.raw_gbbq ORDER BY symbol, date"
        )
        rows = cur.fetchall()
    return [GbbqRow(int(r[0]), str(r[1]), _to_date(r[2])) for r in rows]


def get_distinct_symbols(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM tdx.raw_stocks_daily ORDER BY symbol")
        return [r[0] for r in cur.fetchall()]


def get_max_table_date(conn, table: str, schema: str = "tdx") -> date | None:
    with conn.cursor() as cur:
        cur.execute(f'SELECT MAX(date) FROM {schema}."{table}"')
        r = cur.fetchone()
    if not r or r[0] is None:
        return None
    return _to_date(r[0])


def get_basics_by_symbol(conn, symbol: str) -> list[StockBasic]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, date, close, preclose
            FROM tdx.raw_stocks_basic
            WHERE symbol = %s
            ORDER BY date ASC
            """,
            (symbol,),
        )
        rows = cur.fetchall()
    return [
        StockBasic(str(r[0]), _to_date(r[1]), float(r[2]), float(r[3])) for r in rows
    ]


def get_basics_since(conn, since: date) -> list[StockBasic]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, date, close, preclose
            FROM tdx.raw_stocks_basic
            WHERE date >= %s
            ORDER BY symbol, date
            """,
            (since,),
        )
        rows = cur.fetchall()
    return [
        StockBasic(str(r[0]), _to_date(r[1]), float(r[2]), float(r[3])) for r in rows
    ]


def get_latest_factors(conn) -> list[tuple[str, date, float]]:
    """每 symbol 一条：date、hfq_factor 最新。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT symbol, date, hfq_factor
            FROM (
                SELECT symbol, date, hfq_factor,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
                FROM tdx.raw_adjust_factor
            ) t
            WHERE rn = 1
            """
        )
        rows = cur.fetchall()
    return [(str(r[0]), _to_date(r[1]), float(r[2])) for r in rows]


def build_factor_state_index(
    conn, factor_latest: date, basics_map: dict[str, list[StockBasic]]
) -> dict[str, FactorState]:
    latest_factors = get_latest_factors(conn)
    index: dict[str, FactorState] = {}
    for sym, _fd, hfq in latest_factors:
        symbol_basics = basics_map.get(sym, [])
        if not symbol_basics:
            continue
        index[sym] = FactorState(last_hfq=hfq, prev_close=symbol_basics[0].close)
    return index


def process_factor_symbol(
    conn,
    symbol: str,
    gbbq_index: dict[str, list[GbbqRow]],
    is_incremental: bool,
    state_index: dict[str, FactorState],
    basics_map: dict[str, list[StockBasic]],
) -> list[FactorRow]:
    xdxrs = gbbq_index.get(symbol, [])

    if is_incremental:
        state = state_index.get(symbol)
        basics = basics_map.get(symbol, [])

        if state is None:
            if not basics:
                return []
            all_b = get_basics_by_symbol(conn, symbol)
            if not all_b:
                return []
            return calculate_full_hfq(all_b, xdxrs)

        if len(basics) <= 1:
            return []

        new_basics = basics[1:]
        return calculate_incremental_hfq(
            new_basics, state.last_hfq, state.prev_close, xdxrs
        )

    all_b = get_basics_by_symbol(conn, symbol)
    if not all_b:
        return []
    return calculate_full_hfq(all_b, xdxrs)


def insert_factors(conn, rows: list[FactorRow], batch: int) -> int:
    from psycopg2.extras import execute_values

    if not rows:
        return 0
    tuples = [(r.symbol, r.d, r.hfq_factor) for r in rows]
    total = 0
    for i in range(0, len(tuples), batch):
        chunk = tuples[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO tdx.raw_adjust_factor (symbol, date, hfq_factor)
                VALUES %s
                ON CONFLICT (symbol, date) DO UPDATE SET
                    hfq_factor = EXCLUDED.hfq_factor
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def count_adjust_factor_rows(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tdx.raw_adjust_factor")
        return int(cur.fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="calc_factor → tdx.raw_adjust_factor（纯 Python）")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--full", action="store_true", help="TRUNCATE raw_adjust_factor 后全标的、全日期写入（耗时长）")
    parser.add_argument(
        "--truncate-before",
        action="store_true",
        help="开始前 TRUNCATE raw_adjust_factor（可与试跑参数合用）",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=0,
        metavar="N",
        help="只处理按 symbol 排序后的前 N 个标的（0=全部；试跑建议配合 --truncate-before）",
    )
    parser.add_argument(
        "--export-min-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="仅写入该日（含）之后的因子行（须与 --export-max-date 同时使用）",
    )
    parser.add_argument(
        "--export-max-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="仅写入该日（含）之前的因子行",
    )
    parser.add_argument("--batch", type=int, default=8000, help="每批插入行数")
    args = parser.parse_args()

    export_min: date | None = None
    export_max: date | None = None
    if args.export_min_date or args.export_max_date:
        if not args.export_min_date or not args.export_max_date:
            parser.error("试跑导出区间须同时指定 --export-min-date 与 --export-max-date")
        export_min = date.fromisoformat(args.export_min_date)
        export_max = date.fromisoformat(args.export_max_date)
        if export_min > export_max:
            parser.error("--export-min-date 不能晚于 --export-max-date")

    trial_export = export_min is not None
    trial_limit_sym = args.max_symbols > 0
    trial_mode = trial_export or trial_limit_sym

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        ensure_table(conn)

        if args.full:
            if trial_mode:
                parser.error("--full 不能与 --export-* / --max-symbols 同时使用")
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE tdx.raw_adjust_factor;")
            conn.commit()

        if args.truncate_before and not args.full:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE tdx.raw_adjust_factor;")
            conn.commit()

        factor_latest = get_max_table_date(conn, "raw_adjust_factor")
        basic_latest = get_max_table_date(conn, "raw_stocks_basic")

        existing_factors = count_adjust_factor_rows(conn)
        if trial_mode and existing_factors > 0 and not args.full and not args.truncate_before:
            print(
                "错误: 表中已有因子数据。试跑请加 --truncate-before（或先手动清空表）。",
                file=sys.stderr,
            )
            sys.exit(1)

        is_incremental = factor_latest is not None and factor_latest.year > 1900

        if trial_mode:
            is_incremental = False
            state_index: dict[str, FactorState] = {}
            basics_map_inc: dict[str, list[StockBasic]] = {}
            msg = "试跑: 内存中仍按全日 basic 链计算 hfq"
            if trial_limit_sym:
                msg += f"，标的≤{args.max_symbols}"
            if trial_export:
                msg += f"，仅写入 [{export_min} .. {export_max}]"
            print(msg)
        elif is_incremental and basic_latest is not None and basic_latest <= factor_latest:
            print("复权因子已追平 basic 最新日，无需增量（与 Go 一致）。")
            return
        elif args.full:
            state_index = {}
            basics_map_inc = {}
            print("模式: 全量（已 TRUNCATE raw_adjust_factor）")
        else:
            state_index = {}
            basics_map_inc = {}
            if is_incremental and factor_latest is not None:
                basics_since = get_basics_since(conn, factor_latest)
                basics_map_inc = defaultdict(list)
                for b in basics_since:
                    basics_map_inc[b.symbol].append(b)
                basics_map_inc = dict(basics_map_inc)
                state_index = build_factor_state_index(
                    conn, factor_latest, basics_map_inc
                )
            print(
                f"模式: {'增量' if is_incremental else '全量(空表)'} | "
                f"factor.max={factor_latest} | basic.max={basic_latest}"
            )

        print("加载 raw_gbbq …")
        gbbq_rows = load_all_gbbq(conn)
        if not gbbq_rows:
            print("错误: tdx.raw_gbbq 为空", file=sys.stderr)
            sys.exit(1)
        gbbq_index = build_gbbq_index(gbbq_rows)

        symbols = get_distinct_symbols(conn)
        if trial_limit_sym:
            symbols = symbols[: args.max_symbols]
        print(f"处理 {len(symbols):,} 个标的 …")

        def maybe_filter(rows: list[FactorRow]) -> list[FactorRow]:
            if export_min is None:
                return rows
            return [r for r in rows if export_min <= r.d <= export_max]

        total_rows = 0
        buf: list[FactorRow] = []
        for idx, sym in enumerate(symbols, 1):
            rows = process_factor_symbol(
                conn,
                sym,
                gbbq_index,
                is_incremental,
                state_index,
                basics_map_inc,
            )
            buf.extend(maybe_filter(rows))
            if len(buf) >= args.batch:
                total_rows += insert_factors(conn, buf, args.batch)
                buf = []
            if idx % 500 == 0:
                print(f"  … {idx}/{len(symbols)} 标的, 已写入 {total_rows:,} 行")

        if buf:
            total_rows += insert_factors(conn, buf, args.batch)

        print(f"完成: 共写入/更新 tdx.raw_adjust_factor {total_rows:,} 行")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
