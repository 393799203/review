#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子研究服务：提供因子 IC/IR 评估结果（来自 tdx_daily eval --save 落库）。
支持样本（universe）维度：all=全部符号 / ashare=沪深A股 / main=沪深主板 / gem=创业+科创。
"""

from typing import Dict, Optional, Tuple

from app.core.tdx_db import TdxNotConfiguredError
from app.repositories.factor_research_repository import FactorResearchRepository

VALID_HORIZONS = (1, 5, 10, 20)
VALID_UNIVERSES = ('all', 'ashare', 'main', 'gem', 'hs300')
VALID_METHODS = ('raw', 'neutral')

# 样本中文名（前端展示）
UNIVERSE_LABELS = {
    'all': '全市场（含指数/北交所/基金等）',
    'ashare': '沪深A股（主板+创业+科创）',
    'main': '沪深主板',
    'gem': '创业板+科创板',
    'hs300': '沪深300成分（当前成分口径）',
}

# 因子说明目录（47 个因子）：factor -> (类别, 说明)
# 与 tdx_daily/calc_indicator_standalone.py 的 COLUMNS 保持一致
FACTOR_DESCRIPTIONS = {
    # ---- 趋势 ----
    'ma5': ('趋势', '5日均线（最近5日收盘均值，含当日），反映短期趋势方向'),
    'ma10': ('趋势', '10日均线，短期趋势与短线支撑/压力'),
    'ma20': ('趋势', '20日均线，中期趋势与常用支撑/压力位'),
    'ma60': ('趋势', '60日均线，中长期趋势分水岭'),
    'ema12': ('趋势', '指数移动平均(12)，对近期价格加权更大，反应更灵敏'),
    'ema26': ('趋势', '指数移动平均(26)，较慢的加权均线'),
    'dif': ('趋势', 'MACD 快线 = EMA12 − EMA26，反映短期动能方向与强弱'),
    'dea': ('趋势', 'MACD 慢线 = DIF 的 9 日 EMA，即信号线'),
    'macd_hist': ('趋势', 'MACD 柱 = (DIF − DEA) × 2，红柱为多头、绿柱为空头'),
    'ma_bull': ('趋势', '均线多头排列标志：ma5>ma10>ma20>ma60 时为 1，否则 0'),
    'mom5': ('趋势', '5 日动量 = 今收/5日前收盘 − 1，短期涨速'),
    'mom20': ('趋势', '20 日动量，一个月涨跌幅'),
    'mom60': ('趋势', '60 日动量，季度涨跌幅'),
    # ---- 摆动 ----
    'rsi6': ('摆动', 'RSI(6)（Wilder），0~100，>70 超买、<30 超卖，短线情绪'),
    'rsi12': ('摆动', 'RSI(12)，>70 超买、<30 超卖，中短线情绪'),
    'rsi24': ('摆动', 'RSI(24)，>70 超买、<30 超卖，中期情绪'),
    'kdj_k': ('摆动', 'KDJ 之 K 值（9,3,3），随机指标快线'),
    'kdj_d': ('摆动', 'KDJ 之 D 值，K 的 3 日平滑（慢线）'),
    'kdj_j': ('摆动', 'KDJ 之 J 值 = 3K − 2D，>100 超买、<0 超卖，摆动最强'),
    'cci14': ('摆动', 'CCI(14) 顺势指标，>100 超买、<−100 超卖'),
    'wr14': ('摆动', '威廉指标(14)，0~100，>80 超卖、<20 超买（与 RSI 反向）'),
    'bias6': ('摆动', '乖离率(6) = (收盘−MA6)/MA6×100，偏离短期均线程度'),
    'bias12': ('摆动', '乖离率(12)，偏离中期均线程度，过大有回归压力'),
    'bias24': ('摆动', '乖离率(24)，偏离长期均线程度'),
    # ---- 波动 ----
    'atr14': ('波动', 'ATR(14) 平均真实波幅（Wilder），衡量单日波动幅度'),
    'boll_mid': ('波动', '布林带中轨 = 20日均线'),
    'boll_up': ('波动', '布林带上轨 = 中轨 + 2×20日标准差，压力参考'),
    'boll_low': ('波动', '布林带下轨 = 中轨 − 2×20日标准差，支撑参考'),
    'boll_pctb': ('波动', '布林带 %b = (收盘−下轨)/(上轨−下轨)，0~1 表示价格在带内位置'),
    'std20': ('波动', '20 日收益率标准差，衡量波动率（越低越平稳）'),
    # ---- 量价关系 ----
    'vr5': ('量价', '量比(5) = 当日量/近5日均量（含当日），>1 放量'),
    'vr10': ('量价', '量比(10)，中期量能放大程度'),
    'vr20': ('量价', '量比(20)，>1 放量、<1 缩量，判断量能水平'),
    'vol_trend': ('量价', '量能趋势 = 5日均量/20日均量，>1 量能扩张、<1 萎缩'),
    'vol_cv20': ('量价', '20日量能变异系数 = 量标准差/量均值，越低量能越平稳（地量特征）'),
    'vol_low_ratio20': ('量价', '地量指标 = 当日量/20日最大量，越低越接近地量'),
    'pos20': ('量价', '价格 20 日区间位置 = (收盘−20日最低)/(20日最高−最低)，0~1'),
    'vol_pos20': ('量价', '量能 20 日区间位置，0~1'),
    'div20': ('量价', '量价背离 = pos20 − vol_pos20；>0 价强量弱（上攻动能不足），<0 价弱量强（底部吸筹/背离）'),
    'corr_pv20': ('量价', '量价相关性 = 20日价格收益率与量变化率的 Pearson 相关，高=量价同步、低=背离'),
    'obv': ('量价', 'OBV 能量潮，按涨跌方向累积成交量，衡量资金净流入趋势'),
    'obv_slope5': ('量价', 'OBV 斜率 = (OBV_MA5 − OBV_MA10)/(1+|OBV_MA10|)，>0 资金持续流入'),
    'vpt': ('量价', 'VPT 量价趋势 = 累积(涨跌幅×成交量)，量价配合度'),
    'mfi14': ('量价', 'MFI(14) 资金流量指标，0~100，>80 超买、<20 超卖'),
    'cmf20': ('量价', 'CMF(20) 蔡金资金流 = 20日Σ(资金流量乘数×量)/Σ量，>0 资金流入、<0 流出'),
    'new_high20': ('量价', '收盘价创前 20 个交易日（不含当日）新高记为 1，否则 0'),
    'new_low20': ('量价', '收盘价创前 20 个交易日（不含当日）新低记为 1，否则 0'),
    # ---- 基本面（calc_fundamental_standalone.py，point-in-time 最新快照） ----
    'pe': ('基本面', '市盈率 = 总市值/净利润（静态，基于最近财报快照）；负值或异常大需注意'),
    'pb': ('基本面', '市净率 = 收盘价/每股净资产'),
    'ps': ('基本面', '市销率 = 总市值/主营收入'),
    'pcf': ('基本面', '市现率 = 总市值/经营现金流'),
    'roe': ('基本面', '净资产收益率 = 净利润/净资产，衡量股东回报'),
    'roa': ('基本面', '总资产收益率 = 净利润/总资产'),
    'net_margin': ('基本面', '净利率 = 净利润/主营收入'),
    'op_margin': ('基本面', '主营利润率 = 主营利润/主营收入'),
    'debt_ratio': ('基本面', '资产负债率 = 1 − 净资产/总资产，越高杠杆越大'),
    'cf_quality': ('基本面', '盈利含金量 = 经营现金流/净利润，<1 说明利润缺乏现金支撑'),
    'ar_ratio': ('基本面', '应收账款/主营收入，越高回款质量越差'),
    'inv_ratio': ('基本面', '存货/总资产，越高占用资金越多'),
}


class FactorResearchService:
    """因子研究服务类"""

    def _create_repository(self) -> FactorResearchRepository:
        return FactorResearchRepository()

    @staticmethod
    def _normalize_universe(universe) -> Tuple[bool, str, str]:
        u = str(universe or 'all').strip() or 'all'
        if u not in VALID_UNIVERSES:
            return False, f'universe 可选值：{" / ".join(VALID_UNIVERSES)}', ''
        return True, '', u

    @staticmethod
    def _normalize_method(method) -> Tuple[bool, str, str]:
        m = str(method or 'neutral').strip() or 'neutral'
        if m not in VALID_METHODS:
            return False, f'method 可选值：{" / ".join(VALID_METHODS)}', ''
        return True, '', m

    def get_meta(self) -> Tuple[bool, str, Optional[Dict]]:
        """评估元信息（样本、口径、持有期、因子列表、最近评估时间）"""
        try:
            repository = self._create_repository()
        except TdxNotConfiguredError as e:
            raise e
        try:
            meta = repository.get_meta()
            meta['universe_labels'] = UNIVERSE_LABELS
            return True, '获取成功', meta
        except Exception as e:
            return False, str(e), None

    def get_summary(self, horizon: Optional[int], universe: Optional[str],
                    method: Optional[str]) -> Tuple[bool, str, Optional[Dict]]:
        """某持有期×样本×口径的因子 IC/IR 汇总表"""
        try:
            horizon = int(horizon) if horizon is not None else 5
        except (TypeError, ValueError):
            return False, f'horizon 必须为整数，可选 {VALID_HORIZONS}', None
        if horizon not in VALID_HORIZONS:
            return False, f'horizon 可选值：{VALID_HORIZONS}', None
        ok, msg, u = self._normalize_universe(universe)
        if not ok:
            return False, msg, None
        ok, msg, m = self._normalize_method(method)
        if not ok:
            return False, msg, None
        try:
            repository = self._create_repository()
        except TdxNotConfiguredError as e:
            raise e
        try:
            rows = repository.get_summary(horizon, u, m)
            # 合并因子类别与说明
            for r in rows:
                category, desc = FACTOR_DESCRIPTIONS.get(r['factor'], ('', ''))
                r['category'] = category
                r['desc'] = desc
            return True, '获取成功', {'horizon': horizon, 'universe': u, 'method': m, 'factors': rows}
        except Exception as e:
            return False, str(e), None

    def get_ic_series(self, factor: Optional[str], horizon: Optional[int],
                      universe: Optional[str], method: Optional[str]) -> Tuple[bool, str, Optional[Dict]]:
        """某因子×持有期×样本×口径的逐日 IC 时间序列"""
        if not factor or not str(factor).strip():
            return False, '缺少因子名 factor', None
        factor = str(factor).strip()
        try:
            horizon = int(horizon) if horizon is not None else 5
        except (TypeError, ValueError):
            return False, f'horizon 必须为整数，可选 {VALID_HORIZONS}', None
        ok, msg, u = self._normalize_universe(universe)
        if not ok:
            return False, msg, None
        ok, msg, m = self._normalize_method(method)
        if not ok:
            return False, msg, None
        try:
            repository = self._create_repository()
        except TdxNotConfiguredError as e:
            raise e
        try:
            series = repository.get_daily_ic(factor, horizon, u, m)
            if not series:
                return False, f'未找到因子 {factor} (H={horizon}, 样本={u}, 口径={m}) 的评估数据', None
            return True, '获取成功', {'factor': factor, 'horizon': horizon, 'universe': u, 'method': m, 'series': series}
        except Exception as e:
            return False, str(e), None
