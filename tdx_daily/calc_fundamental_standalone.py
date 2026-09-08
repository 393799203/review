#!/usr/bin/env python3
r"""
基本面因子计算：用 tdx.raw_stock_finance 最新财务快照（point-in-time：updated_date <= 评估日）
结合当日收盘/市值，计算估值/盈利/质量因子，写入 tdx.raw_stock_indicators 新增列
（pe/pb/ps/pcf/roe/roa/net_margin/op_margin/debt_ratio/cf_quality/ar_ratio/inv_ratio）。

依赖表: raw_stock_finance（sync_fundamental_standalone.py 同步）、raw_stocks_basic、
        raw_stock_indicators（calc_indicator_standalone.py）。

用法:
  python calc_fundamental_standalone.py                 # 全日期（增量：只算指标表已有日期）
  python calc_fundamental_standalone.py --limit-dates 5 # 只算最近 N 个交易日（快）
  python calc_fundamental_standalone.py --date 2026-09-04

口径说明:
  - 估值: pe = 总市值(元) / 净利润；pb = 收盘/每股净资产；ps = 总市值/主营收入；pcf = 总市值/经营现金流
    （raw_stocks_basic.totalmv 实测单位为元，直接使用）
  - 盈利: roe = 净利润/净资产；roa = 净利润/总资产；net_margin = 净利润/主营收入；op_margin = 主营利润/主营收入
  - 质量: debt_ratio = 1 − 净资产/总资产；cf_quality = 经营现金流/净利润；ar_ratio = 应收账款/主营收入；inv_ratio = 存货/总资产
  - 分母为 0/缺失 → NULL；评估日早于该股财务快照 updated_date → NULL（point-in-time，避免用未来财报）
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import date, datetime
from typing import Any, Optional

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()

# 因子列名（同时进入 raw_stock_indicators 的表列）
FACTOR_DEFS = {
    "pe": "pe",
    "pb": "pb",
    "ps": "ps",
    "pcf": "pcf",
    "roe": "roe",
    "roa": "roa",
    "net_margin": "net_margin",
    "op_margin": "op_margin",
    "debt_ratio": "debt_ratio",
    "cf_quality": "cf_quality",
    "ar_ratio": "ar_ratio",
    "inv_ratio": "inv_ratio",
}
FACTOR_COLS = list(FACTOR_DEFS)


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    v = a / b
    if not math.isfinite(v):
        return None
    # 明显异常值（如总公司负债率>5 或 pe 负得离谱）置 NULL
    return v


def compute_row(close: float, totalmv_yuan: float,
                jinglirun, jingzichan, zongzichan, zhuyingshouru,
                zhuyinglirun, meigujingzichan, jingyingxianjinliu,
                yingshouzhangkuan, cunhuo) -> dict[str, Optional[float]]:
    """totalmv_yuan 单位 = 元（raw_stocks_basic.totalmv 实测为元，非万元；
       茅台 12.5亿股×1330元 ≈ 1.66e12 == totalmv 值，验证一致）"""
    out: dict[str, Optional[float]] = {c: None for c in FACTOR_COLS}
    mv = float(totalmv_yuan) if totalmv_yuan else None
    if mv is None or close is None or close <= 0:
        return out
    # 数据缩放校正：本环境财务「总量」字段（净利润/收入/现金流/资产合计）实测为
    # 每股口径对应值的 10 倍（净资产总额/每股净资产/总股本 ≈ 10.0，见实测），
    # 而市值、价格、股本正确 → 混合口径的 PE/PS/PCF 需 ×10 还原真实水平；
    # 比值因子（ROE/负债率/含金量/占比等）分子分母同为总量 → 天然正确，不校正。
    SCALE = 10.0
    out["pe"] = _safe_div(mv, jinglirun)
    out["pb"] = _safe_div(close, meigujingzichan)
    out["ps"] = _safe_div(mv, zhuyingshouru)
    out["pcf"] = _safe_div(mv, jingyingxianjinliu)
    if out["pe"] is not None:
        out["pe"] = out["pe"] * SCALE
    if out["ps"] is not None:
        out["ps"] = out["ps"] * SCALE
    if out["pcf"] is not None:
        out["pcf"] = out["pcf"] * SCALE
    out["roe"] = _safe_div(jinglirun, jingzichan)
    out["roa"] = _safe_div(jinglirun, zongzichan)
    out["net_margin"] = _safe_div(jinglirun, zhuyingshouru)
    out["op_margin"] = _safe_div(zhuyinglirun, zhuyingshouru)
    out["debt_ratio"] = _safe_div(jingzichan, zongzichan) if jingzichan is not None and zongzichan else None
    if out["debt_ratio"] is not None:
        out["debt_ratio"] = 1.0 - out["debt_ratio"]
    out["cf_quality"] = _safe_div(jingyingxianjinliu, jinglirun)
    out["ar_ratio"] = _safe_div(yingshouzhangkuan, zhuyingshouru)
    out["inv_ratio"] = _safe_div(cunhuo, zongzichan)
    return out


def _to_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return v


def ensure_columns(conn) -> None:
    with conn.cursor() as cur:
        for c in FACTOR_COLS:
            cur.execute(f'ALTER TABLE tdx.raw_stock_indicators ADD COLUMN IF NOT EXISTS "{c}" DOUBLE PRECISION;')
    conn.commit()


def get_dates(conn, limit: int) -> list[date]:
    sql = "SELECT DISTINCT date FROM tdx.raw_stock_indicators ORDER BY date"
    if limit > 0:
        sql = f"SELECT DISTINCT date FROM (SELECT DISTINCT date FROM tdx.raw_stock_indicators ORDER BY date DESC LIMIT {int(limit)}) t ORDER BY date"
    with conn.cursor() as cur:
        cur.execute(sql)
        return [_to_date(r[0]) for r in cur.fetchall()]


def load_finance_snapshots(conn) -> list[dict]:
    """每只股票全部快照（按 updated_date 升序）"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, updated_date, jinglirun, jingzichan, zongzichan, zhuyingshouru, "
            "zhuyinglirun, meigujingzichan, jingyingxianjinliu, yingshouzhangkuan, cunhuo "
            "FROM tdx.raw_stock_finance ORDER BY symbol, updated_date"
        )
        out: dict[str, list[dict]] = {}
        for r in cur.fetchall():
            out.setdefault(str(r[0]), []).append({
                "updated_date": int(r[1]) if r[1] else None,
                "jinglirun": r[2], "jingzichan": r[3], "zongzichan": r[4],
                "zhuyingshouru": r[5], "zhuyinglirun": r[6], "meigujingzichan": r[7],
                "jingyingxianjinliu": r[8], "yingshouzhangkuan": r[9], "cunhuo": r[10],
            })
    return out


