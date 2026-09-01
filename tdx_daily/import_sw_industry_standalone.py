#!/usr/bin/env python3
r"""
申万行业分类导入：读取 A股申万行业分类.xlsx → 写入 PostgreSQL tdx.dim_sw_industry。

与 import_gbbq_standalone.py 行为一致：先 TRUNCATE 再全量导入。
Excel 中含历史变迁记录（当前是否最新=0），全量保留，便于回测时按日期取行业归属。

Excel 说明：
  - 无 sharedStrings（内联字符串），用 pandas + openpyxl 读取。
  - 纳入/剔除行业日期为 Excel 序列数（如 46234），基准 1899-12-30 转 date；剔除日期可为空。
  - symbol 映射：XSHG→sh、XSHE→sz、BJSE→bj + 6 位代码（如 sh600519 / sz000001 / bj920238）。

依赖: pip install pandas openpyxl psycopg2-binary（写库时需要 psycopg2-binary）

用法:
  python import_sw_industry_standalone.py
  python import_sw_industry_standalone.py --excel "A股申万行业分类.xlsx"
  python import_sw_industry_standalone.py --db-url "postgresql://..."
  python import_sw_industry_standalone.py --dry-run   # 只解析 Excel 打印统计，不连库
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from tdx_config import PACKAGE_ROOT, get_db_url

DEFAULT_DB_URL = get_db_url()
DEFAULT_EXCEL = PACKAGE_ROOT / "A股申万行业分类.xlsx"

MARKET_PREFIX = {"XSHG": "sh", "XSHE": "sz", "BJSE": "bj"}
EXCEL_EPOCH = date(1899, 12, 30)  # Excel 序列数基准（含 1900 闰年 bug 的兼容基准）


def norm_code(value, width: int = 6) -> str:
    """代码归一化为 6 位字符串。pandas 会把数字形态的代码读成 int64（前导零丢失），需 zfill 补齐。"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.isdigit() and len(s) < width:
        s = s.zfill(width)
    return s


def cell_to_date(value) -> date | None:
    """日期单元格 → date。openpyxl 按单元格日期格式通常已给出 datetime；
    若为 Excel 序列数（如 46234）则按基准 1899-12-30 换算；空值返回 None。"""
    import pandas as pd

    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        serial = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if serial != serial or serial <= 0:  # NaN 或非正数
        return None
    return EXCEL_EPOCH + timedelta(days=int(serial))


def parse_excel(path: Path) -> list[tuple]:
    """解析 Excel，返回行元组列表：
    (symbol, code, name, market, sw1_code, sw1_name, sw2_code, sw2_name,
     sw3_code, sw3_name, start_date, end_date, is_latest)
    """
    import pandas as pd

    df = pd.read_excel(path, engine="openpyxl")
    rows: list[tuple] = []
    skipped: Counter[str] = Counter()

    # 列顺序（与表头一致）：股票代码, 股票简称, 交易市场, 申万3级行业代码, 所属申万3级行业,
    # 申万2级行业代码, 所属申万2级行业, 申万1级行业代码, 所属申万1级行业, 纳入行业日期, 剔除行业日期, 当前是否最新
    for rec in df.itertuples(index=False):
        code = norm_code(rec[0])
        name = str(rec[1]).strip()
        market_raw = str(rec[2]).strip()
        sw3_code = norm_code(rec[3])
        sw3_name = str(rec[4]).strip()
        sw2_code = norm_code(rec[5])
        sw2_name = str(rec[6]).strip()
        sw1_code = norm_code(rec[7])
        sw1_name = str(rec[8]).strip()
        start_date = cell_to_date(rec[9])
        end_date = cell_to_date(rec[10])
        try:
            is_latest = int(float(str(rec[11]).strip()))
        except (TypeError, ValueError):
            is_latest = 0

        prefix = MARKET_PREFIX.get(market_raw)
        if prefix is None:
            skipped[f"未知市场:{market_raw}"] += 1
            continue
        if not (len(code) == 6 and code.isdigit()):
            skipped[f"非法代码:{code}"] += 1
            continue
        if start_date is None:
            skipped["纳入日期为空"] += 1
            continue

        symbol = prefix + code
        rows.append(
            (
                symbol, code, name, market_raw,
                sw1_code, sw1_name, sw2_code, sw2_name, sw3_code, sw3_name,
                start_date, end_date, is_latest,
            )
        )

    if skipped:
        for reason, n in skipped.items():
            print(f"跳过 {n} 行：{reason}", file=sys.stderr)
    return rows


def print_stats(rows: list[tuple]) -> None:
    total = len(rows)
    latest = sum(1 for r in rows if r[12] == 1)
    market_dist = Counter(r[0][:2] for r in rows)
    dates = [r[10] for r in rows if r[10] is not None]
    print(f"总行数: {total:,}")
    print(f"is_latest=1: {latest:,}（历史记录 is_latest=0: {total - latest:,}）")
    print("按市场分布:", dict(sorted(market_dist.items())))
    if dates:
        print(f"纳入日期范围: {min(dates)} ~ {max(dates)}")
    print("样本前 5 行:")
    for r in rows[:5]:
        print(" ", r)


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tdx.dim_sw_industry (
                symbol      TEXT NOT NULL,
                code        TEXT NOT NULL,
                name        TEXT,
                market      TEXT,
                sw1_code    TEXT,
                sw1_name    TEXT,
                sw2_code    TEXT,
                sw2_name    TEXT,
                sw3_code    TEXT,
                sw3_name    TEXT,
                start_date  DATE,
                end_date    DATE,
                is_latest   SMALLINT NOT NULL DEFAULT 1
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dim_sw_industry_symbol ON tdx.dim_sw_industry (symbol);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dim_sw_industry_is_latest ON tdx.dim_sw_industry (is_latest);")
    conn.commit()


def import_rows(conn, rows: list[tuple], batch: int, truncate: bool) -> int:
    from psycopg2.extras import execute_values

    ensure_table(conn)
    with conn.cursor() as cur:
        if truncate:
            cur.execute("TRUNCATE TABLE tdx.dim_sw_industry;")
    conn.commit()

    if not rows:
        return 0

    total = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO tdx.dim_sw_industry
                    (symbol, code, name, market,
                     sw1_code, sw1_name, sw2_code, sw2_name, sw3_code, sw3_name,
                     start_date, end_date, is_latest)
                VALUES %s
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="申万行业分类 Excel → tdx.dim_sw_industry（先 TRUNCATE 再全量导入）")
    parser.add_argument("--excel", default=str(DEFAULT_EXCEL), help="申万行业分类 xlsx 路径（默认仓库内文件）")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="PostgreSQL 连接 URL")
    parser.add_argument("--batch", type=int, default=5000, help="每批插入行数")
    parser.add_argument("--dry-run", action="store_true", help="只解析 Excel 打印统计，不连数据库")
    parser.add_argument("--no-truncate", action="store_true", help="不 TRUNCATE（追加导入）")
    args = parser.parse_args()

    excel_path = Path(args.excel)
    if not excel_path.is_file():
        print(f"错误：找不到 Excel 文件: {excel_path}", file=sys.stderr)
        sys.exit(1)

    print(f"解析: {excel_path}")
    rows = parse_excel(excel_path)
    print(f"解析得到 {len(rows):,} 条")

    if args.dry_run:
        print_stats(rows)
        print("dry-run：未写入数据库")
        return

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        n = import_rows(conn, rows, args.batch, truncate=not args.no_truncate)
        print(f"已写入 tdx.dim_sw_industry: {n:,} 条（truncate={'否' if args.no_truncate else '是'}）")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
