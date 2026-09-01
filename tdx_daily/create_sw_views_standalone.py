#!/usr/bin/env python3
r"""
创建申万行业日线聚合视图 tdx.v_sw_industry_daily：

  按 date × 申万一级 × 申万二级 聚合 tdx.raw_stocks_basic（仅 join is_latest=1 的行业归属），
  avg(change_pct) 为行业涨跌幅，stock_count 为成分股数量。
  视图同时包含两级聚合行：申万一级行（sw2_code/sw2_name 为 NULL）与申万二级行。

依赖表：tdx.raw_stocks_basic、tdx.dim_sw_industry（须先完成 calc_basic、import_sw_industry）。

说明：视图中 date 直接取自 raw_stocks_basic."date" 且为 GROUP BY 列，
按单日查询（WHERE date = '...'）时谓词可下推至基表，不会全表扫描。

依赖: pip install psycopg2-binary

用法:
  python create_sw_views_standalone.py
  python create_sw_views_standalone.py --schema tdx --db-url 'postgresql://...'
"""
from __future__ import annotations

import argparse

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()


def qi(ident: str) -> str:
    """PostgreSQL 双引号标识符"""
    return '"' + ident.replace('"', '""') + '"'


def qobj(schema: str, name: str) -> str:
    return f"{qi(schema)}.{qi(name)}"


def create_views_sql(schema: str) -> list[tuple[str, str]]:
    """(视图名, CREATE OR REPLACE VIEW ... SQL)"""
    basic = qobj(schema, "raw_stocks_basic")
    industry = qobj(schema, "dim_sw_industry")
    v_sw = qobj(schema, "v_sw_industry_daily")

    # GROUPING SETS 同时产出两级聚合行：
    #   申万一级行（sw2_code/sw2_name 为 NULL）+ 申万二级行（sw1+sw2 齐全）。
    sw = f"""
CREATE OR REPLACE VIEW {v_sw} AS
SELECT
    b."date"        AS date,
    i.sw1_code      AS sw1_code,
    i.sw1_name      AS sw1_name,
    i.sw2_code      AS sw2_code,
    i.sw2_name      AS sw2_name,
    COUNT(*)        AS stock_count,
    AVG(b.change_pct) AS avg_change_pct
FROM {basic} b
JOIN {industry} i
  ON i.symbol = b.symbol
 AND i.is_latest = 1
GROUP BY GROUPING SETS (
    (b."date", i.sw1_code, i.sw1_name),
    (b."date", i.sw1_code, i.sw1_name, i.sw2_code, i.sw2_name)
)
"""

    return [
        ("v_sw_industry_daily", sw),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="创建申万行业日线聚合视图 tdx.v_sw_industry_daily")
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
