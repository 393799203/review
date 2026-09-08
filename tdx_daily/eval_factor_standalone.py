#!/usr/bin/env python3
r"""
因子有效性评估：对 tdx.raw_stock_indicators（或自定义因子列）计算
截面 Rank IC / ICIR / t 值 / IC>0 占比 / 分层（分位数）收益检验。

收益口径：前复权后复权统一用 tdx.v_hfq_daily（后复权）收盘价，
前视收益 = close(T+H) / close(T) - 1，H 为市场交易日历上第 H 个交易日，
避免未来函数（与 strategy_gen 回测口径一致）。

评估对象：每交易日对全市场横截面计算因子值与未来 H 日收益的 Spearman 秩相关。

用法:
  python eval_factor_standalone.py                                    # 默认全部因子，H=5，5 分位
  python eval_factor_standalone.py --factors vr20,div20,mom20,cmf20   # 指定因子
  python eval_factor_standalone.py --horizon 10 --quantiles 5 --limit-dates 60
  python eval_factor_standalone.py --out-csv /tmp/ic_matrix.csv       # 导出逐日 IC 矩阵
  python eval_factor_standalone.py --no-exclude-st                    # 不剔除 ST

说明:
  - 因子值不足 min-stocks 的交易日跳过该因子（默认 100）
  - 停牌股在 T+H 无收盘价的自动剔除（不入截面）
  - ST 剔除按 dim_sw_industry.is_latest=1 的 name LIKE '%ST%'（与筛选策略一致）
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime
from typing import Any, Optional

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()

FACTOR_TABLE = "raw_stock_indicators"

# 样本（universe）预设：symbol 前缀过滤
UNIVERSE_PREFIXES = {
    'all': None,                      # 全部符号（含指数/板块/北交所/基金等，默认，便于对照）
    'ashare': ('sh60%', 'sh68%', 'sz00%', 'sz30%'),  # 沪深 A 股（主板+创业+科创）
    'main': ('sh60%', 'sz00%'),       # 沪深主板
    'gem': ('sh68%', 'sz30%'),        # 创业板+科创板
}
UNIVERSE_CHOICES = ('all', 'ashare', 'main', 'gem')

# 指数成分样本（依赖 tdx.dim_index_member，由 sync_index_constituents.py 同步）
INDEX_UNIVERSES: dict[str, str] = {
    'hs300': '沪深300',
}


# ---------------------------------------------------------------- 秩相关

def _average_ranks(values: list[float]) -> list[float]:
    """平均秩（处理并列）"""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based 平均秩
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return cov / (sx * sy)


def spearman_ic(factors: list[float], fwd_rets: list[float]) -> Optional[float]:
    """截面 Spearman Rank IC（因子值 vs 未来收益）"""
    n = len(factors)
    if n < 3:
        return None
    r_f = _average_ranks(factors)
    r_r = _average_ranks(fwd_rets)
    return _pearson(r_f, r_r)


def winsorize(values: list[float], lo: float = 0.01, hi: float = 0.99) -> list[float]:
    """按分位数缩尾：超出 [P_lo, P_hi] 的极端收益替换为边界值。
    注意：单调变换不改变秩，Spearman IC 不受影响；缩尾主要修正分位组均值（Q1~Q5）。"""
    if len(values) < 10:
        return values
    vs = sorted(values)
    v_lo = vs[min(int(lo * len(vs)), len(vs) - 1)]
    v_hi = vs[min(int(hi * len(vs)) - 1, len(vs) - 1)]
    return [max(v_lo, min(v, v_hi)) for v in values]


def neutralize_values(symbols: list[str], values: list[float],
                      industry_map: dict[str, str], lnmv_map: dict[str, float],
                      min_group: int = 5) -> list[float]:
    """行业市值中性化（每日截面）：
    1) 因子值先按当日截面 1%/99% 缩尾；
    2) 减去所属申万一级行业当日均值（行业样本 < min_group 或无行业归属的用全截面均值）；
    3) 对 ln(总市值) 做一元线性回归，取残差。
    """
    n = len(values)
    wv = winsorize(values)
    # 行业均值（含计数）
    ind_sum: dict[str, float] = {}
    ind_cnt: dict[str, int] = {}
    for s, v in zip(symbols, wv):
        code = industry_map.get(s)
        if code:
            ind_sum[code] = ind_sum.get(code, 0.0) + v
            ind_cnt[code] = ind_cnt.get(code, 0) + 1
    overall = sum(wv) / n
    ind_mean = {
        code: (ind_sum[code] / ind_cnt[code] if ind_cnt[code] >= min_group else overall)
        for code in ind_sum
    }
    # 1) 行业去均值
    dem = []
    for i, s in enumerate(symbols):
        code = industry_map.get(s)
        m = ind_mean.get(code, overall) if code else overall
        dem.append(wv[i] - m)
    # 2) 对 ln(总市值) 回归取残差（无市值数据的保留行业去均值后的值）
    xs: list[float] = []
    ys: list[float] = []
    for i, s in enumerate(symbols):
        lm = lnmv_map.get(s)
        if lm is not None:
            xs.append(lm)
            ys.append(dem[i])
    if len(xs) < 5:
        return dem
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    b = num / den if den != 0 else 0.0
    a = my - b * mx
    out: list[float] = []
    for i, s in enumerate(symbols):
        lm = lnmv_map.get(s)
        out.append(dem[i] - (b * lm + a) if lm is not None else dem[i])
    return out


def load_industry_map(conn) -> dict[str, str]:
    """申万一级行业归属（is_latest=1）：symbol -> sw1_code"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, sw1_code FROM tdx.dim_sw_industry WHERE is_latest = 1 AND sw1_code IS NOT NULL"
        )
        return {str(r[0]): str(r[1]) for r in cur.fetchall()}


