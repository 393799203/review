#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化筛选服务

筛选公式（全部基于 TDX 行情库，schema=tdx）：

设当日为 D，对应 raw_stocks_daily(daily) 与 raw_stocks_basic(basic)
按 (symbol, date) 关联后的开高低收量额为 open/high/low/close/volume，
昨收 preclose，换手率 turnover（百分比数值），涨跌幅 change_pct（百分比数值）。

策略一：抄底放量（strategy='bottom'，默认）——只按成交量筛选，不加价格条件
取 D 向前连续 3 个交易日（含 D，不足 3 日或 D 当日该股无交易则排除）：
1. 第 1 天（3 天中最早的那天）volume >= 该日前 vol_window 个交易日
   （不含当日）AVG(volume) * day1_mult（默认 vol_window=20，day1_mult=2.5）
2. 第 2、3 天 volume >= 各自前 vol_window 个交易日（不含当日）均量
   * day23_mult（默认 2.0）
3. 每只股票在 D 之前必须有完整的 vol_window 个交易日均量，不足则排除
4. 放量前须持续地量：第 1 天之前 vol_window 个交易日成交量的变异系数
   CV = STDDEV_POP(volume) / AVG(volume) <= cv_max（默认 0.5）
5. 首个放量日（第 1 天）涨幅达标：change_pct > day1_change_min
   （默认 3%，不限制必须阳线，可为负数）

