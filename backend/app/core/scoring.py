#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则打分卡：为量化筛选结果计算 ml_score（0~100）

方案 A：不训练模型，按可解释的规则维度加权打分。
抄底放量与突破放量两个策略的信号语义不同，分别打分。

所有维度输出 0~1，加权求和后 ×100 取整。
None 特征按中性值处理，保证打分稳定。
"""

from typing import Dict, Optional


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _lin(v: float, x0: float, x1: float) -> float:
    """v 在 [x0, x1] 线性映射到 [0, 1]，超出截断"""
    if x1 == x0:
        return 1.0 if v >= x1 else 0.0
    return _clamp01((v - x0) / (x1 - x0))


def _tri(v: float, lo: float, mid: float, hi: float) -> float:
    """三角形：v <= lo 或 v >= hi 为 0，v = mid 为 1"""
    if v <= lo or v >= hi:
        return 0.0
    if v <= mid:
        return (v - lo) / (mid - lo)
    return (hi - v) / (hi - mid)


def _f(v, default: float = 0.0) -> float:
    """安全转 float，None/异常取默认值"""
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


class RuleScorer:
    """规则打分器"""

    # 维度权重（可调）
    BOTTOM_WEIGHTS = {
        'vol_strength': 0.25,   # 放量强度（首日实际放量倍数）
        'vol_sustain': 0.15,    # 量能持续性（第2/3天倍数 / 首日倍数）
        'cv': 0.15,             # 地量充分度（放量前 CV 越小越好）
        'day1_change': 0.15,    # 首日涨幅（适中加分，过热降分）
        'turnover': 0.10,       # 换手率（D 日）
        'industry': 0.10,       # 行业强度（申万一级当日涨跌）
        'mktcap': 0.10,         # 市值（中小市值加分）
    }

    BREAKOUT_WEIGHTS = {
        'breakout': 0.25,       # 突破强度（收盘 / 前高）
        'vol_ratio': 0.20,      # 放量倍数（当日 / 均量）
        'turnover': 0.15,       # 换手率（适中加分，过热降分）
        'upper_shadow': 0.10,   # 上影线（越短越好）
        'ma_dev': 0.10,         # 均线偏离（适中加分，追高降分）
        'change': 0.10,         # 当日涨幅（适中加分）
        'industry': 0.05,       # 行业强度
        'mktcap': 0.05,         # 市值
    }

    def score(self, features: Dict, strategy: str) -> Optional[int]:
        """计算综合分（0~100 整数），特征缺失过多时返回 None"""
        try:
            if strategy == 'bottom':
                parts = self._bottom_parts(features)
                weights = self.BOTTOM_WEIGHTS
            else:
                parts = self._breakout_parts(features)
                weights = self.BREAKOUT_WEIGHTS

            total = 0.0
            for key, w in weights.items():
                total += w * parts[key]
            return int(round(total * 100))
        except Exception:
            return None

    # ---------- 各维度打分 ----------

    @staticmethod
    def _mktcap_part(totalmv) -> float:
        """市值分：<=100 亿满分，100~500 亿线性降到 0。totalmv 单位元。"""
        mv_yi = _f(totalmv) / 100000000.0
        if mv_yi <= 0:
            return 0.4  # 无市值数据给中性分
        return 1.0 - _lin(mv_yi, 100, 500)

    @staticmethod
    def _industry_part(sw1_change_pct) -> float:
        """行业分：申万一级当日涨幅 0~3% 线性，无数据给中性分"""
        v = _f(sw1_change_pct, default=0.0)
        if sw1_change_pct is None:
            return 0.4
        return _lin(v, 0, 3)

    def _bottom_parts(self, f: Dict) -> Dict[str, float]:
        day1_ratio = _f(f.get('day1_vol_ratio'))
        day23_ratio = _f(f.get('day23_vol_ratio'))
        cv = _f(f.get('cv'))

        # 量能持续性：第2/3天倍数相对首日的维持度
        sustain = day23_ratio / day1_ratio if day1_ratio > 0 else 0.0
        sustain_part = _lin(min(sustain, 1.0), 0.5, 0.9)

        return {
            'vol_strength': _lin(day1_ratio, 2.5, 4.0),
            'vol_sustain': sustain_part,
            'cv': 1.0 - _lin(cv, 0.1, 0.5),          # CV 0.1 → 1，0.5 → 0
            'day1_change': _tri(_f(f.get('day1_change_pct')), 0, 5, 10),
            'turnover': _tri(_f(f.get('turnover')), 1, 8, 25),
            'industry': self._industry_part(f.get('sw1_change_pct')),
            'mktcap': self._mktcap_part(f.get('totalmv')),
        }

    def _breakout_parts(self, f: Dict) -> Dict[str, float]:
        ma_ratio = _f(f.get('ma_ratio'))
        # 均线偏离：1.0~1.05 升，1.05~1.30 降（追高降分）
        ma_dev_part = min(_lin(ma_ratio, 1.0, 1.05), 1.0 - _lin(ma_ratio, 1.05, 1.30))

        return {
            'breakout': _lin(_f(f.get('prev_high_ratio')), 1.0, 1.08),
            'vol_ratio': _lin(_f(f.get('vol_ratio')), 1.3, 3.0),
            'turnover': _tri(_f(f.get('turnover')), 5, 25, 50),
            'upper_shadow': 1.0 - _lin(_f(f.get('upper_shadow')), 0, 10),
            'ma_dev': ma_dev_part,
            'change': _tri(_f(f.get('change_pct')), 0, 5, 9.5),
            'industry': self._industry_part(f.get('sw1_change_pct')),
            'mktcap': self._mktcap_part(f.get('totalmv')),
        }


scorer = RuleScorer()
