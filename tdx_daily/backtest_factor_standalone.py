#!/usr/bin/env python3
r"""
多因子组合打分 + 组合回测。

组合分：每日对所选因子做「行业+ln市值」中性化 → 按方向（由 factor_eval_summary 的
mean_ic 符号自动确定，负向因子取负 z）→ 截面 z-score → 等权平均。

回测：按组合分每日（或每 rebalance 日）取 top N%（或 top K）等权持仓，
T+1 开盘买入、持有至第 H 个交易日收盘卖出（v_hfq_daily 后复权，无未来函数），
输出净值/年化/Sharpe/最大回撤/Calmar/换手/月度收益，对照基准（沪深300）。

用法:
  python backtest_factor_standalone.py                          # 默认核心7因子, ashare, 前20%, 每5日再平衡
  python backtest_factor_standalone.py --factors vol_cv20,mom60,cmf20 --top-k 30 --rebalance 5
  python backtest_factor_standalone.py --top-pct 0.1 --cost 0.001 --out-csv /tmp/nav.csv
  python backtest_factor_standalone.py --universe hs300 --max-date 2026-09-04

说明:
  - --factors 缺省为核心 7 个（|ICIR|>=0.3：vol_cv20,corr_pv20,vol_pos20,dea,rsi24,mom60,vr20）
  - 方向符号从 factor_eval_summary(ashare, neutral, H=5) 的 mean_ic 取；缺数据默认正向
  - 基准：tdx.v_hfq_daily 中 sh000300（沪深300指数）；缺失则用样本等权
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import date, datetime
from typing import Any, Optional

from tdx_config import get_db_url

from eval_factor_standalone import (
    get_calendar, get_closes, get_factor_rows, load_industry_map, load_lnmv_map,
    neutralize_values, UNIVERSE_PREFIXES, INDEX_UNIVERSES,
)

DEFAULT_DB_URL = get_db_url()

DEFAULT_FACTORS = ['vol_cv20', 'corr_pv20', 'vol_pos20', 'dea', 'rsi24', 'mom60', 'vr20']


def _to_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return v


def get_opens(conn, d: date) -> dict[str, float]:
    with conn.cursor() as cur:
        cur.execute("SELECT symbol, open FROM tdx.v_hfq_daily WHERE date = %s", (d,))
        return {str(r[0]): float(r[1]) for r in cur.fetchall()}


def get_benchmark_returns(conn, usable: list[date]) -> list[float]:
    """沪深300（sh000300）相邻交易日收益；不可用则返回空"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT date, close FROM tdx.v_hfq_daily WHERE symbol = %s AND date >= %s ORDER BY date",
            ("sh000300", usable[0]),
        )
        rows = cur.fetchall()
    closes = {_to_date(r[0]): float(r[1]) for r in rows if r[1]}
    out = []
    for i in range(1, len(usable)):
        c0 = closes.get(usable[i - 1])
        c1 = closes.get(usable[i])
        if c0 and c1 and c0 > 0:
            out.append((usable[i], c1 / c0 - 1.0))
    return out