def load_lnmv_map(conn, d: date) -> dict[str, float]:
    """当日 ln(总市值)：symbol -> ln(totalmv)。totalmv 单位万元，取对数后单位常数被截距吸收。"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, LN(totalmv) FROM tdx.raw_stocks_basic WHERE date = %s AND totalmv > 0",
            (d,),
        )
        return {str(r[0]): float(r[1]) for r in cur.fetchall()}


# ---------------------------------------------------------------- DB 层

def _to_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return v


def get_calendar(conn) -> list[date]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT date FROM tdx.v_hfq_daily ORDER BY date")
        return [_to_date(r[0]) for r in cur.fetchall()]


def get_closes(conn, d: date) -> dict[str, float]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, close FROM tdx.v_hfq_daily WHERE date = %s",
            (d,),
        )
        return {str(r[0]): float(r[1]) for r in cur.fetchall()}


def get_factor_columns(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'tdx' AND table_name = %s
              AND data_type IN ('double precision', 'real', 'numeric')
              AND column_name NOT IN ('symbol', 'date')
            ORDER BY ordinal_position
            """,
            (FACTOR_TABLE,),
        )
        return [r[0] for r in cur.fetchall()]


def get_factor_rows(conn, d: date, factors: list[str], exclude_st: bool,
                    universe: str = 'all', sw1_name: str | None = None,
                    member_symbols: set[str] | None = None) -> list[tuple[str, list[float]]]:
    """返回 [(symbol, [因子值...])]；ST 剔除与筛选策略同口径，支持样本/申万一级行业/指数成分过滤"""
    cols = ", ".join(f'f."{c}"' for c in factors)
    where = ["f.date = %s"]
    args: list = [d]
    if exclude_st:
        where.append("(i.name IS NULL OR i.name NOT LIKE '%%ST%%')")
    prefixes = UNIVERSE_PREFIXES.get(universe)
    if prefixes:
        like = " OR ".join(["f.symbol LIKE %s"] * len(prefixes))
        where.append(f"({like})")
        args.extend(prefixes)
    if member_symbols is not None:
        if not member_symbols:
            return []
        where.append("f.symbol = ANY(%s)")
        args.append(sorted(member_symbols))
    if sw1_name:
        where.append("i.sw1_name = %s")
        args.append(sw1_name)
    where_sql = " AND ".join(where)
    if exclude_st or sw1_name:
        sql = f"""
            SELECT f.symbol, {cols}
            FROM tdx.{FACTOR_TABLE} f
            LEFT JOIN tdx.dim_sw_industry i
                ON i.symbol = f.symbol AND i.is_latest = 1
            WHERE {where_sql}
        """
    else:
        sql = f"""
            SELECT f.symbol, {cols}
            FROM tdx.{FACTOR_TABLE} f
            WHERE {where_sql}
        """
    with conn.cursor() as cur:
        cur.execute(sql, tuple(args))
        rows = cur.fetchall()
    out: list[tuple[str, list[float]]] = []
    for r in rows:
        # 列级 NULL 保留（eval 循环按因子跳过，不整行丢弃——基本面列缺数据不影响其他因子）
        vals: list[float] = []
        for v in r[1:]:
            try:
                vals.append(float(v) if v is not None else None)
            except (TypeError, ValueError):
                vals.append(None)
        out.append((str(r[0]), vals))
    return out


