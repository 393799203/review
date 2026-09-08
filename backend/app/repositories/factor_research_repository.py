#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子研究仓库：读取 tdx.factor_eval_summary / tdx.factor_eval_daily_ic
（由 tdx_daily/eval_factor_standalone.py --save 预计算落库，含 universe 样本 与 method 口径维度）

不继承 BaseRepository（无 ORM 模型，纯 SQL 只读查询，走 TDX 外部行情库）。
评估表尚未生成（eval --save 未跑过）时按空数据返回，避免 500。
"""

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.tdx_db import require_tdx_engine


def _table_missing(e: ProgrammingError) -> bool:
    return 'does not exist' in str(e)


class FactorResearchRepository:
    """因子研究仓库类"""

    def __init__(self):
        self.engine = require_tdx_engine()

    def get_meta(self) -> dict:
        """评估元信息：可用样本、各样本的持有期与口径、因子列表、最近评估时间"""
        try:
            with self.engine.connect() as conn:
                universes = [r[0] for r in conn.execute(
                    text("SELECT DISTINCT universe FROM tdx.factor_eval_summary ORDER BY universe")
                ).fetchall()]
                factors = [r[0] for r in conn.execute(
                    text("SELECT DISTINCT factor FROM tdx.factor_eval_summary ORDER BY factor")
                ).fetchall()]
                # universe -> {method -> [horizon...]}
                hm_rows = conn.execute(
                    text("""
                        SELECT DISTINCT universe, method, horizon
                        FROM tdx.factor_eval_summary ORDER BY universe, method, horizon
                    """)
                ).fetchall()
                latest_rows = conn.execute(
                    text("""
                        SELECT DISTINCT ON (universe, method, horizon) universe, method, horizon, max_date, computed_at
                        FROM tdx.factor_eval_summary
                        ORDER BY universe, method, horizon, computed_at DESC
                    """)
                ).fetchall()
        except ProgrammingError as e:
            if _table_missing(e):
                return {'universes': [], 'factors': [], 'horizons': {}, 'methods': {}, 'latest': []}
            raise
        horizons: dict[str, dict[str, list[int]]] = {}
        methods: dict[str, list[str]] = {}
        for u, m, h in hm_rows:
            horizons.setdefault(u, {}).setdefault(m, []).append(h)
            if m not in methods.setdefault(u, []):
                methods[u].append(m)
        latest = [
            {
                'universe': r[0],
                'method': r[1],
                'horizon': r[2],
                'max_date': r[3].isoformat() if r[3] is not None else None,
                'computed_at': r[4].isoformat() if r[4] is not None else None,
            }
            for r in latest_rows
        ]
        return {
            'universes': universes,
            'factors': factors,
            'horizons': horizons,   # {universe: {method: [horizon...]}}
            'methods': methods,     # {universe: [method...]}
            'latest': latest,
        }

    def get_summary(self, horizon: int, universe: str = 'all', method: str = 'neutral') -> list[dict]:
        """某持有期×样本×口径下全部因子的 IC/IR 汇总（按 |icir| 降序）；
        口径为 neutral 时顺带返回 raw_icir（供前端计算"风格贡献 ΔICIR"）"""
        sql = text("""
            SELECT factor, min_date, max_date, n_dates,
                   mean_ic, ic_std, icir, t_stat, ic_pos_pct,
                   q_means, mono, computed_at
            FROM tdx.factor_eval_summary
            WHERE horizon = :horizon AND universe = :universe AND method = :method
            ORDER BY abs(icir) DESC, factor
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(
                    sql, {'horizon': horizon, 'universe': universe, 'method': method}
                ).mappings().fetchall()
                raw_icir_map: dict[str, float] = {}
                if method == 'neutral':
                    raw_rows = conn.execute(
                        text("""
                            SELECT factor, icir FROM tdx.factor_eval_summary
                            WHERE horizon = :horizon AND universe = :universe AND method = 'raw'
                        """),
                        {'horizon': horizon, 'universe': universe},
                    ).mappings().fetchall()
                    raw_icir_map = {r['factor']: float(r['icir']) for r in raw_rows if r['icir'] is not None}
        except ProgrammingError as e:
            if _table_missing(e):
                return []
            raise
        out = []
        for r in rows:
            out.append({
                'factor': r['factor'],
                'min_date': r['min_date'].isoformat() if r['min_date'] is not None else None,
                'max_date': r['max_date'].isoformat() if r['max_date'] is not None else None,
                'n_dates': r['n_dates'],
                'mean_ic': float(r['mean_ic']) if r['mean_ic'] is not None else None,
                'ic_std': float(r['ic_std']) if r['ic_std'] is not None else None,
                'icir': float(r['icir']) if r['icir'] is not None else None,
                'raw_icir': raw_icir_map.get(r['factor']),
                't_stat': float(r['t_stat']) if r['t_stat'] is not None else None,
                'ic_pos_pct': float(r['ic_pos_pct']) if r['ic_pos_pct'] is not None else None,
                'q_means': r['q_means'],
                'mono': float(r['mono']) if r['mono'] is not None else None,
                'computed_at': r['computed_at'].isoformat() if r['computed_at'] is not None else None,
            })
        return out

    def get_daily_ic(self, factor: str, horizon: int, universe: str = 'all', method: str = 'neutral') -> list[dict]:
        """某因子×持有期×样本×口径的逐日 IC 时间序列"""
        sql = text("""
            SELECT date, ic
            FROM tdx.factor_eval_daily_ic
            WHERE factor = :factor AND horizon = :horizon
              AND universe = :universe AND method = :method
            ORDER BY date
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(
                    sql, {'factor': factor, 'horizon': horizon, 'universe': universe, 'method': method}
                ).mappings().fetchall()
        except ProgrammingError as e:
            if _table_missing(e):
                return []
            raise
        return [
            {
                'date': r['date'].isoformat(),
                'ic': float(r['ic']) if r['ic'] is not None else None,
            }
            for r in rows
        ]