两个策略均只保留 00/30/60/68 开头的股票（沪深主板/创业板/科创板），
且排除 ST/*ST 股票（按 dim_sw_industry.name 判断）。

策略二：突破放量（strategy='breakout'）
1. 换手率：当日 turnover >= turnover_min（默认 15%）
2. 上影线：(high - GREATEST(open, close)) / preclose * 100 <= upper_shadow_max
   （默认 10%，即上影线不超过昨收的 10%）
3. 前高：prev_high = 前 prev_high_days 个交易日（不含当日）的 MAX(high)，
   要求当日 close >= prev_high * prev_high_coef（默认 60 日、系数 0.9，
   即收盘价接近或站上 60 日前高）
4. 放量：当日 volume >= (1 + vol_pct / 100) * 前 vol_window 个交易日
   （不含当日）的 AVG(volume)（默认放量 30%，参考 10 日均量）
5. 不过度追高：当日 close <= close_ratio * 前 close_window 个交易日
   （不含当日）的 AVG(close)（默认收盘价不超过 20 日均价的 1.3 倍）

历史数据扫描范围：date 前推窗口天数 * 2 + 余量个自然日作为下界
（交易日->自然日按 2 倍放宽），窗口函数在该范围内计算。

结果按 change_pct 倒序。行业信息来自 dim_sw_industry（is_latest=1），
行业当日涨跌幅来自 v_sw_industry_daily。ml_score 预留，当前一律为 null。
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.core.tdx_db import TdxNotConfiguredError
from app.core.scoring import scorer
from app.repositories.screening_repository import ScreeningRepository

DEFAULT_PARAMS = {
    'turnover_min': 15,
    'upper_shadow_max': 10,
    'prev_high_days': 60,
    'prev_high_coef': 0.9,
    'vol_window': 10,
    'vol_pct': 30,
    'close_window': 20,
    'close_ratio': 1.3,
}

BOTTOM_DEFAULT_PARAMS = {
    'vol_window': 20,
    'day1_mult': 2.5,
    'day23_mult': 2.0,
    'cv_max': 0.5,
    'day1_change_min': 3.0,
}

STRATEGIES = ('bottom', 'breakout')


class ScreeningService:
    """量化筛选服务类"""

    def _create_repository(self) -> ScreeningRepository:
        """创建仓库（TDX 未配置时抛出 TdxNotConfiguredError）"""
        return ScreeningRepository()

    def get_available_dates(self, limit: int = 60) -> Tuple[bool, str, Optional[List[str]]]:
        """获取最近 N 个有数据的交易日"""
        try:
            repository = self._create_repository()
        except TdxNotConfiguredError as e:
            raise e
        try:
            dates = repository.get_available_dates(limit)
            return True, '获取成功', dates
        except Exception as e:
            return False, str(e), None

    def run_screening(self, payload: Dict) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        执行量化筛选

        Args:
            payload: 请求 JSON，strategy 指定策略（'bottom' 默认 / 'breakout'），
                其余字段均可选，缺省用对应策略的默认参数

        Returns:
            tuple: (success, message, data)
        """
        payload = payload or {}

        date_str = payload.get('date')
        if not date_str:
            return False, '缺少交易日期参数 date', None
        date_str = str(date_str).replace('-', '')
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            return False, '日期格式错误，应为 YYYY-MM-DD 或 YYYYMMDD', None

        strategy = str(payload.get('strategy', 'bottom'))
        if strategy not in STRATEGIES:
            return False, f"未知策略 strategy={strategy}，可选：{', '.join(STRATEGIES)}", None

        repository = self._create_repository()
        try:
            if strategy == 'bottom':
                data = repository.run_bottom_screening(
                    self._normalize_bottom_params(payload, trade_date)
                )
            else:
                data = repository.run_screening(
                    self._normalize_breakout_params(payload, trade_date)
                )
            # 规则打分卡：为每条结果计算 ml_score（0~100）
            for row in (data or []):
                row['ml_score'] = scorer.score(row, strategy)
            return True, '筛选成功', data
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            return False, str(e), None

    def _normalize_breakout_params(self, payload: Dict, trade_date) -> Dict:
        """归一化"突破放量"策略参数"""
        try:
            params = {
                'date': trade_date,
                'turnover_min': float(payload.get('turnover_min', DEFAULT_PARAMS['turnover_min'])),
                'upper_shadow_max': float(payload.get('upper_shadow_max', DEFAULT_PARAMS['upper_shadow_max'])),
                'prev_high_days': int(payload.get('prev_high_days', DEFAULT_PARAMS['prev_high_days'])),
                'prev_high_coef': float(payload.get('prev_high_coef', DEFAULT_PARAMS['prev_high_coef'])),
                'vol_window': int(payload.get('vol_window', DEFAULT_PARAMS['vol_window'])),
                'vol_pct': float(payload.get('vol_pct', DEFAULT_PARAMS['vol_pct'])),
                'close_window': int(payload.get('close_window', DEFAULT_PARAMS['close_window'])),
                'close_ratio': float(payload.get('close_ratio', DEFAULT_PARAMS['close_ratio'])),
            }
        except (TypeError, ValueError):
            raise ValueError('参数类型错误，窗口天数必须为整数，其余为数值')

        if params['prev_high_days'] < 1 or params['vol_window'] < 1 or params['close_window'] < 1:
            raise ValueError('窗口天数必须为正整数')
        if params['prev_high_coef'] <=  0 or params['close_ratio'] <= 0:
            raise ValueError('前高系数与收盘价比例必须为正数')
        return params

    def _normalize_bottom_params(self, payload: Dict, trade_date) -> Dict:
        """归一化"抄底放量"策略参数"""
        try:
            params = {
                'date': trade_date,
                'vol_window': int(payload.get('vol_window', BOTTOM_DEFAULT_PARAMS['vol_window'])),
                'day1_mult': float(payload.get('day1_mult', BOTTOM_DEFAULT_PARAMS['day1_mult'])),
                'day23_mult': float(payload.get('day23_mult', BOTTOM_DEFAULT_PARAMS['day23_mult'])),
                'cv_max': float(payload.get('cv_max', BOTTOM_DEFAULT_PARAMS['cv_max'])),
                'day1_change_min': float(payload.get('day1_change_min', BOTTOM_DEFAULT_PARAMS['day1_change_min'])),
            }
        except (TypeError, ValueError):
            raise ValueError('参数类型错误，vol_window 必须为整数，倍数为数值')

        if params['vol_window'] < 1:
            raise ValueError('vol_window 必须为正整数')
        if params['day1_mult'] <= 0 or params['day23_mult'] <= 0:
            raise ValueError('放量倍数必须为正数')
        if params['cv_max'] <= 0:
            raise ValueError('cv_max 必须为正数')
        return params
