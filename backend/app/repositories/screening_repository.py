#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化筛选仓库：直接查询 TDX 外部行情库（PostgreSQL，schema=tdx）

不继承 BaseRepository（无 ORM 模型，纯 SQL 只读查询）。
窗口函数的 frame 天数无法绑定参数，必须先校验为 int 后再内联进 SQL，
其余参数一律使用绑定参数。
"""

from datetime import date as date_type, timedelta
from typing import Dict, List

from sqlalchemy import text

from app.core.tdx_db import require_tdx_engine


class ScreeningRepository:
    """量化筛选仓库类"""

    def __init__(self):
        self.engine = require_tdx_engine()

    def get_available_dates(self, limit: int = 60) -> List[str]:
        """
        获取最近 N 个有数据的交易日（raw_stocks_basic 去重日期倒序）

        Args:
            limit: 返回的最大日期数

        Returns:
            list: ['YYYY-MM-DD', ...] 倒序
        """
        limit = max(1, min(int(limit), 250))
        sql = text(f"""
            SELECT DISTINCT date
            FROM tdx.raw_stocks_basic
            ORDER BY date DESC
            LIMIT {limit}
        """)
        with self.engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [row[0].isoformat() for row in rows]

    def run_screening(self, params: Dict) -> List[Dict]:
        """
        执行量化筛选（单条 SQL，窗口函数实现）

        Args:
            params: 已由 service 层校验/归一化的参数：
                date (date), turnover_min, upper_shadow_max,
                prev_high_days (int), vol_window (int), vol_pct,
                close_window (int), close_ratio

        Returns:
            list: 筛选结果字典列表，按 change_pct 倒序
        """
        trade_date = params['date']
        # 窗口 frame 天数：强制 int 校验后内联（无法绑定）
        prev_high_days = int(params['prev_high_days'])
        vol_window = int(params['vol_window'])
        close_window = int(params['close_window'])

        # 历史数据下界：最长窗口按 2 倍交易日->自然日放宽，再加 30 天余量
        max_window = max(prev_high_days, vol_window, close_window)
        start_date = trade_date - timedelta(days=max_window * 2 + 30)

        sql = text(f"""
            WITH hist AS (
                SELECT
                    d.symbol,
                    d.date,
                    d.open,
                    d.high,
                    d.low,
                    d.close,
                    d.volume,
                    b.preclose,
                    b.turnover,
                    b.change_pct,
                    b.totalmv,
                    b.amplitude,
                    MAX(d.high) OVER (
                        PARTITION BY d.symbol ORDER BY d.date
                        ROWS BETWEEN {prev_high_days} PRECEDING AND 1 PRECEDING
                    ) AS prev_high,
                    AVG(d.volume) OVER (
                        PARTITION BY d.symbol ORDER BY d.date
                        ROWS BETWEEN {vol_window} PRECEDING AND 1 PRECEDING
                    ) AS avg_vol,
                    AVG(d.close) OVER (
                        PARTITION BY d.symbol ORDER BY d.date
                        ROWS BETWEEN {close_window} PRECEDING AND 1 PRECEDING
                    ) AS ma_close
                FROM tdx.raw_stocks_daily d
                JOIN tdx.raw_stocks_basic b
                    ON b.symbol = d.symbol AND b.date = d.date
                WHERE d.date BETWEEN :start_date AND :trade_date
                  -- 只保留沪深主板/创业板/科创板（00/30/60/68 开头）
                  AND (d.symbol LIKE 'sh60%' OR d.symbol LIKE 'sh68%'
                       OR d.symbol LIKE 'sz00%' OR d.symbol LIKE 'sz30%')
            ),
            -- 行业涨跌只对目标日聚合一次（直接查基表；v_sw_industry_daily 是
            -- GROUPING SETS 视图，相关子查询下推不了谓词，会反复全量聚合）
            ind AS (
                SELECT i.sw1_code, i.sw2_code, AVG(b.change_pct) AS avg_pct
                FROM tdx.raw_stocks_basic b
                JOIN tdx.dim_sw_industry i
                    ON i.symbol = b.symbol AND i.is_latest = 1
                WHERE b.date = :trade_date
                GROUP BY GROUPING SETS ((i.sw1_code), (i.sw1_code, i.sw2_code))
            )
            SELECT
                COALESCE(i.code, SUBSTRING(h.symbol FROM 3)) AS code,
                h.symbol,
                i.name AS name,
                h.date AS date,
                h.close AS close,
                h.low AS low,
                h.turnover AS turnover,
                h.change_pct AS change_pct,
                -- 打分特征
                h.volume / NULLIF(h.avg_vol, 0) AS vol_ratio,
                h.close / NULLIF(h.prev_high, 0) AS prev_high_ratio,
                h.close / NULLIF(h.ma_close, 0) AS ma_ratio,
                (h.high - GREATEST(h.open, h.close)) / NULLIF(h.preclose, 0) * 100 AS upper_shadow,
                h.totalmv AS totalmv,
                h.amplitude AS amplitude,
                i.sw1_name AS sw1_name,
                i1.avg_pct AS sw1_change_pct,
                i.sw2_name AS sw2_name,
                i2.avg_pct AS sw2_change_pct
            FROM hist h
            LEFT JOIN tdx.dim_sw_industry i
                ON i.symbol = h.symbol AND i.is_latest = 1
            LEFT JOIN ind i1
                ON i1.sw1_code = i.sw1_code AND i1.sw2_code IS NULL
            LEFT JOIN ind i2
                ON i2.sw1_code = i.sw1_code AND i2.sw2_code = i.sw2_code
            WHERE h.date = :trade_date
              AND (i.name IS NULL OR i.name NOT LIKE '%ST%')
              AND h.turnover >= :turnover_min
              AND (h.high - GREATEST(h.open, h.close)) / NULLIF(h.preclose, 0) * 100
                  <= :upper_shadow_max
              AND h.prev_high IS NOT NULL
              AND h.close >= h.prev_high * :prev_high_coef
              AND h.avg_vol IS NOT NULL AND h.avg_vol > 0
              AND h.volume >= (1 + :vol_pct / 100.0) * h.avg_vol
              AND h.volume <= (1 + :vol_pct_max / 100.0) * h.avg_vol
              AND h.ma_close IS NOT NULL AND h.ma_close > 0
              AND h.close <= :close_ratio * h.ma_close
            ORDER BY h.change_pct DESC
        """)

        with self.engine.connect() as conn:
            rows = conn.execute(sql, {
                'trade_date': trade_date,
                'start_date': start_date,
                'turnover_min': params['turnover_min'],
                'upper_shadow_max': params['upper_shadow_max'],
                'prev_high_coef': params['prev_high_coef'],
                'vol_pct': params['vol_pct'],
                'vol_pct_max': params['vol_pct_max'],
                'close_ratio': params['close_ratio'],
            }).mappings().fetchall()

        return self._rows_to_result(rows)

    def run_bottom_screening(self, params: Dict) -> List[Dict]:
        """
        执行"抄底放量"筛选（单条 SQL，窗口函数实现）

        连续 3 个交易日（含 D）逐天校验放量倍数：
        rn=3（最早一天）用 day1_mult，rn=1/2 用 day23_mult。

        Args:
            params: 已由 service 层校验/归一化的参数：
                date (date), vol_window (int), day1_mult, day23_mult

        Returns:
            list: 筛选结果字典列表（date 取 D 当日数据），按 change_pct 倒序
        """
        trade_date = params['date']
        # 窗口 frame 天数：强制 int 校验后内联（无法绑定）
        vol_window = int(params['vol_window'])

        # 历史数据下界：vol_window 个交易日前高 + 3 天观察期，按 2 倍交易日->自然日放宽再加 40 天余量
        start_date = trade_date - timedelta(days=vol_window * 2 + 40)

        sql = text(f"""
            WITH hist AS (
                SELECT
                    d.symbol,
                    d.date,
                    d.open,
                    d.low,
                    d.close,
                    d.volume,
                    b.turnover,
                    b.change_pct,
                    b.totalmv,
                    b.amplitude,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.symbol ORDER BY d.date DESC
                    ) AS rn,
                    AVG(d.volume) OVER (
                        PARTITION BY d.symbol ORDER BY d.date
                        ROWS BETWEEN {vol_window} PRECEDING AND 1 PRECEDING
                    ) AS avg_vol,
                    COUNT(*) OVER (
                        PARTITION BY d.symbol ORDER BY d.date
                        ROWS BETWEEN {vol_window} PRECEDING AND 1 PRECEDING
                    ) AS vol_cnt,
                    STDDEV_POP(d.volume) OVER (
                        PARTITION BY d.symbol ORDER BY d.date
                        ROWS BETWEEN {vol_window} PRECEDING AND 1 PRECEDING
                    ) AS vol_std
                FROM tdx.raw_stocks_daily d
                JOIN tdx.raw_stocks_basic b
                    ON b.symbol = d.symbol AND b.date = d.date
                WHERE d.date BETWEEN :start_date AND :trade_date
                  -- 只保留沪深主板/创业板/科创板（00/30/60/68 开头）
                  AND (d.symbol LIKE 'sh60%' OR d.symbol LIKE 'sh68%'
                       OR d.symbol LIKE 'sz00%' OR d.symbol LIKE 'sz30%')
            ),
            picked AS (
                SELECT
                    symbol,
                    MAX(CASE WHEN rn = 1 THEN date END) AS date,
                    MAX(CASE WHEN rn = 3 THEN date END) AS signal_date,
                    MAX(CASE WHEN rn = 1 THEN close END) AS close,
                    MAX(CASE WHEN rn = 1 THEN low END) AS low,
                    MAX(CASE WHEN rn = 3 THEN low END) AS signal_low,
                    MAX(CASE WHEN rn = 1 THEN turnover END) AS turnover,
                    MAX(CASE WHEN rn = 1 THEN change_pct END) AS change_pct,
                    -- 打分特征
                    MAX(CASE WHEN rn = 3 THEN volume / NULLIF(avg_vol, 0) END) AS day1_vol_ratio,
                    MAX(CASE WHEN rn = 1 THEN volume / NULLIF(avg_vol, 0) END) AS day23_vol_ratio,
                    MAX(CASE WHEN rn = 3 AND avg_vol > 0 THEN vol_std / avg_vol END) AS cv,
                    MAX(CASE WHEN rn = 3 THEN change_pct END) AS day1_change_pct,
                    MAX(CASE WHEN rn = 1 THEN totalmv END) AS totalmv,
                    MAX(CASE WHEN rn = 1 THEN amplitude END) AS amplitude
                FROM hist
                WHERE rn <= 3
                GROUP BY symbol
                HAVING COUNT(*) = 3
                   -- rn=1 必须恰好是目标交易日（该股在 D 有交易）
                   AND MAX(CASE WHEN rn = 1 THEN date END) = :trade_date
                   -- D 之前必须有完整的 vol_window 个交易日均量，不足则排除
                   AND MAX(CASE WHEN rn = 1 THEN vol_cnt END) >= :vol_window
                   -- 放量前 vol_window 日须持续地量：CV(标准差/均值)不超过 cv_max
                   AND MAX(CASE WHEN rn = 3 AND avg_vol > 0 THEN vol_std / avg_vol END) <= :cv_max
                   -- 首个放量日（rn=3）涨幅达标：change_pct > day1_change_min（不限制必须阳线，可为负）
                   AND MAX(CASE WHEN rn = 3 AND change_pct > :day1_change_min THEN 1 ELSE 0 END) = 1
                   -- 逐天校验放量倍数：rn=3 用 day1_mult，rn=1/2 用 day23_mult
                   AND BOOL_AND(CASE WHEN rn = 3
                                     THEN volume >= avg_vol * :day1_mult
                                     ELSE volume >= avg_vol * :day23_mult
                                END)
            ),
            -- 行业涨跌只对目标日聚合一次（直接查基表；v_sw_industry_daily 是
            -- GROUPING SETS 视图，相关子查询下推不了谓词，会反复全量聚合）
            ind AS (
                SELECT i.sw1_code, i.sw2_code, AVG(b.change_pct) AS avg_pct
                FROM tdx.raw_stocks_basic b
                JOIN tdx.dim_sw_industry i
                    ON i.symbol = b.symbol AND i.is_latest = 1
                WHERE b.date = :trade_date
                GROUP BY GROUPING SETS ((i.sw1_code), (i.sw1_code, i.sw2_code))
            )
            SELECT
                COALESCE(i.code, SUBSTRING(p.symbol FROM 3)) AS code,
                p.symbol,
                i.name AS name,
                p.date AS date,
                p.signal_date AS signal_date,
                p.close AS close,
                p.low AS low,
                p.signal_low AS signal_low,
                p.turnover AS turnover,
                p.change_pct AS change_pct,
                p.day1_vol_ratio AS day1_vol_ratio,
                p.day23_vol_ratio AS day23_vol_ratio,
                p.cv AS cv,
                p.day1_change_pct AS day1_change_pct,
                p.totalmv AS totalmv,
                p.amplitude AS amplitude,
                i.sw1_name AS sw1_name,
                i1.avg_pct AS sw1_change_pct,
                i.sw2_name AS sw2_name,
                i2.avg_pct AS sw2_change_pct
            FROM picked p
            LEFT JOIN tdx.dim_sw_industry i
                ON i.symbol = p.symbol AND i.is_latest = 1
            LEFT JOIN ind i1
                ON i1.sw1_code = i.sw1_code AND i1.sw2_code IS NULL
            LEFT JOIN ind i2
                ON i2.sw1_code = i.sw1_code AND i2.sw2_code = i.sw2_code
            WHERE (i.name IS NULL OR i.name NOT LIKE '%ST%')
            ORDER BY p.change_pct DESC
        """)

        with self.engine.connect() as conn:
            rows = conn.execute(sql, {
                'trade_date': trade_date,
                'start_date': start_date,
                'vol_window': vol_window,
                'day1_mult': params['day1_mult'],
                'day23_mult': params['day23_mult'],
                'cv_max': params['cv_max'],
                'day1_change_min': params['day1_change_min'],
            }).mappings().fetchall()

        return self._rows_to_result(rows)

    def _rows_to_result(self, rows) -> List[Dict]:
        """将查询行转换为统一的结果字典列表（ml_score 预留为 null）"""
        result = []
        for row in rows:
            result.append({
                'code': row['code'],
                'symbol': row['symbol'],
                'name': row['name'],
                'date': row['date'].isoformat() if isinstance(row['date'], date_type) else str(row['date']),
                'signal_date': (
                    row['signal_date'].isoformat() if isinstance(row.get('signal_date'), date_type)
                    else (str(row['signal_date']) if row.get('signal_date') else None)
                ),
                'close': float(row['close']) if row['close'] is not None else None,
                'low': float(row['low']) if row.get('low') is not None else None,
                'signal_low': (
                    float(row['signal_low']) if row.get('signal_low') is not None else None
                ),
                'turnover': float(row['turnover']) if row['turnover'] is not None else None,
                'change_pct': float(row['change_pct']) if row['change_pct'] is not None else None,
                # 打分特征（ml_score 由 service 层计算）
                'day1_vol_ratio': float(row['day1_vol_ratio']) if row.get('day1_vol_ratio') is not None else None,
                'day23_vol_ratio': float(row['day23_vol_ratio']) if row.get('day23_vol_ratio') is not None else None,
                'cv': float(row['cv']) if row.get('cv') is not None else None,
                'day1_change_pct': float(row['day1_change_pct']) if row.get('day1_change_pct') is not None else None,
                'vol_ratio': float(row['vol_ratio']) if row.get('vol_ratio') is not None else None,
                'prev_high_ratio': float(row['prev_high_ratio']) if row.get('prev_high_ratio') is not None else None,
                'ma_ratio': float(row['ma_ratio']) if row.get('ma_ratio') is not None else None,
                'upper_shadow': float(row['upper_shadow']) if row.get('upper_shadow') is not None else None,
                'totalmv': float(row['totalmv']) if row.get('totalmv') is not None else None,
                'amplitude': float(row['amplitude']) if row.get('amplitude') is not None else None,
                'sw1_name': row['sw1_name'],
                'sw1_change_pct': float(row['sw1_change_pct']) if row['sw1_change_pct'] is not None else None,
                'sw2_name': row['sw2_name'],
                'sw2_change_pct': float(row['sw2_change_pct']) if row['sw2_change_pct'] is not None else None,
                'ml_score': None,
            })
        return result
