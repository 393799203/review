#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合回测服务：多因子中性化 zscore 等权打分 → top N% 持仓 → T+1 开盘入场、
每 rebalance 交易日再平衡（v_hfq_daily 后复权），返回绩效 + 净值序列 + 最新股票池。

逻辑对齐 tdx_daily/backtest_factor_standalone.py，用 TDX 外部行情库（只读）。
"""

import math
from datetime import date as date_type, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque

from sqlalchemy import text

from app.core.tdx_db import require_tdx_engine

DEFAULT_FACTORS = ['vol_cv20', 'corr_pv20']  # 推荐因子（|ICIR|≥0.5 @ ashare H5 中性化）
VALID_UNIVERSES = ('all', 'ashare', 'main', 'gem', 'hs300')
RANK = 100  # 每期最多返回的最新持仓数


def _to_date(v) -> date_type:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date_type):
        return v
    return v


def _winsorize(values, lo=0.01, hi=0.99):
    if len(values) < 10:
        return list(values)
    vs = sorted(values)
    v_lo = vs[min(int(lo * len(vs)), len(vs) - 1)]
    v_hi = vs[min(int(hi * len(vs)) - 1, len(vs) - 1)]
    return [max(v_lo, min(v, v_hi)) for v in values]


def _neutralize(symbols, values, ind_map, lnmv_map, min_group=5):
    n = len(values)
    wv = _winsorize(values)
    ind_sum: dict = {}
    ind_cnt: dict = {}
    for s, v in zip(symbols, wv):
        code = ind_map.get(s)
        if code:
            ind_sum[code] = ind_sum.get(code, 0.0) + v
            ind_cnt[code] = ind_cnt.get(code, 0) + 1
    overall = sum(wv) / n
    ind_mean = {c: (ind_sum[c] / ind_cnt[c] if ind_cnt[c] >= min_group else overall) for c in ind_sum}
    dem = [wv[i] - (ind_mean.get(ind_map.get(symbols[i]), overall) if ind_map.get(symbols[i]) else overall) for i in range(n)]
    xs, ys = [], []
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
    return [dem[i] - (b * lm + a) if (lm := lnmv_map.get(symbols[i])) is not None else dem[i] for i in range(n)]


def _zscore(vals):
    n = len(vals)
    if n < 3:
        return [0.0] * n
    mu = sum(vals) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / n)
    if sd == 0:
        return [0.0] * n
    return [(v - mu) / sd for v in vals]


class BacktestService:
    """组合回测服务类"""

    def __init__(self):
        self.engine = require_tdx_engine()

    # ---------- 数据查询 ----------

    def _calendar(self, min_date: Optional[date_type] = None, max_date: Optional[date_type] = None) -> list[date_type]:
        sql = "SELECT DISTINCT date FROM tdx.v_hfq_daily ORDER BY date"
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
        out = [_to_date(r[0]) for r in rows]
        if min_date:
            out = [d for d in out if d >= min_date]
        if max_date:
            out = [d for d in out if d <= max_date]
        return out

    def _closes(self, d: date_type) -> dict[str, float]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT symbol, close FROM tdx.v_hfq_daily WHERE date = :d"), {'d': d}
            ).fetchall()
        return {str(r[0]): float(r[1]) for r in rows}

    def _opens(self, d: date_type) -> dict[str, float]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT symbol, open FROM tdx.v_hfq_daily WHERE date = :d"), {'d': d}
            ).fetchall()
        return {str(r[0]): float(r[1]) for r in rows}

    def _lnmv(self, d: date_type) -> dict[str, float]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT symbol, LN(totalmv) FROM tdx.raw_stocks_basic WHERE date = :d AND totalmv > 0"),
                {'d': d},
            ).fetchall()
        return {str(r[0]): float(r[1]) for r in rows}

    def _industry_map(self) -> dict[str, str]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT symbol, sw1_code FROM tdx.dim_sw_industry WHERE is_latest = 1 AND sw1_code IS NOT NULL")
            ).fetchall()
        return {str(r[0]): str(r[1]) for r in rows}

    def _member_symbols(self, universe: str) -> Optional[set[str]]:
        if universe not in ('hs300',):
            return None
        with self.engine.connect() as conn:
            rows = conn.execute(
                text('SELECT symbol FROM tdx.dim_index_member WHERE "index" = :u'), {'u': universe}
            ).fetchall()
        return {str(r[0]) for r in rows}

    def _factor_rows(self, d: date_type, factors: list[str], universe: str, member: Optional[set[str]]) -> list[tuple[str, list[Optional[float]]]]:
        cols = ", ".join(f'f."{c}"' for c in factors)
        where = ["f.date = :d"]
        params: dict = {'d': d}
        prefixes = {
            'ashare': ('sh60%', 'sh68%', 'sz00%', 'sz30%'),
            'main': ('sh60%', 'sz00%'),
            'gem': ('sh68%', 'sz30%'),
        }.get(universe)
        if prefixes:
            like = " OR ".join(["f.symbol LIKE :p%d" % i for i in range(len(prefixes))])
            where.append(f"({like})")
            for i, p in enumerate(prefixes):
                params[f'p{i}'] = p
        if member is not None:
            if not member:
                return []
            where.append("f.symbol = ANY(:m)")
            params['m'] = sorted(member)
        where.append("(i.name IS NULL OR i.name NOT LIKE '%%ST%%')")
        sql = f"""
            SELECT f.symbol, {cols}
            FROM tdx.raw_stock_indicators f
            LEFT JOIN tdx.dim_sw_industry i ON i.symbol = f.symbol AND i.is_latest = 1
            WHERE {" AND ".join(where)}
        """
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        out = []
        for r in rows:
            vals = []
            for v in r[1:]:
                try:
                    vals.append(float(v) if v is not None else None)
                except (TypeError, ValueError):
                    vals.append(None)
            out.append((str(r[0]), vals))
        return out

    def _factor_directions(self, factors: list[str], universe: str) -> dict[str, float]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT factor, mean_ic FROM tdx.factor_eval_summary "
                     "WHERE universe = :u AND method = 'neutral' AND horizon = 5"),
                {'u': universe},
            ).fetchall()
        m = {str(r[0]): float(r[1]) for r in rows if r[1] is not None}
        return {f: (-1.0 if m.get(f, 0) < 0 else 1.0) for f in factors}

    def _benchmark(self, calendar: list[date_type]) -> tuple[list[date_type], list[float]]:
        """沪深300 收盘序列（对齐交易日历，缺失日 None→前值）"""
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT date, close FROM tdx.v_hfq_daily WHERE symbol = 'sh000300' ORDER BY date")
            ).fetchall()
        closes = {_to_date(r[0]): float(r[1]) for r in rows}
        dates, values = [], []
        last = None
        for d in calendar:
            v = closes.get(d)
            if v is not None:
                last = v
            if last is not None:
                dates.append(d)
                values.append(last)
        return dates, values

    # ---------- 主回测 ----------

    def run_via_payload(self, payload: dict) -> Tuple[bool, str, Optional[Dict]]:
        """控制器入口：解析 JSON payload，返回 (success, message, result)"""
        try:
            factors = payload.get('factors') or None
            universe = str(payload.get('universe') or 'ashare')
            top_pct = float(payload.get('top_pct', 0.2))
            top_k = int(payload.get('top_k') or 0)
            rebalance = int(payload.get('rebalance', 5))
            cost = float(payload.get('cost', 0.0))
            min_date = payload.get('min_date') or None
            max_date = payload.get('max_date') or None
            stop_mode = str(payload.get('stop_mode') or 'trail')   # off|fixed|trail|atr
            stop_pct = float(payload.get('stop_pct', 0.15))        # 固定/灾难止损比例
            trail_pct = float(payload.get('trail_pct', 0.10))      # 移动止盈：从峰值回撤比例
            atr_mult = float(payload.get('atr_mult', 2.0))         # ATR 止损倍数
            ma_exit = int(payload.get('ma_exit', 10))              # 跌破 N 日均线卖出（0=关闭）
            if factors is not None and not isinstance(factors, list):
                return False, 'factors 必须为数组', None
            if not 0 < top_pct <= 1:
                return False, 'top_pct 必须在 (0,1]', None
            if stop_mode not in ('off', 'fixed', 'trail', 'atr'):
                return False, 'stop_mode 可选：off/fixed/trail/atr', None
            if not 0 <= stop_pct < 1 or not 0 <= trail_pct < 1:
                return False, 'stop_pct/trail_pct 必须在 [0,1)', None
            if atr_mult <= 0:
                return False, 'atr_mult 必须 >0', None
            if ma_exit < 0:
                return False, 'ma_exit 必须 ≥0', None
            result = self.run(factors, universe, top_pct, top_k, rebalance, cost,
                              min_date, max_date, stop_mode, stop_pct, trail_pct, atr_mult, ma_exit)
            return True, '回测完成', result
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            return False, f'回测失败: {e}', None

    def run(self, factors: Optional[List[str]], universe: str,
            top_pct: float, top_k: int, rebalance: int, cost: float,
            min_date: Optional[str], max_date: Optional[str],
            stop_mode: str = 'trail', stop_pct: float = 0.15,
            trail_pct: float = 0.10, atr_mult: float = 2.0, ma_exit: int = 10) -> Dict:
        factors = factors or DEFAULT_FACTORS
        if universe not in VALID_UNIVERSES:
            raise ValueError(f'universe 可选：{" / ".join(VALID_UNIVERSES)}')
        if not 0 < top_pct <= 1:
            raise ValueError('top_pct 必须在 (0,1]')
        if rebalance < 1:
            raise ValueError('rebalance 必须 ≥1')

        min_d = date_type.fromisoformat(min_date) if min_date else None
        max_d = date_type.fromisoformat(max_date) if max_date else None
        calendar = self._calendar(min_d, max_d)
        if len(calendar) < rebalance + 2:
            raise ValueError('区间内交易日不足')

        # ===== 每日轮动回测 =====
        # 口径：每日收盘按因子打分 → 次日开盘调仓（掉出前 N% 自动卖出、新进自动买入，
        # 仍在池内的持有不动）→ 收盘按持仓计当日收益；成本按实际买卖金额（换手）扣。
        directions = self._factor_directions(factors, universe)
        industry_map = self._industry_map()
        member = self._member_symbols(universe)

        # 样本过滤（前缀或成分集合），价格/市值查询同样过滤，避免全市场 226 天 ×1万+ 标的
        prefixes = {
            'ashare': ('sh60%', 'sh68%', 'sz00%', 'sz30%'),
            'main': ('sh60%', 'sz00%'),
            'gem': ('sh68%', 'sz30%'),
        }.get(universe)
        extra_where = ""
        extra_params: dict = {}
        if prefixes:
            like = " OR ".join([f"symbol LIKE :p{i}" for i in range(len(prefixes))])
            extra_where = f" AND ({like})"
            for k, p in enumerate(prefixes):
                extra_params[f'p{k}'] = p
        elif member is not None:
            extra_where = " AND symbol = ANY(:m)"
            extra_params['m'] = sorted(member)

        cal_dates = list(calendar)
        with self.engine.connect() as conn:
            closes_all: dict = {}
            for r in conn.execute(
                    text(f"SELECT date, symbol, close FROM tdx.v_hfq_daily "
                         f"WHERE date = ANY(:ds){extra_where}"),
                    {**{'ds': cal_dates}, **extra_params}).fetchall():
                closes_all.setdefault(_to_date(r[0]), {})[str(r[1])] = float(r[2])
            opens_all: dict = {}
            for r in conn.execute(
                    text(f"SELECT date, symbol, open FROM tdx.v_hfq_daily "
                         f"WHERE date = ANY(:ds){extra_where}"),
                    {**{'ds': cal_dates}, **extra_params}).fetchall():
                opens_all.setdefault(_to_date(r[0]), {})[str(r[1])] = float(r[2])
            lows_all: dict = {}
            for r in conn.execute(
                    text(f"SELECT date, symbol, low FROM tdx.v_hfq_daily "
                         f"WHERE date = ANY(:ds){extra_where}"),
                    {**{'ds': cal_dates}, **extra_params}).fetchall():
                lows_all.setdefault(_to_date(r[0]), {})[str(r[1])] = float(r[2])
            highs_all: dict = {}
            for r in conn.execute(
                    text(f"SELECT date, symbol, high FROM tdx.v_hfq_daily "
                         f"WHERE date = ANY(:ds){extra_where}"),
                    {**{'ds': cal_dates}, **extra_params}).fetchall():
                highs_all.setdefault(_to_date(r[0]), {})[str(r[1])] = float(r[2])
            lnmv_all: dict = {}
            for r in conn.execute(
                    text(f"SELECT date, symbol, LN(totalmv) FROM tdx.raw_stocks_basic "
                         f"WHERE date = ANY(:ds) AND totalmv > 0{extra_where}"),
                    {**{'ds': cal_dates}, **extra_params}).fetchall():
                lnmv_all.setdefault(_to_date(r[0]), {})[str(r[1])] = float(r[2])
            cols = ", ".join(f'f."{c}"' for c in factors)
            fwhere = ["f.date = ANY(:ds)"]
            if prefixes:
                like = " OR ".join([f"f.symbol LIKE :p{i}" for i in range(len(prefixes))])
                fwhere.append(f"({like})")
            if member is not None:
                fwhere.append("f.symbol = ANY(:m)")
            fwhere.append("(i.name IS NULL OR i.name NOT LIKE '%%ST%%')")
            fsql = f"""
                SELECT f.date, f.symbol, {cols}
                FROM tdx.raw_stock_indicators f
                LEFT JOIN tdx.dim_sw_industry i ON i.symbol = f.symbol AND i.is_latest = 1
                WHERE {" AND ".join(fwhere)}
            """
            fparams: dict = {'ds': cal_dates}
            if prefixes:
                for k, p in enumerate(prefixes):
                    fparams[f'p{k}'] = p
            if member is not None:
                fparams['m'] = sorted(member)
            factor_map: dict[date_type, list[tuple[str, list[Optional[float]]]]] = {}
            for r in conn.execute(text(fsql), fparams).fetchall():
                vals = []
                for v in r[2:]:
                    try:
                        vals.append(float(v) if v is not None else None)
                    except (TypeError, ValueError):
                        vals.append(None)
                factor_map.setdefault(_to_date(r[0]), []).append((str(r[1]), vals))

        # ATR14 预计算（Wilder 平滑），atr 止损用
        atr_map: dict[str, dict[date_type, float]] = {}
        if stop_mode == 'atr':
            sym_prev: dict[str, float] = {}
            sym_dq: dict[str, deque] = {}
            sym_atr: dict[str, float] = {}
            for d in cal_dates:
                hs = highs_all.get(d, {})
                ls = lows_all.get(d, {})
                cs = closes_all.get(d, {})
                for sym, h in hs.items():
                    l = ls.get(sym)
                    c = cs.get(sym)
                    if l is None or c is None:
                        continue
                    pc = sym_prev.get(sym)
                    if pc is None:
                        sym_prev[sym] = c
                        continue
                    tr = max(h - l, abs(h - pc), abs(l - pc))
                    dq = sym_dq.get(sym)
                    if dq is None:
                        dq = deque(maxlen=14)
                        sym_dq[sym] = dq
                    dq.append(tr)
                    if len(dq) == 14:
                        if sym in sym_atr:
                            sym_atr[sym] = (sym_atr[sym] * 13 + tr) / 14
                        else:
                            sym_atr[sym] = sum(dq) / 14
                        atr_map.setdefault(sym, {})[d] = sym_atr[sym]
                    sym_prev[sym] = c

        def _score_of(t: date_type) -> Optional[dict[str, float]]:
            rows = factor_map.get(t, [])
            if not rows:
                return None
            lnmv = lnmv_all.get(t, {})
            per_stock: dict[str, list[float]] = defaultdict(list)
            ok = 0
            for fi, fname in enumerate(factors):
                pairs = [(s, r[fi]) for s, r in rows if r[fi] is not None]
                if not pairs:
                    continue
                syms = [p[0] for p in pairs]
                vals = [p[1] for p in pairs]
                nz = _neutralize(syms, vals, industry_map, lnmv)
                zs = _zscore([v if v is not None else 0.0 for v in nz])
                sign = directions.get(fname, 1.0)
                for j, s in enumerate(syms):
                    per_stock[s].append(sign * zs[j])
                ok += 1
            if ok < min(3, len(factors)):
                return None
            return {s: (sum(v) / len(v)) for s, v in per_stock.items() if v}

# ===== 每日轮动 + 止盈止损 =====
        # 持仓池：units[sym] = {unit(投入份数), basis(买入开盘价), buy_date, last_mark}
        # 止损：当日最低 ≤ 买入价×(1−stop_loss) → 以止损价卖出（跳空低开则按开盘价）
        # 止盈/趋势退出：收盘 < 最近 ma_exit 日收盘均值 → 以收盘卖出
        # 成本：买入扣 unit×(1−cost)，卖出扣 proceeds×(1−cost)（单边）
        units: dict[str, dict] = {}
        cash = 1.0
        trades: list[dict] = []
        prev_nav = 1.0
        nav = 1.0
        nav_series: list[dict] = []
        monthly_ret: dict[str, float] = defaultdict(lambda: 1.0)
        latest_score: dict[str, float] = {}
        close_deque: dict[str, deque] = {}   # 各 symbol 最近 ma_exit 日收盘（均线退出用）
        ma_win = max(ma_exit, 1)
        for k in range(1, len(cal_dates)):
            prev_d = cal_dates[k - 1]
            cur_d = cal_dates[k]
            opens_cur = opens_all.get(cur_d, {})
            closes_cur = closes_all.get(cur_d, {})
            lows_cur = lows_all.get(cur_d, {})
            if not opens_cur or not closes_cur:
                continue
            # 更新收盘滚动窗（含当日）
            for sym, c in closes_cur.items():
                dq = close_deque.get(sym)
                if dq is None:
                    dq = deque(maxlen=ma_win)
                    close_deque[sym] = dq
                dq.append(c)
            # 打分来自 prev_d 收盘（T+1 执行）
            score = _score_of(prev_d)
            if score is None:
                continue
            if top_k > 0:
                pool = set(sorted(score, key=lambda s: -score[s])[:top_k])
            else:
                kk = max(1, int(round(len(score) * top_pct)))
                pool = set(sorted(score, key=lambda s: -score[s])[:kk])
            if not pool:
                continue
            # 1) 退出：止损/移动止盈/ATR/跌破均线 → 卖；然后"掉出池" → 开盘卖出
            for sym in list(units):
                u = units[sym]
                basis = u['basis']
                low = lows_cur.get(sym)
                open_px = opens_cur.get(sym)
                close_px = closes_cur.get(sym)
                if close_px is not None:
                    u['peak'] = max(u.get('peak', basis), close_px)
                exit_px = None
                reason = None
                if stop_mode == 'fixed' and low is not None and open_px is not None:
                    stop_px = basis * (1 - stop_pct)
                    if low <= stop_px:
                        exit_px = open_px if open_px <= stop_px else stop_px
                        reason = '固定止损'
                elif stop_mode == 'trail' and low is not None and open_px is not None:
                    trail_px = u.get('peak', basis) * (1 - trail_pct)
                    if low <= trail_px:
                        exit_px = open_px if open_px <= trail_px else trail_px
                        reason = '移动止盈'
                elif stop_mode == 'atr' and low is not None and open_px is not None:
                    atr_now = atr_map.get(sym, {}).get(cur_d)
                    stop_px = (basis - atr_mult * atr_now) if atr_now else basis * (1 - stop_pct)
                    if low <= stop_px:
                        exit_px = open_px if open_px <= stop_px else stop_px
                        reason = 'ATR止损'
                if exit_px is None and ma_exit > 0 and close_px is not None:
                    dq = close_deque.get(sym)
                    if dq is not None and len(dq) == ma_win:
                        ma = sum(dq) / ma_win
                        if close_px < ma:
                            exit_px = close_px
                            reason = '跌破均线'
                if exit_px is not None:
                    pnl = (exit_px / basis - 1.0) * 100.0
                    cash += u['unit'] * (exit_px / basis) * (1 - cost)
                    trades.append({'date': cur_d.isoformat(), 'symbol': sym, 'dir': 'sell',
                                   'price': round(exit_px, 2), 'reason': reason or '卖出', 'pnl': round(pnl, 2)})
                    del units[sym]
            # 1.5) 掉出池：仍在持有但不在新池 → 开盘卖出（轮动退出）
            for sym in list(units):
                if sym not in pool:
                    u = units[sym]
                    basis = u['basis']
                    open_px = opens_cur.get(sym)
                    if open_px and open_px > 0:
                        pnl = (open_px / basis - 1.0) * 100.0
                        cash += u['unit'] * (open_px / basis) * (1 - cost)
                        trades.append({'date': cur_d.isoformat(), 'symbol': sym, 'dir': 'sell',
                                       'price': round(open_px, 2), 'reason': '掉出池', 'pnl': round(pnl, 2)})
                        del units[sym]
            # 2) 买入池内新股（现金等分；保留已在池中的持仓）
            held = set(units)
            new_syms = [s for s in pool if s not in held and opens_cur.get(s)]
            if cash > 0 and new_syms:
                unit_each = cash / len(new_syms)
                for s in new_syms:
                    units[s] = {'unit': unit_each * (1 - cost),
                                'basis': opens_cur[s], 'buy_date': cur_d,
                                'peak': opens_cur[s]}
                    trades.append({'date': cur_d.isoformat(), 'symbol': s, 'dir': 'buy',
                                   'price': round(opens_cur[s], 2), 'reason': '买入', 'pnl': None})
                cash = 0.0
            # 3) 收盘估值
            V = cash
            for sym, u in units.items():
                close_px = closes_cur.get(sym)
                if close_px:
                    u['last_mark'] = close_px
                    V += u['unit'] * (close_px / u['basis'])
                else:
                    V += u['unit'] * (u.get('last_mark', u['basis']) / u['basis'])
            day_ret = V / prev_nav - 1.0
            nav = V
            nav_series.append({'date': cur_d.isoformat(), 'nav': round(nav, 6)})
            mk = cur_d.strftime('%Y-%m')
            monthly_ret[mk] *= (1 + day_ret)
            prev_nav = V
            latest_score = {s: score[s] for s in units if s in score}

        if not nav_series:
            raise ValueError('回测无数据：检查因子/区间/样本')

        # 最新持仓（当前仍持有的池，入场日=各自买入日、入场价=买入开盘价，未卖出）
        latest_holdings = []
        rows_h = [(s, u) for s, u in units.items()]
        syms = [x[0] for x in rows_h]
        name_map: dict[str, str] = {}
        if syms:
            with self.engine.connect() as conn:
                for r in conn.execute(
                        text("SELECT symbol, name FROM tdx.dim_sw_industry "
                             "WHERE symbol = ANY(:s) AND is_latest = 1"),
                        {'s': syms}).fetchall():
                    name_map[str(r[0])] = str(r[1])
        for s, u in sorted(rows_h, key=lambda x: x[1].get('buy_date') or date_type.min):
            latest_holdings.append({
                'symbol': s,
                'code': s[2:],
                'name': name_map.get(s, s[2:]),
                'score': round(float(latest_score.get(s, 0.0)), 4),
                'entry_date': u['buy_date'].isoformat() if u.get('buy_date') else None,
                'entry_open': round(float(u['basis']), 2) if u.get('basis') else None,
                'exit_date': None,  # 仍在持有
                'exit_close': round(float(u.get('last_mark')), 2) if u.get('last_mark') else None,
            })

        # 绩效（日频）
        prev = 1.0
        peak = 1.0
        max_dd = 0.0
        for item in nav_series:
            v = item['nav']
            rv = v / prev - 1.0
            prev = v
            peak = max(peak, v)
            max_dd = min(max_dd, v / peak - 1.0)
        total = nav_series[-1]['nav'] - 1.0
        days = (date_type.fromisoformat(nav_series[-1]['date']) - date_type.fromisoformat(nav_series[0]['date'])).days
        years = max(days / 365.0, 1e-9)
        rets_arr = [nav_series[j]['nav'] / nav_series[j - 1]['nav'] - 1.0 for j in range(1, len(nav_series))]
        mean_r = sum(rets_arr) / len(rets_arr) if rets_arr else 0.0
        sd_r = math.sqrt(sum((r - mean_r) ** 2 for r in rets_arr) / len(rets_arr)) if rets_arr else 0.0
        annual = total / years
        sharpe = (mean_r / sd_r) * math.sqrt(252) if sd_r > 0 else 0.0
        calmar = annual / abs(max_dd) if max_dd != 0 else 0.0

        # 基准同期累计
        bd, bv = self._benchmark(calendar)
        bench_total = None
        if bd:
            bench_start = bv[0]
            bench_end = bv[-1]
            if bench_start and bench_start > 0:
                bench_total = bench_end / bench_start - 1.0

        # 基准净值序列（与 nav 日期对齐：用日历索引匹配）
        bnav_map = dict(zip(bd, bv))
        base_val = None
        bench_series = []
        for item in nav_series:
            d = date_type.fromisoformat(item['date'])
            v = bnav_map.get(d)
            if v is not None:
                if base_val is None:
                    base_val = v
                if base_val and base_val > 0:
                    bench_series.append({'date': d.isoformat(), 'nav': round(v / base_val, 6)})

        months = sorted(monthly_ret)
        monthly = [{'month': mk, 'ret': round(monthly_ret[mk] - 1.0, 4)} for mk in months]

        # 交易明细（最近 500 条，倒序），解析名称
        trades_out = trades[-500:][::-1]
        t_syms = list({x['symbol'] for x in trades_out})
        t_name: dict[str, str] = {}
        if t_syms:
            with self.engine.connect() as conn:
                for r in conn.execute(
                        text("SELECT symbol, name FROM tdx.dim_sw_industry "
                             "WHERE symbol = ANY(:s) AND is_latest = 1"),
                        {'s': t_syms}).fetchall():
                    t_name[str(r[0])] = str(r[1])
        for x in trades_out:
            x['code'] = x['symbol'][2:]
            x['name'] = t_name.get(x['symbol'], x['symbol'][2:])

        return {
            'params': {
                'factors': factors, 'universe': universe, 'top_pct': top_pct,
                'top_k': top_k, 'mode': 'daily_rotation', 'cost': cost,
                'stop_mode': stop_mode, 'stop_pct': stop_pct, 'trail_pct': trail_pct,
                'atr_mult': atr_mult, 'ma_exit': ma_exit,
                'start': nav_series[0]['date'], 'end': nav_series[-1]['date'],
                'periods': len(nav_series),
            },
            'metrics': {
                'total_ret': round(total, 4), 'annual_ret': round(annual, 4),
                'vol': round(sd_r * math.sqrt(252), 4),
                'sharpe': round(sharpe, 3), 'max_drawdown': round(max_dd, 4),
                'calmar': round(calmar, 3), 'bench_total': round(bench_total, 4) if bench_total is not None else None,
            },
            'nav': nav_series,
            'bench_nav': bench_series,
            'monthly': monthly,
            'holdings': latest_holdings,
            'trades': trades_out,
        }