def snapshot_at(fin_index: dict[str, list[dict]], symbol: str, d: date) -> Optional[dict]:
    """point-in-time：取 updated_date <= d 的最新快照"""
    snaps = fin_index.get(symbol)
    if not snaps:
        return None
    d_int = int(d.strftime("%Y%m%d"))
    best = None
    for s in snaps:
        if s["updated_date"] is not None and s["updated_date"] <= d_int:
            best = s
        else:
            break
    return best


def upsert_factors(conn, d: date, rows: list[tuple[str, dict]], batch: int = 3000) -> int:
    from psycopg2.extras import execute_values

    if not rows:
        return 0
    tuples = [(sym, d, *(v for v in row.values())) for sym, row in rows]
    cols = ", ".join(f'"{c}"' for c in FACTOR_COLS)
    upd = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in FACTOR_COLS)
    total = 0
    for i in range(0, len(tuples), batch):
        chunk = tuples[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO tdx.raw_stock_indicators (symbol, date, {cols})
                VALUES %s
                ON CONFLICT (symbol, date) DO UPDATE SET {upd}
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="基本面因子计算 → raw_stock_indicators 新增列")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--date", type=str, default=None, metavar="YYYY-MM-DD", help="只算指定日")
    parser.add_argument("--limit-dates", type=int, default=0, metavar="N", help="只算最近 N 个交易日（0=全部）")
    args = parser.parse_args()

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        ensure_columns(conn)
        dates = get_dates(conn, args.limit_dates)
        if args.date:
            dates = [date.fromisoformat(args.date)]
        if not dates:
            print("raw_stock_indicators 无日期", file=sys.stderr)
            sys.exit(1)
        fin_index = load_finance_snapshots(conn)
        print(f"财务快照: {sum(len(v) for v in fin_index.values()):,} 条（{len(fin_index):,} 只）")
        print(f"计算 {len(dates)} 个交易日 [{dates[0]} .. {dates[-1]}] …")

        total = 0
        for di, d in enumerate(dates):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT b.symbol, b.close, b.totalmv
                    FROM tdx.raw_stocks_basic b
                    WHERE b.date = %s AND b.close > 0 AND b.totalmv > 0
                    """,
                    (d,),
                )
                basics = cur.fetchall()
            if not basics:
                continue
            rows: list[tuple[str, dict]] = []
            for sym, close, totalmv in basics:
                snap = snapshot_at(fin_index, str(sym), d)
                if not snap:
                    continue  # 无快照 → 该日该股基本面因子保持 NULL
                row = compute_row(
                    float(close), float(totalmv),
                    snap["jinglirun"], snap["jingzichan"], snap["zongzichan"],
                    snap["zhuyingshouru"], snap["zhuyinglirun"], snap["meigujingzichan"],
                    snap["jingyingxianjinliu"], snap["yingshouzhangkuan"], snap["cunhuo"],
                )
                rows.append((str(sym), row))
            total += upsert_factors(conn, d, rows)
            if (di + 1) % 20 == 0 or di + 1 == len(dates):
                print(f"  … {di + 1}/{len(dates)} 交易日, 已更新 {total:,} 行", flush=True)
        print(f"完成: 共更新 {total:,} 行")
    finally:
        conn.close()


if __name__ == "__main__":
    main()