# ---------------------------------------------------------------- 结果落库（前端因子研究页数据源）

def _drop_unique_with_cols(cur, table: str, cols: list[str]) -> None:
    """删除由指定列构成的 UNIQUE 约束（旧表迁移用，名字不固定则扫描）"""
    cur.execute(
        f"""
        SELECT c.conname
        FROM pg_constraint c
        WHERE c.conrelid = 'tdx.{table}'::regclass AND c.contype = 'u'
        """
    )
    for (conname,) in cur.fetchall():
        cur.execute(
            f"""
            SELECT array_agg(a.attname ORDER BY k.ord)
            FROM pg_constraint c
            JOIN LATERAL unnest(c.conkey) WITH ORDINALITY k(attnum, ord) ON true
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
            WHERE c.conname = %s AND c.conrelid = 'tdx.{table}'::regclass
            """,
            (conname,),
        )
        row = cur.fetchone()
        if row and row[0] and sorted(row[0]) == sorted(cols):
            cur.execute(f'ALTER TABLE tdx.{table} DROP CONSTRAINT "{conname}"')


def ensure_eval_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tdx.factor_eval_summary (
                factor TEXT NOT NULL,
                horizon INT NOT NULL,
                universe TEXT NOT NULL DEFAULT 'all',
                method TEXT NOT NULL DEFAULT 'raw',
                min_date DATE,
                max_date DATE,
                n_dates INT,
                mean_ic DOUBLE PRECISION,
                ic_std DOUBLE PRECISION,
                icir DOUBLE PRECISION,
                t_stat DOUBLE PRECISION,
                ic_pos_pct DOUBLE PRECISION,
                q_means JSONB,
                mono DOUBLE PRECISION,
                computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tdx.factor_eval_daily_ic (
                factor TEXT NOT NULL,
                horizon INT NOT NULL,
                universe TEXT NOT NULL DEFAULT 'all',
                method TEXT NOT NULL DEFAULT 'raw',
                "date" DATE NOT NULL,
                ic DOUBLE PRECISION,
                computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        # 旧表迁移：补 universe/method 列（如缺）并重建唯一索引（含 method）
        cur.execute("ALTER TABLE tdx.factor_eval_summary ADD COLUMN IF NOT EXISTS universe TEXT NOT NULL DEFAULT 'all';")
        cur.execute("ALTER TABLE tdx.factor_eval_daily_ic ADD COLUMN IF NOT EXISTS universe TEXT NOT NULL DEFAULT 'all';")
        cur.execute("ALTER TABLE tdx.factor_eval_summary ADD COLUMN IF NOT EXISTS method TEXT NOT NULL DEFAULT 'raw';")
        cur.execute("ALTER TABLE tdx.factor_eval_daily_ic ADD COLUMN IF NOT EXISTS method TEXT NOT NULL DEFAULT 'raw';")
        # 删除旧的窄唯一索引/约束（不含 method 的），换成含 method 的唯一索引
        _drop_unique_with_cols(cur, "factor_eval_summary", ["factor", "horizon"])
        _drop_unique_with_cols(cur, "factor_eval_daily_ic", ["factor", "horizon", "date"])
        _drop_unique_with_cols(cur, "factor_eval_summary", ["factor", "horizon", "universe"])
        _drop_unique_with_cols(cur, "factor_eval_daily_ic", ["factor", "horizon", "universe", "date"])
        for name in ("ux_factor_eval_summary_fhu", "ux_factor_eval_daily_ic_fhud"):
            cur.execute(f'DROP INDEX IF EXISTS tdx.{name};')
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_factor_eval_summary_fhum "
            "ON tdx.factor_eval_summary (factor, horizon, universe, method);"
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_factor_eval_daily_ic_fhumd "
            "ON tdx.factor_eval_daily_ic (factor, horizon, universe, method, date);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_factor_eval_daily_ic_lookup "
            "ON tdx.factor_eval_daily_ic (factor, horizon, universe, method, date);"
        )
    conn.commit()


def save_results(conn, horizon: int, universe: str, method: str, usable: list[date], stats: dict, date_ic: list) -> int:
    """写 factor_eval_summary（upsert）+ factor_eval_daily_ic（先删后插）"""
    from psycopg2.extras import execute_values

    ensure_eval_tables(conn)
    min_d = usable[0] if usable else None
    max_d = usable[-1] if usable else None

    summary_tuples = []
    for fname, s in stats.items():
        q_means = [None if x is None else round(x, 6) for x in s["q_means"]]
        summary_tuples.append((
            fname, horizon, universe, method, min_d, max_d, s["n"], s["mean_ic"], s["ic_std"],
            s["icir"], s["t_stat"], s["pos_pct"], json.dumps(q_means), s["mono"],
        ))
    if summary_tuples:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO tdx.factor_eval_summary
                (factor, horizon, universe, method, min_date, max_date, n_dates, mean_ic, ic_std,
                 icir, t_stat, ic_pos_pct, q_means, mono)
                VALUES %s
                ON CONFLICT (factor, horizon, universe, method) DO UPDATE SET
                    min_date = EXCLUDED.min_date, max_date = EXCLUDED.max_date,
                    n_dates = EXCLUDED.n_dates, mean_ic = EXCLUDED.mean_ic,
                    ic_std = EXCLUDED.ic_std, icir = EXCLUDED.icir,
                    t_stat = EXCLUDED.t_stat, ic_pos_pct = EXCLUDED.ic_pos_pct,
                    q_means = EXCLUDED.q_means, mono = EXCLUDED.mono,
                    computed_at = now()
                """,
                summary_tuples,
            )
        conn.commit()

    # 先删旧逐日 IC（该 horizon×universe×method 整轮重写），再插新
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM tdx.factor_eval_daily_ic WHERE horizon = %s AND universe = %s AND method = %s",
            (horizon, universe, method),
        )
    conn.commit()

    daily_tuples = []
    for d, dic in date_ic:
        for fname, ic in dic.items():
            daily_tuples.append((fname, horizon, universe, method, d, ic))
    if daily_tuples:
        for i in range(0, len(daily_tuples), 5000):
            chunk = daily_tuples[i : i + 5000]
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO tdx.factor_eval_daily_ic (factor, horizon, universe, method, "date", ic)
                    VALUES %s
                    ON CONFLICT (factor, horizon, universe, method, date) DO UPDATE SET ic = EXCLUDED.ic
                    """,
                    chunk,
                )
            conn.commit()
    return len(daily_tuples)