def get_factor_directions(conn, factors: list[str], universe: str) -> dict[str, float]:
    """因子方向：mean_ic < 0 → -1（负向选股），>0 → +1；缺数据默认 +1"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT factor, mean_ic FROM tdx.factor_eval_summary "
            "WHERE universe = %s AND method = 'neutral' AND horizon = 5",
            (universe,),
        )
        rows = cur.fetchall()
    m = {str(r[0]): float(r[1]) for r in rows if r[1] is not None}
    return {f: (-1.0 if m.get(f, 0) < 0 else 1.0) for f in factors}


def zscore(vals: list[float]) -> list[float]:
    n = len(vals)
    if n < 3:
        return [0.0] * n
    mu = sum(vals) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / n)
    if sd == 0:
        return [0.0] * n
    return [(v - mu) / sd for v in vals]


def main() -> None:
    parser = argparse.ArgumentParser(description="多因子组合打分与回测")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--factors", type=str, default="", help="逗号分隔因子（缺省核心7个）")
    parser.add_argument("--universe", type=str, default="ashare",
                        choices=sorted(set(UNIVERSE_PREFIXES) | set(INDEX_UNIVERSES)),
                        help="样本（默认 ashare 沪深A股）")
    parser.add_argument("--top-pct", type=float, default=0.2, help="每日取组合分前 N% 持仓（默认 0.2）")
    parser.add_argument("--top-k", type=int, default=0, help="取前 K 只（>0 时覆盖 --top-pct）")
    parser.add_argument("--rebalance", type=int, default=5, help="每 N 个交易日再平衡（默认 5）")
    parser.add_argument("--cost", type=float, default=0.0, help="单边交易成本（默认 0，如 0.001=0.1%）")
    parser.add_argument("--min-date", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--max-date", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--min-factors", type=int, default=3, help="组合分最少可用因子数（默认 3）")
    parser.add_argument("--out-csv", type=str, default=None, help="导出净值 CSV 路径")
    args = parser.parse_args()

    if args.top_pct <= 0 or args.top_pct > 1:
        parser.error("--top-pct 必须在 (0,1]")
    if args.rebalance < 1:
        parser.error("--rebalance 必须 ≥1")

    import psycopg2

    factors = [f.strip() for f in args.factors.split(",") if f.strip()] or DEFAULT_FACTORS
    conn = psycopg2.connect(args.db_url)
    try:
        directions = get_factor_directions(conn, factors, args.universe)
        print(f"因子方向: { {f: ('负' if directions[f] < 0 else '正') for f in factors} }")

        industry_map = load_industry_map(conn)
        calendar = get_calendar(conn)
        min_d = date.fromisoformat(args.min_date) if args.min_date else None
        max_d = date.fromisoformat(args.max_date) if args.max_date else None
        if min_d:
            calendar = [d for d in calendar if d >= min_d]
        if max_d:
            calendar = [d for d in calendar if d <= max_d]

        # 回测分段：每个再平衡期 [T0, T0+rebalance]
        nav = 1.0
        navs: list[tuple[date, float]] = []
        rebalance_cnt = 0
        # hs300 等指数成分样本：加载成员集合
        member_symbols: set[str] | None = None
        if args.universe in INDEX_UNIVERSES:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT symbol FROM tdx.dim_index_member WHERE "index" = %s',
                    (args.universe,),
                )
                member_symbols = {r[0] for r in cur.fetchall()}
        i = 0
        n = len(calendar)
        while i + 1 < n:
            t0 = calendar[i]
            t_end_idx = min(i + args.rebalance, n - 1)
            t1 = calendar[t_end_idx]  # 出场日（T+rebalance 收盘）
            if t1 == t0:
                break
            # 入场日 = T0 次日开盘
            t_entry = calendar[i + 1]

            # 因子行（T0 收盘截面）
            lnmv_map = load_lnmv_map(conn, t0)
            rows = get_factor_rows(conn, t0, factors, exclude_st=True,
                                   universe=args.universe, member_symbols=member_symbols)
            if not rows:
                i = t_end_idx
                continue
            opens_entry = get_opens(conn, t_entry)
            closes_exit = get_closes(conn, t1)
            if not opens_entry or not closes_exit:
                i = t_end_idx
                continue

            # 逐因子中性化 → zscore → 方向 → 等权组合分
            per_stock: dict[str, list[float]] = {s: [] for s, _ in rows}
            ok_factor = 0
            for fi, fname in enumerate(factors):
                # 过滤该因子为 None 的股票（其余因子不受影响）；r 即因子值列表
                pairs = [(s, r[fi]) for s, r in rows if r[fi] is not None]
                if not pairs:
                    continue
                syms = [p[0] for p in pairs]
                vals = [p[1] for p in pairs]
                nz = neutralize_values(syms, vals, industry_map, lnmv_map)
                zs = zscore([v if v is not None else 0.0 for v in nz])
                sign = directions.get(fname, 1.0)
                for idx2, s in enumerate(syms):
                    per_stock[s].append(sign * zs[idx2])
                ok_factor += 1
            if ok_factor < args.min_factors:
                i = t_end_idx
                continue
            score = {s: (sum(v) / len(v)) for s, v in per_stock.items() if v}

            # 持仓：top K（pct 或 K）
            if args.top_k > 0:
                picks = sorted(score, key=lambda s: -score[s])[: args.top_k]
            else:
                k = max(1, int(round(len(score) * args.top_pct)))
                picks = sorted(score, key=lambda s: -score[s])[:k]
            if not picks:
                i = t_end_idx
                continue

            # T+1 开盘入场，T1 收盘出场，等权，扣单边成本
            rets = []
            for s in picks:
                o0 = opens_entry.get(s)
                c1 = closes_exit.get(s)
                if o0 and c1 and o0 > 0:
                    rets.append(c1 / o0 - 1.0)
            if not rets:
                i = t_end_idx
                continue
            port_ret = sum(rets) / len(rets) - args.cost
            nav *= (1 + port_ret)
            navs.append((t1, nav))
            rebalance_cnt += 1
            i = t_end_idx

        if not navs:
            print("无回测数据：请检查因子/日期/样本", file=sys.stderr)
            sys.exit(1)

        # 绩效统计
        prev = 1.0
        peak = 1.0
        max_dd = 0.0
        for _d, v in navs:
            ret = v / prev - 1.0
            prev = v
            peak = max(peak, v)
            dd = v / peak - 1.0
            max_dd = min(max_dd, dd)
        total = navs[-1][1] - 1.0
        days = (navs[-1][0] - navs[0][0]).days
        years = max(days / 365.0, 1e-9)
        rets_arr = [navs[j][1] / navs[j - 1][1] - 1.0 for j in range(1, len(navs))]
        mean_r = sum(rets_arr) / len(rets_arr) if rets_arr else 0.0
        var_r = sum((r - mean_r) ** 2 for r in rets_arr) / len(rets_arr) if rets_arr else 0.0
        sd_r = math.sqrt(var_r)
        annual = total / years
        sharpe = (mean_r / sd_r) * math.sqrt(252 / max(args.rebalance, 1)) if sd_r > 0 else 0.0
        calmar = annual / abs(max_dd) if max_dd != 0 else 0.0

        # 基准（沪深300，同区间累计）
        bench = get_benchmark_returns(conn, calendar)
        bench_total = None
        if bench:
            bench_total = 1.0
            for _bd, br in bench:
                bench_total *= (1 + br)
            bench_total -= 1.0

        print("\n===== 组合回测结果 =====")
        print(f"因子: {factors}")
        print(f"样本: {args.universe} | 每 {args.rebalance} 交易日再平衡 | "
              f"持仓: {args.top_k if args.top_k else f'前{args.top_pct:.0%}'} | 成本: {args.cost:.2%}")
        print(f"区间: {navs[0][0]} ~ {navs[-1][0]}（{len(navs)} 期，{days} 天）")
        print(f"累计收益: {total:+.2%}（年化 {annual:+.2%}）"
              + (f" | 沪深300同区间: {bench_total:+.2%}" if bench_total is not None else ""))
        print(f"年化波动: {sd_r * math.sqrt(252 / max(args.rebalance, 1)):.2%} | "
              f"Sharpe: {sharpe:.2f} | 最大回撤: {max_dd:.2%} | Calmar: {calmar:.2f}")
        print(f"策略换手: 每期全换（{rebalance_cnt} 期）")
        print("净值走势（含日期）:")
        step = max(1, len(navs) // 12)
        for d, v in navs[::step]:
            print(f"  {d}  NAV={v:.4f}")
        print(f"  最终 {navs[-1][0]} NAV={navs[-1][1]:.4f}")

        if args.out_csv:
            with open(args.out_csv, "w", encoding="utf-8") as fh:
                fh.write("date,nav\n")
                for d, v in navs:
                    fh.write(f"{d},{v:.6f}\n")
            print(f"净值已导出: {args.out_csv}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()