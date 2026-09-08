#!/usr/bin/env python3
r"""
纯 Python 技术指标 / 量价因子计算：依赖 tdx.raw_stocks_daily，不引入新数据源
（对齐「低成本因子扩展」决策：先用现有日线补技术指标与量价因子），
计算后写入 tdx.raw_stock_indicators（宽表，每 symbol×date 一行）。

与 calc_basic_standalone.py / calc_factor_standalone.py 同风格、同管线。

因子分类（47 列，量价关系为重点）：
  趋势   ma5/10/20/60, ema12, ema26, dif, dea, macd_hist, ma_bull, mom5/20/60
  摆动   rsi6/12/24, kdj_k/d/j, cci14, wr14, bias6/12/24
  波动   atr14, boll_mid/up/low, boll_pctb, std20
  量价关系 vr5/10/20, vol_trend, vol_cv20, vol_low_ratio20, pos20, vol_pos20,
         div20, corr_pv20, obv, obv_slope5, vpt, mfi14, cmf20, new_high20, new_low20

窗口约定：
- 均线/量比类窗口含当日（vr5 = volume / SMA(volume,5) 含当日）
- new_high20/new_low20 的 20 日窗口不含当日（与筛选策略 prev_high 口径一致）
- 状态类（EMA/MACD/RSI/KDJ/ATR/OBV/VPT）从装载区间首日起一次性扫描，
  增量模式回看 LOOKBACK_NATURAL_DAYS 天装载，保证尾部窗口与全量一致、可复算
- 各列在数据不足时写 NULL（DOUBLE PRECISION）

用法:
  python calc_indicator_standalone.py                    # 增量（默认，清理残尾后追加）
  python calc_indicator_standalone.py --full             # TRUNCATE 后全量重算
  python calc_indicator_standalone.py --db-url "postgresql://..."
  python calc_indicator_standalone.py --limit-symbols 50 # 仅处理前 N 个标的（调试）
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()

# 增量模式回看自然日：按 2 倍交易日->自然日放宽再加 60 天余量（覆盖 ma60/mom60 等最长窗口）
LOOKBACK_NATURAL_DAYS = 60 * 2 + 60


@dataclass
class DailyBar:
    symbol: str
    d: date
    open: float
    high: float
    low: float
    close: float
    amount: float
    volume: float


@dataclass
class IndicatorRow:
    symbol: str
    d: date
    values: list[Optional[float]]


# ---------------------------------------------------------------- 基础窗口函数

def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _std_pop(values: list[float]) -> float:
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def _ema_series(values: list[float], n: int) -> list[float]:
    """EMA(n) 序列，alpha=2/(n+1)，首值作种子"""
    if not values:
        return []
    alpha = 2.0 / (n + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def _rsi_series(closes: list[float], n: int) -> list[Optional[float]]:
    """Wilder RSI(n) 全历史平滑；有效值自 i>=n 起"""
    ln = len(closes)
    out: list[Optional[float]] = [None] * ln
    if ln < n + 1:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, n + 1):
        chg = closes[i] - closes[i - 1]
        gains.append(max(chg, 0.0))
        losses.append(max(-chg, 0.0))
    ag = sum(gains) / n
    al = sum(losses) / n

    def _rsi(avg_g: float, avg_l: float) -> float:
        if avg_l == 0:
            return 100.0 if avg_g > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + avg_g / avg_l)

    out[n] = _rsi(ag, al)
    for i in range(n + 1, ln):
        chg = closes[i] - closes[i - 1]
        g, l = max(chg, 0.0), max(-chg, 0.0)
        ag = (ag * (n - 1) + g) / n
        al = (al * (n - 1) + l) / n
        out[i] = _rsi(ag, al)
    return out


def _kdj_series(bars: list[DailyBar]) -> tuple[list[Optional[float]], list[Optional[float]], list[Optional[float]]]:
    """KDJ(9,3,3)：RSV 滑窗 + K/D 平滑，首值 50；有效值自 i>=11 起"""
    ln = len(bars)
    ks: list[Optional[float]] = [None] * ln
    ds: list[Optional[float]] = [None] * ln
    js: list[Optional[float]] = [None] * ln
    if ln == 0:
        return ks, ds, js
    k = d = 50.0
    win: deque[DailyBar] = deque()
    for i, b in enumerate(bars):
        win.append(b)
        if len(win) > 9:
            win.popleft()
        ll = min(x.low for x in win)
        hh = max(x.high for x in win)
        rsv = 50.0 if hh == ll else (b.close - ll) / (hh - ll) * 100.0
        k = 2.0 / 3.0 * k + 1.0 / 3.0 * rsv
        d = 2.0 / 3.0 * d + 1.0 / 3.0 * k
        if i >= 11:
            ks[i], ds[i], js[i] = k, d, 3.0 * k - 2.0 * d
    return ks, ds, js


def _atr_series(bars: list[DailyBar], n: int = 14) -> list[Optional[float]]:
    """ATR(n) Wilder 平滑（SMA 种子）；有效值自 i>=n 起"""
    ln = len(bars)
    out: list[Optional[float]] = [None] * ln
    if ln < n + 1:
        return out

    def _tr(i: int) -> float:
        b, p = bars[i], bars[i - 1]
        return max(b.high - b.low, abs(b.high - p.close), abs(b.low - p.close))

    atr = sum(_tr(i) for i in range(1, n + 1)) / n
    out[n] = atr
    for i in range(n + 1, ln):
        atr = (atr * (n - 1) + _tr(i)) / n
        out[i] = atr
    return out


def _obv_vpt_series(bars: list[DailyBar]) -> tuple[list[float], list[float]]:
    """OBV 累积能量潮 / VPT 量价趋势，O(n) 一次性扫描"""
    ln = len(bars)
    obv = [0.0] * ln
    vpt = [0.0] * ln
    for i in range(1, ln):
        b, p = bars[i], bars[i - 1]
        if b.close > p.close:
            obv[i] = obv[i - 1] + b.volume
        elif b.close < p.close:
            obv[i] = obv[i - 1] - b.volume
        else:
            obv[i] = obv[i - 1]
        if p.close > 0:
            vpt[i] = vpt[i - 1] + (b.close - p.close) / p.close * b.volume
        else:
            vpt[i] = vpt[i - 1]
    return obv, vpt


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return cov / (sx * sy)


# ---------------------------------------------------------------- 计算上下文
# 预计算全序列数组，供各列 O(1) 取值；其余滑窗列按需切片（窗口≤60，O(n) 量级）

@dataclass
class Ctx:
    closes: list[float]
    volumes: list[float]
    ema12: list[float]
    ema26: list[float]
    dif: list[float]
    dea: list[float]
    rsi6: list[Optional[float]]
    rsi12: list[Optional[float]]
    rsi24: list[Optional[float]]
    kdj_k: list[Optional[float]]
    kdj_d: list[Optional[float]]
    kdj_j: list[Optional[float]]
    atr: list[Optional[float]]
    obv: list[float]
    vpt: list[float]


def _build_ctx(bars: list[DailyBar]) -> Ctx:
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    ema12 = _ema_series(closes, 12)
    ema26 = _ema_series(closes, 26)
    dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    dea = _ema_series(dif, 9)
    rsi6, rsi12, rsi24 = _rsi_series(closes, 6), _rsi_series(closes, 12), _rsi_series(closes, 24)
    kdj_k, kdj_d, kdj_j = _kdj_series(bars)
    atr = _atr_series(bars)
    obv, vpt = _obv_vpt_series(bars)
    return Ctx(closes, volumes, ema12, ema26, dif, dea, rsi6, rsi12, rsi24,
               kdj_k, kdj_d, kdj_j, atr, obv, vpt)


# ---------------------------------------------------------------- 各列计算
# (列名, fn(bars, i, ctx) -> float|None)

def _sma_of(vals: list[float], i: int, n: int) -> Optional[float]:
    if i + 1 < n:
        return None
    return sum(vals[i - n + 1 : i + 1]) / n


def _c_ma(bars, i, ctx, n):
    return _sma_of(ctx.closes, i, n)


def _c_vol_ma(bars, i, ctx, n):
    return _sma_of(ctx.volumes, i, n)


def _c_mom(bars, i, ctx, n):
    if i < n:
        return None
    prev = ctx.closes[i - n]
    if prev == 0:
        return None
    return ctx.closes[i] / prev - 1.0


def _c_ema(bars, i, ctx, n):
    if i + 1 < 26:
        return None
    return ctx.ema12[i] if n == 12 else ctx.ema26[i]


def _c_cci(bars, i, ctx):
    n = 14
    if i + 1 < n:
        return None
    seg = bars[i - n + 1 : i + 1]
    tp = (bars[i].high + bars[i].low + bars[i].close) / 3.0
    tps = [(b.high + b.low + b.close) / 3.0 for b in seg]
    mtp = _mean(tps)
    mad = sum(abs(t - mtp) for t in tps) / n
    if mad == 0:
        return None
    return (tp - mtp) / (0.015 * mad)


def _c_wr(bars, i, ctx):
    n = 14
    if i + 1 < n:
        return None
    seg = bars[i - n + 1 : i + 1]
    hh = max(b.high for b in seg)
    ll = min(b.low for b in seg)
    if hh == ll:
        return None
    return (hh - bars[i].close) / (hh - ll) * 100.0


def _c_bias(bars, i, ctx, n):
    ma = _c_ma(bars, i, ctx, n)
    if ma is None or ma == 0:
        return None
    return (ctx.closes[i] - ma) / ma * 100.0


def _c_boll(bars, i, ctx):
    n = 20
    if i + 1 < n:
        return None, None, None
    closes = ctx.closes[i - n + 1 : i + 1]
    mid = _mean(closes)
    sd = _std_pop(closes)
    return mid, mid + 2 * sd, mid - 2 * sd


def _c_std20(bars, i, ctx):
    n = 20
    if i + 1 < n + 1:
        return None
    rets = [ctx.closes[k] / ctx.closes[k - 1] - 1.0 for k in range(i - n + 1, i + 1) if ctx.closes[k - 1] > 0]
    if len(rets) < n:
        return None
    return _std_pop(rets)


def _c_corr_pv(bars, i, ctx):
    """20 对样本：日收盘收益率 vs 成交量环比变化率的 Pearson 相关（量价同步性）"""
    n = 20
    if i + 1 < n + 1:
        return None
    rets: list[float] = []
    vchg: list[float] = []
    for k in range(i - n + 1, i + 1):
        if ctx.closes[k - 1] <= 0 or ctx.volumes[k - 1] <= 0:
            return None
        rets.append(ctx.closes[k] / ctx.closes[k - 1] - 1.0)
        vchg.append(ctx.volumes[k] / ctx.volumes[k - 1] - 1.0)
    return _pearson(rets, vchg)


def _c_mfi(bars, i, ctx):
    n = 14
    if i + 1 < n + 1:
        return None
    pos = 0.0
    neg = 0.0
    for k in range(i - n + 1, i + 1):
        b, p = bars[k], bars[k - 1]
        tp = (b.high + b.low + b.close) / 3.0
        ptp = (p.high + p.low + p.close) / 3.0
        if tp > ptp:
            pos += b.volume
        elif tp < ptp:
            neg += b.volume
    if neg == 0:
        return 100.0 if pos > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + pos / neg)


def _c_cmf(bars, i, ctx):
    n = 20
    if i + 1 < n:
        return None
    num = 0.0
    den = 0.0
    for b in bars[i - n + 1 : i + 1]:
        rng = b.high - b.low
        mfm = 0.0 if rng == 0 else ((b.close - b.low) - (b.high - b.close)) / rng
        num += mfm * b.volume
        den += b.volume
    if den == 0:
        return None
    return num / den


def _c_pos20(bars, i, ctx):
    n = 20
    if i + 1 < n:
        return None
    seg = bars[i - n + 1 : i + 1]
    ll = min(b.low for b in seg)
    hh = max(b.high for b in seg)
    if hh == ll:
        return None
    return (ctx.closes[i] - ll) / (hh - ll)


def _c_vol_pos20(bars, i, ctx):
    n = 20
    if i + 1 < n:
        return None
    vols = ctx.volumes[i - n + 1 : i + 1]
    mn, mx = min(vols), max(vols)
    if mx == mn:
        return None
    return (ctx.volumes[i] - mn) / (mx - mn)


def _c_new_high20(bars, i, ctx):
    """收盘创前 20 个交易日（不含当日）新高 → 1 否则 0"""
    n = 20
    if i < n:
        return None
    prev_high = max(b.high for b in bars[i - n : i])
    return 1.0 if ctx.closes[i] >= prev_high else 0.0


def _c_new_low20(bars, i, ctx):
    n = 20
    if i < n:
        return None
    prev_low = min(b.low for b in bars[i - n : i])
    return 1.0 if ctx.closes[i] <= prev_low else 0.0


COLUMNS: list[tuple[str, Callable]] = [
    # ---- 核心技术因子（2026-09-05 数据精简：|ICIR|≥0.25 @ ashare H5 中性化，其余 33 个归档并已删列） ----
    # 趋势/动量
    ("dif", lambda b, i, c: c.dif[i] if i + 1 >= 60 else None),
    ("dea", lambda b, i, c: c.dea[i] if i + 1 >= 60 else None),
    ("mom20", lambda b, i, c: _c_mom(b, i, c, 20)),
    ("mom60", lambda b, i, c: _c_mom(b, i, c, 60)),
    # 摆动（仅 RSI24 达标）
    ("rsi24", lambda b, i, c: c.rsi24[i]),
    # 量价关系（核心）
    ("vr10", lambda b, i, c: (c.volumes[i] / v) if (v := _c_vol_ma(b, i, c, 10)) and v > 0 else None),
    ("vr20", lambda b, i, c: (c.volumes[i] / v) if (v := _c_vol_ma(b, i, c, 20)) and v > 0 else None),
    ("vol_trend", lambda b, i, c: (lambda v5, v20: (v5 / v20) if (v5 is not None and v20 and v20 > 0) else None)(_c_vol_ma(b, i, c, 5), _c_vol_ma(b, i, c, 20))),
    ("vol_cv20", lambda b, i, c: (lambda vv: (_std_pop(vv) / _mean(vv)) if len(vv) >= 20 and _mean(vv) > 0 else None)(c.volumes[max(0, i - 19) : i + 1])),
    ("vol_pos20", lambda b, i, c: _c_vol_pos20(b, i, c)),
    ("corr_pv20", lambda b, i, c: _c_corr_pv(b, i, c)),
    ("vpt", lambda b, i, c: c.vpt[i]),
    ("cmf20", lambda b, i, c: _c_cmf(b, i, c)),
    ("mfi14", lambda b, i, c: _c_mfi(b, i, c)),
]

COLUMN_NAMES = [name for name, _ in COLUMNS]


def compute_rows(bars: list[DailyBar]) -> list[IndicatorRow]:
    """对单标的升序 bars 计算全部因子行（含不足窗口的 NULL 行，写入时按需过滤）"""
    ctx = _build_ctx(bars)
    rows: list[IndicatorRow] = []
    for i in range(len(bars)):
        values: list[Optional[float]] = []
        for _name, fn in COLUMNS:
            try:
                v = fn(bars, i, ctx)
            except Exception:
                v = None
            if v is not None and isinstance(v, float) and not math.isfinite(v):
                v = None
            values.append(v)
        rows.append(IndicatorRow(symbol=bars[i].symbol, d=bars[i].d, values=values))
    return rows


# ---------------------------------------------------------------- DB 层

def _to_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return v


def ensure_table(conn) -> None:
    cols = ", ".join(f'"{c}" DOUBLE PRECISION' for c in COLUMN_NAMES)
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS tdx.raw_stock_indicators (
                symbol TEXT NOT NULL,
                "date" DATE NOT NULL,
                {cols},
                UNIQUE (symbol, date)
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_stock_indicators_symbol_date "
            "ON tdx.raw_stock_indicators (symbol, date);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_stock_indicators_date "
            "ON tdx.raw_stock_indicators (date);"
        )
    conn.commit()


def get_distinct_symbols(conn, limit: int | None) -> list[str]:
    sql = "SELECT DISTINCT symbol FROM tdx.raw_stocks_daily ORDER BY symbol"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    with conn.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]


def get_max_indicator_date(conn) -> date | None:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(date) FROM tdx.raw_stock_indicators")
        r = cur.fetchone()
    if not r or r[0] is None:
        return None
    return _to_date(r[0])


def query_stock_data(conn, symbol: str, start_date: date | None) -> list[DailyBar]:
    if start_date is None:
        sql = """
            SELECT symbol, date, open, high, low, close, amount, volume
            FROM tdx.raw_stocks_daily
            WHERE symbol = %s
            ORDER BY date ASC
        """
        args = (symbol,)
    else:
        sql = """
            SELECT symbol, date, open, high, low, close, amount, volume
            FROM tdx.raw_stocks_daily
            WHERE symbol = %s AND date >= %s
            ORDER BY date ASC
        """
        args = (symbol, start_date)
    with conn.cursor() as cur:
        cur.execute(sql, args)
        rows = cur.fetchall()
    out: list[DailyBar] = []
    for r in rows:
        out.append(
            DailyBar(
                symbol=str(r[0]),
                d=_to_date(r[1]),
                open=float(r[2]),
                high=float(r[3]),
                low=float(r[4]),
                close=float(r[5]),
                amount=float(r[6]),
                volume=float(r[7]),
            )
        )
    return out


def insert_rows(conn, rows: list[IndicatorRow], batch: int) -> int:
    from psycopg2.extras import execute_values

    if not rows:
        return 0
    names = ", ".join(f'"{c}"' for c in COLUMN_NAMES)
    tuples = [(r.symbol, r.d) + tuple(r.values) for r in rows]
    total = 0
    for i in range(0, len(tuples), batch):
        chunk = tuples[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO tdx.raw_stock_indicators (symbol, "date", {names})
                VALUES %s
                ON CONFLICT (symbol, date) DO UPDATE SET
                    {", ".join(f'"{c}" = EXCLUDED."{c}"' for c in COLUMN_NAMES)}
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def delete_tail(conn, since: date) -> None:
    """清理 date >= since 的残留行（上次中断的残尾），保证增量可重算"""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM tdx.raw_stock_indicators WHERE date >= %s", (since,))
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="calc_indicator → tdx.raw_stock_indicators（技术指标 + 量价因子，纯 Python）"
    )
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--full", action="store_true", help="TRUNCATE raw_stock_indicators 后全量重算")
    parser.add_argument("--batch", type=int, default=5000, help="每批插入行数")
    parser.add_argument("--limit-symbols", type=int, default=0, metavar="N", help="仅处理前 N 个 symbol（0=全部）")
    args = parser.parse_args()

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        ensure_table(conn)

        with conn.cursor() as cur:
            cur.execute("SELECT MAX(date) FROM tdx.raw_stocks_daily")
            r = cur.fetchone()
            raw_max = _to_date(r[0]) if r and r[0] is not None else None
        if raw_max is None:
            print("错误: tdx.raw_stocks_daily 为空，请先运行 tdx_import_daily_bar.py", file=sys.stderr)
            sys.exit(1)

        ind_max = get_max_indicator_date(conn)

        if args.full:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE tdx.raw_stock_indicators;")
            conn.commit()
            write_since: date | None = None
            load_start: date | None = None
            print("模式: 全量（已 TRUNCATE raw_stock_indicators）")
        elif ind_max is None or ind_max.year <= 1900:
            write_since = None
            load_start = None
            print("模式: 全量(空表)")
        elif ind_max >= raw_max:
            print(f"raw_stock_indicators 已追平日线最新日（{raw_max}），无需增量。")
            return
        else:
            # 增量：清理残尾后，从 ind_max 回看 LOOKBACK 天装载日线重算，
            # 仅写入 date > ind_max 的行（旧行不覆盖，避免窗口不足写入 NULL）
            delete_tail(conn, ind_max + timedelta(days=1))
            load_start = ind_max - timedelta(days=LOOKBACK_NATURAL_DAYS)
            write_since = ind_max + timedelta(days=1)
            print(
                f"模式: 增量 | indicators.max(date)={ind_max} | 日线最新={raw_max} | "
                f"回看装载自 {load_start}，仅写入 {write_since} 之后"
            )

        limit = args.limit_symbols if args.limit_symbols > 0 else None
        symbols = get_distinct_symbols(conn, limit)
        print(f"处理 {len(symbols):,} 个标的 …")

        total_rows = 0
        buf: list[IndicatorRow] = []
        for idx, sym in enumerate(symbols, 1):
            bars = query_stock_data(conn, sym, load_start)
            if not bars:
                continue
            rows = compute_rows(bars)
            if write_since is not None:
                rows = [r for r in rows if r.d >= write_since]
            buf.extend(rows)
            if len(buf) >= args.batch:
                total_rows += insert_rows(conn, buf, args.batch)
                buf = []
            if idx % 500 == 0:
                print(f"  … {idx}/{len(symbols)} 标的, 已写入 {total_rows:,} 行")
        if buf:
            total_rows += insert_rows(conn, buf, args.batch)

        print(f"完成: 共写入/更新 tdx.raw_stock_indicators {total_rows:,} 行")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