# ---------------------------------------------------------------- 主流程

def _fmt(v: Optional[float], nd: int = 4) -> str:
    if v is None:
        return "-"
    return f"{v:.{nd}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="因子 IC/IR 与分层有效性评估（基于 v_hfq_daily 后复权）")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--horizon", type=int, default=5, help="未来收益持有交易日数（默认 5）")
    parser.add_argument("--factors", type=str, default="", help="逗号分隔因子列；缺省为表内全部数值列")
    parser.add_argument("--min-date", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--max-date", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--limit-dates", type=int, default=0, metavar="N", help="只评估最近 N 个交易日（0=全部）")
    parser.add_argument("--quantiles", type=int, default=5, help="分层组数（默认 5；0=不做分层）")
    parser.add_argument("--min-stocks", type=int, default=100, help="每日期截面最少样本数（默认 100）")
    parser.add_argument("--no-exclude-st", action="store_true", help="不剔除 ST")
    parser.add_argument("--winsorize", action="store_true", default=True,
                        help="对未来收益按每日截面 1%/99% 分位缩尾（默认开；修正极端妖股对分位均值的影响，秩IC不受影响）")
    parser.add_argument("--no-winsorize", action="store_true", help="关闭收益缩尾")
    parser.add_argument("--demean", action="store_true", default=True,
                        help="每日截面收益去均值（超额收益口径，默认开；消除市场单边行情对分位收益的影响，秩IC不受影响）")
    parser.add_argument("--no-demean", action="store_true", help="关闭截面去均值（分位收益为绝对收益）")
    parser.add_argument("--neutralize", action="store_true", default=True,
                        help="因子值做行业市值中性化（默认开）：因子值-申万一级行业当日均值，再对ln(总市值)回归取残差；与 raw 轨同时计算并落库 method=raw/neutral")
    parser.add_argument("--no-neutralize", action="store_true", help="关闭中性化（只算并只落 raw 轨）")
    parser.add_argument("--min-days", type=int, default=0, metavar="N",
                        help="只评估因子表历史 >= N 个交易日的标的（0=不限制；如 240 可排除上市不满一年的次新股）")
    parser.add_argument("--universe", type=str, default="all", choices=UNIVERSE_CHOICES + tuple(INDEX_UNIVERSES),
                        help="样本范围：all=全部符号（含指数/北交所/基金，默认）/ ashare=沪深A股 / main=沪深主板 / gem=创业+科创 / hs300=沪深300成分（需先 sync_index_constituents.py）")
    parser.add_argument("--sw1-name", type=str, default=None, metavar="申万一级行业名",
                        help="只评估指定申万一级行业（如 电子；需先 import_sw_industry）")
    parser.add_argument("--out-csv", type=str, default=None, help="导出逐日 IC 矩阵 CSV 路径")
    parser.add_argument("--save", action="store_true", help="结果落库 tdx.factor_eval_summary / tdx.factor_eval_daily_ic（供前端因子研究页）")
    args = parser.parse_args()

    if args.horizon < 1:
        parser.error("--horizon 必须 ≥ 1")
    if args.quantiles < 0:
        parser.error("--quantiles 必须 ≥ 0")
    if args.min_stocks < 3:
        parser.error("--min-stocks 必须 ≥ 3")

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        factors = [f.strip() for f in args.factors.split(",") if f.strip()]
        if not factors:
            factors = get_factor_columns(conn)
        if not factors:
            print(f"错误: tdx.{FACTOR_TABLE} 无数值列，请先运行 calc_indicator_standalone.py", file=sys.stderr)
            sys.exit(1)
        known = set(get_factor_columns(conn))
        unknown = [f for f in factors if f not in known]
        if unknown:
            print(f"错误: 未知因子列 {unknown}", file=sys.stderr)
            sys.exit(1)

        calendar = get_calendar(conn)
        if not calendar:
            print("错误: tdx.v_hfq_daily 无数据，请先运行 create_adj_views_standalone.py", file=sys.stderr)
            sys.exit(1)

        min_d = date.fromisoformat(args.min_date) if args.min_date else None
        max_d = date.fromisoformat(args.max_date) if args.max_date else None
        if min_d:
            calendar = [d for d in calendar if d >= min_d]
        if max_d:
            calendar = [d for d in calendar if d <= max_d]
        if args.limit_dates > 0:
            calendar = calendar[-args.limit_dates:]

        usable = calendar
        universe_label = f"sw1:{args.sw1_name}" if args.sw1_name else args.universe
        winsorize_on = args.winsorize and not args.no_winsorize
        demean_on = args.demean and not args.no_demean
        neutralize_on = args.neutralize and not args.no_neutralize
        # --min-days：一次性取历史足够的标的集合
        valid_symbols: set[str] | None = None
        if args.min_days > 0:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT symbol FROM tdx.raw_stock_indicators "
                    "GROUP BY symbol HAVING COUNT(*) >= %s",
                    (args.min_days,),
                )
                valid_symbols = {r[0] for r in cur.fetchall()}
            print(f"历史 >= {args.min_days} 日的标的: {len(valid_symbols):,} 只")
        # 中性化所需静态数据（行业归属）
        industry_map = load_industry_map(conn) if neutralize_on else {}
        if neutralize_on:
            print(f"行业归属: {len(industry_map):,} 个标的（申万一级，is_latest=1）")
        # 指数成分样本（--universe hs300 等）：从 dim_index_member 加载成员集合
        member_symbols: set[str] | None = None
        if args.universe in INDEX_UNIVERSES:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT symbol FROM tdx.dim_index_member WHERE "index" = %s',
                    (args.universe,),
                )
                member_symbols = {r[0] for r in cur.fetchall()}
            if not member_symbols:
                print(
                    f"错误: 指数 {args.universe}({INDEX_UNIVERSES[args.universe]}) 无成分数据，"
                    "请先运行 python sync_index_constituents.py",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"指数成分样本 {args.universe}: {len(member_symbols):,} 只（当前成分口径）")
        print(
            f"评估: {len(factors)} 个因子 × {len(usable)} 个交易日 [{usable[0]} .. {usable[-1]}] | "
            f"H={args.horizon} | 样本={universe_label}"
            f"{' | 行业=' + args.sw1_name if args.sw1_name else ''}"
            f" | 分位={args.quantiles} | 剔除ST={'是' if not args.no_exclude_st else '否'}"
            f" | 收益处理={'缩尾1%/99%' if winsorize_on else '不缩尾'}"
            f"{'+日度去均值' if demean_on else ''}"
            f" | 中性化={'行业均值+ln市值残差' if neutralize_on else '无'}"
        )

        # 逐日 IC：raw 与 neutral 双轨
        ic_by_factor: dict[str, list[float]] = {f: [] for f in factors}
        ic_n_by_factor: dict[str, list[float]] = {f: [] for f in factors}
        quant_acc: dict[str, dict[int, list[float]]] = {f: {g: [0.0, 0] for g in range(args.quantiles)} for f in factors}
        quant_acc_n: dict[str, dict[int, list[float]]] = {f: {g: [0.0, 0] for g in range(args.quantiles)} for f in factors}
        date_ic: list[tuple[date, dict[str, float]]] = []
        date_ic_n: list[tuple[date, dict[str, float]]] = []

        for idx, d in enumerate(usable):
            if (idx + 1) % 20 == 0:
                print(f"  … 已处理 {idx + 1}/{len(usable)} 个交易日", flush=True)
            if idx + args.horizon >= len(usable):
                continue
            # 目标日 = 该日期后第 horizon 个交易日
            tgt = usable[idx + args.horizon]
            closes_t = get_closes(conn, d)
            closes_tgt = get_closes(conn, tgt)
            if not closes_t or not closes_tgt:
                continue

            lnmv_map = load_lnmv_map(conn, d) if neutralize_on else {}
            rows = get_factor_rows(conn, d, factors, exclude_st=not args.no_exclude_st,
                                   universe=args.universe, sw1_name=args.sw1_name,
                                   member_symbols=member_symbols)
            if valid_symbols is not None:
                rows = [r for r in rows if r[0] in valid_symbols]
            if len(rows) < args.min_stocks:
                continue

            day_ic: dict[str, float] = {}
            day_ic_n: dict[str, float] = {}
            for fi, fname in enumerate(factors):
                pairs: list[tuple[str, float, float]] = []
                for sym, vals in rows:
                    c0 = closes_t.get(sym)
                    c1 = closes_tgt.get(sym)
                    fv = vals[fi]
                    if c0 is None or c1 is None or c0 <= 0 or fv is None:
                        continue
                    pairs.append((sym, fv, c1 / c0 - 1.0))
                if len(pairs) < args.min_stocks:
                    continue
                syms = [p[0] for p in pairs]
                factors_vals = [p[1] for p in pairs]
                rets = [p[2] for p in pairs]
                if winsorize_on:
                    # 秩不变，IC 不变；仅修正分位组均值的极端值影响
                    rets = winsorize(rets)
                if demean_on:
                    # 截面去均值：分位收益变为相对市场超额收益，消除单边行情影响（秩不变）
                    m = sum(rets) / len(rets)
                    rets = [r - m for r in rets]

                # ---- raw 轨（因子值不中性化） ----
                ic = spearman_ic(factors_vals, rets)
                if ic is None:
                    continue
                ic_by_factor[fname].append(ic)
                day_ic[fname] = ic
                if args.quantiles >= 2:
                    q = args.quantiles
                    order = sorted(range(len(pairs)), key=lambda i: pairs[i][1])
                    per = len(order) // q
                    for g in range(q):
                        seg = order[g * per : (g + 1) * per if g < q - 1 else len(order)]
                        if not seg:
                            continue
                        quant_acc[fname][g][0] += sum(rets[i] for i in seg)
                        quant_acc[fname][g][1] += len(seg)

                # ---- neutral 轨（行业均值 + ln市值残差中性化） ----
                if neutralize_on:
                    nvals = neutralize_values(syms, factors_vals, industry_map, lnmv_map)
                    ic_n = spearman_ic(nvals, rets)
                    if ic_n is None:
                        continue
                    ic_n_by_factor[fname].append(ic_n)
                    day_ic_n[fname] = ic_n
                    if args.quantiles >= 2:
                        q = args.quantiles
                        order_n = sorted(range(len(pairs)), key=lambda i: nvals[i])
                        per_n = len(order_n) // q
                        for g in range(q):
                            seg = order_n[g * per_n : (g + 1) * per_n if g < q - 1 else len(order_n)]
                            if not seg:
                                continue
                            quant_acc_n[fname][g][0] += sum(rets[i] for i in seg)
                            quant_acc_n[fname][g][1] += len(seg)
            date_ic.append((d, day_ic))
            date_ic_n.append((d, day_ic_n))

        if args.out_csv:
            with open(args.out_csv, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["date"] + factors)
                for d, dic in date_ic:
                    w.writerow([d.isoformat()] + [_fmt(dic.get(f), 6) if f in dic else "" for f in factors])
            print(f"逐日 IC 已导出: {args.out_csv}")

        if not ic_by_factor or all(not v for v in ic_by_factor.values()):
            print("无有效 IC 结果：请检查因子数据覆盖或 --min-stocks", file=sys.stderr)
            sys.exit(1)

        # 逐因子汇总统计（打印 + 落库共用）
        def _build_stats(ic_map: dict, q_acc: dict) -> dict:
            stats: dict[str, dict] = {}
            for fname in factors:
                ics = ic_map[fname]
                if not ics:
                    continue
                n = len(ics)
                mean_ic = sum(ics) / n
                var = sum((x - mean_ic) ** 2 for x in ics) / n
                ic_std = math.sqrt(var)
                icir = mean_ic / ic_std if ic_std > 0 else 0.0
                t_stat = mean_ic / (ic_std / math.sqrt(n)) if ic_std > 0 else 0.0
                pos_pct = sum(1 for x in ics if x > 0) / n
                q_means: list[Optional[float]] = []
                mono: Optional[float] = None
                if args.quantiles >= 2:
                    for g in range(args.quantiles):
                        cnt = q_acc[fname][g][1]
                        q_means.append(q_acc[fname][g][0] / cnt if cnt else None)
                    valid = [(g, m) for g, m in enumerate(q_means) if m is not None]
                    mono = spearman_ic([g for g, _ in valid], [m for _, m in valid]) if len(valid) >= 3 else None
                stats[fname] = {
                    "n": n, "mean_ic": mean_ic, "ic_std": ic_std, "icir": icir,
                    "t_stat": t_stat, "pos_pct": pos_pct, "q_means": q_means, "mono": mono,
                }
            return stats

        stats = _build_stats(ic_by_factor, quant_acc)
        stats_n = _build_stats(ic_n_by_factor, quant_acc_n) if neutralize_on else {}

        # 打印汇总
        header = ["factor", "n_dates", "mean_ic", "ic_std", "icir", "t_stat", "ic>0%"]
        if args.quantiles >= 2:
            header += [f"Q{g+1}" for g in range(args.quantiles)] + ["Q1-Q5_spread", "mono"]

        def _print_table(title: str, st: dict) -> None:
            print(f"--- {title} ---")
            print("  ".join(f"{h:>10}" for h in header))

            def _row_of(fname: str, s: dict) -> list[str]:
                row = [fname, str(s["n"]), _fmt(s["mean_ic"]), _fmt(s["ic_std"]),
                       _fmt(s["icir"]), _fmt(s["t_stat"], 2), f"{s['pos_pct']*100:.1f}%"]
                if args.quantiles >= 2:
                    row += [_fmt(x, 4) if x is not None else "-" for x in s["q_means"]]
                    q0, qq = s["q_means"][0], s["q_means"][-1]
                    row.append(_fmt(q0 - qq) if (q0 is not None and qq is not None) else "-")
                    row.append(_fmt(s["mono"], 2) if s["mono"] is not None else "-")
                return row

            for fname, s in sorted(st.items(), key=lambda kv: -(abs(kv[1]["icir"]) + abs(kv[1]["t_stat"]) * 1e-3)):
                print("  ".join(f"{v:>10}" for v in _row_of(fname, s)))

        _print_table(f"汇总: 样本={universe_label} H={args.horizon} method=raw（未中性化）", stats)
        if neutralize_on:
            _print_table(f"汇总: 样本={universe_label} H={args.horizon} method=neutral（行业+市值中性化）", stats_n)
            # 对比：raw vs neutral 的 ICIR
            print("--- raw vs neutral ICIR 对比 ---")
            print("  ".join(f"{h:>12}" for h in ["factor", "raw_icir", "neu_icir", "delta"]))
            for fname in sorted(stats, key=lambda f: -(abs(stats_n.get(f, {}).get("icir", 0.0)))):
                if fname not in stats_n:
                    continue
                r = stats[fname]["icir"]
                nn = stats_n[fname]["icir"]
                print(f"  {fname:>12} {r:>12.3f} {nn:>12.3f} {nn - r:>12.3f}")

        if args.save:
            n_saved = save_results(conn, args.horizon, universe_label, 'raw', usable, stats, date_ic)
            print(f"已落库 raw: factor_eval_summary {len(stats)} 条 + factor_eval_daily_ic {n_saved} 条 (H={args.horizon}, 样本={universe_label})")
            if neutralize_on:
                n_saved_n = save_results(conn, args.horizon, universe_label, 'neutral', usable, stats_n, date_ic_n)
                print(f"已落库 neutral: factor_eval_summary {len(stats_n)} 条 + factor_eval_daily_ic {n_saved_n} 条 (H={args.horizon}, 样本={universe_label})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
