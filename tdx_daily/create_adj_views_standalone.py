#!/usr/bin/env python3
r"""
在 PostgreSQL 中创建与 tdx2db 一致的复权相关视图（对齐 database/postgresql/ddl.go registerViews）：

  - tdx.v_bfq_daily  不复权 OHLC + basic 字段 + hfq_factor + qfq_factor（相对最新日的缩放系数）
  - tdx.v_hfq_daily  后复权 OHLC / preclose（按当日 hfq_factor）
  - tdx.v_qfq_daily  前复权 OHLC / preclose（hfq_factor / 最新 hfq_factor）

依赖表：tdx.raw_stocks_daily、tdx.raw_stocks_basic、tdx.raw_adjust_factor（须先完成日线、calc_basic、calc_factor）。

依赖: pip install psycopg2-binary

用法:
  python create_adj_views_standalone.py
  python create_adj_views_standalone.py --schema tdx --db-url 'postgresql://...'
"""
from __future__ import annotations

import argparse
import sys

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()


def qi(ident: str) -> str:
    """PostgreSQL 双引号标识符"""
    return '"' + ident.replace('"', '""') + '"'


def qobj(schema: str, name: str) -> str:
    return f"{qi(schema)}.{qi(name)}"


def create_views_sql(schema: str) -> list[tuple[str, str]]:
    """(视图名, CREATE OR REPLACE VIEW ... SQL)"""
    daily = qobj(schema, "raw_stocks_daily")
    basic = qobj(schema, "raw_stocks_basic")
    factor = qobj(schema, "raw_adjust_factor")
    v_bfq = qobj(schema, "v_bfq_daily")
    v_hfq = qobj(schema, "v_hfq_daily")
    v_qfq = qobj(schema, "v_qfq_daily")

    # 与 tdx2db/database/postgresql/ddl.go 中 registerViews 一致；列名 date 对 raw 表使用引号避免保留字问题
    bfq = f"""
CREATE OR REPLACE VIEW {v_bfq} AS
WITH latest_factors AS (
    SELECT DISTINCT ON (symbol) symbol, hfq_factor AS latest_hfq
    FROM {factor}
    ORDER BY symbol, "date" DESC
)
SELECT
    s.symbol     AS symbol,
    s."date"    AS date,
    s.open       AS open,
    s.high       AS high,
    s.low        AS low,
    s.close      AS close,
    b.preclose   AS preclose,
    s.volume     AS volume,
    s.amount     AS amount,
    b.turnover   AS turnover,
    b.floatmv    AS floatmv,
    b.totalmv    AS totalmv,
    b.change_pct AS change_pct,
    b.amplitude  AS amplitude,
    COALESCE(f.hfq_factor, 1) AS hfq_factor,
    COALESCE(f.hfq_factor, 1) / COALESCE(lf.latest_hfq, 1) AS qfq_factor
FROM {daily} s
LEFT JOIN {factor} f ON s.symbol = f.symbol AND s."date" = f."date"
LEFT JOIN latest_factors lf ON s.symbol = lf.symbol
LEFT JOIN {basic} b ON s.symbol = b.symbol AND s."date" = b."date"
"""

    hfq = f"""
CREATE OR REPLACE VIEW {v_hfq} AS
SELECT
    s.symbol   AS symbol,
    s."date"   AS date,
    ROUND((s.open  * COALESCE(f.hfq_factor, 1))::numeric, 2) AS open,
    ROUND((s.high  * COALESCE(f.hfq_factor, 1))::numeric, 2) AS high,
    ROUND((s.low   * COALESCE(f.hfq_factor, 1))::numeric, 2) AS low,
    ROUND((s.close * COALESCE(f.hfq_factor, 1))::numeric, 2) AS close,
    ROUND((b.preclose * COALESCE(f.hfq_factor, 1))::numeric, 2) AS preclose,
    s.volume     AS volume,
    s.amount     AS amount,
    b.turnover   AS turnover,
    b.floatmv    AS floatmv,
    b.totalmv    AS totalmv,
    b.change_pct AS change_pct,
    b.amplitude  AS amplitude,
    COALESCE(f.hfq_factor, 1) AS hfq_factor
FROM {daily} s
LEFT JOIN {factor} f ON s.symbol = f.symbol AND s."date" = f."date"
LEFT JOIN {basic} b ON s.symbol = b.symbol AND s."date" = b."date"
"""

    qfq = f"""
CREATE OR REPLACE VIEW {v_qfq} AS
WITH latest_factors AS (
    SELECT DISTINCT ON (symbol) symbol, hfq_factor AS latest_hfq
    FROM {factor}
    ORDER BY symbol, "date" DESC
)
SELECT
    s.symbol   AS symbol,
    s."date"   AS date,
    ROUND((s.open  * COALESCE(f.hfq_factor, 1) / COALESCE(lf.latest_hfq, 1))::numeric, 2) AS open,
    ROUND((s.high  * COALESCE(f.hfq_factor, 1) / COALESCE(lf.latest_hfq, 1))::numeric, 2) AS high,
    ROUND((s.low   * COALESCE(f.hfq_factor, 1) / COALESCE(lf.latest_hfq, 1))::numeric, 2) AS low,
    ROUND((s.close * COALESCE(f.hfq_factor, 1) / COALESCE(lf.latest_hfq, 1))::numeric, 2) AS close,
    ROUND((b.preclose * COALESCE(f.hfq_factor, 1) / COALESCE(lf.latest_hfq, 1))::numeric, 2) AS preclose,
    s.volume     AS volume,
    s.amount     AS amount,
    b.turnover   AS turnover,
    b.floatmv    AS floatmv,
    b.totalmv    AS totalmv,
    b.change_pct AS change_pct,
    b.amplitude  AS amplitude,
    COALESCE(f.hfq_factor, 1) / COALESCE(lf.latest_hfq, 1) AS qfq_factor
FROM {daily} s
LEFT JOIN {factor} f ON s.symbol = f.symbol AND s."date" = f."date"
LEFT JOIN latest_factors lf ON s.symbol = lf.symbol
LEFT JOIN {basic} b ON s.symbol = b.symbol AND s."date" = b."date"
"""

    return [
        ("v_bfq_daily", bfq),
        ("v_hfq_daily", hfq),
        ("v_qfq_daily", qfq),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="创建 tdx2db 同款复权视图（BFQ/HFQ/QFQ）")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--schema", default="tdx", help="表与视图所在 schema，默认 tdx")
    args = parser.parse_args()

    import psycopg2

    sqls = create_views_sql(args.schema)
    conn = psycopg2.connect(args.db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {qi(args.schema)};")
            for name, sql in sqls:
                cur.execute(sql)
                print(f"已创建/替换视图 {args.schema}.{name}")
        conn.commit()
        print("完成。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
