#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深创三大指数成交量查询与全天预测

数据来源：mootdx（通达信）
- 上证指数 999999（沪）
- 深证成指 399001、创业板指 399006（深）

逻辑：
1. quotes 取指数当日累计成交量/成交额
2. 指数日线(index)取上一交易日全天成交额作为基准
3. 交易时段按时间进度折算预测全天成交额：当前累计额 / 已交易进度
   时段：9:30-11:30(120min) + 13:00-15:00(120min)，共 240min
4. 预测增减% = (预测全天 - 昨日全天) / 昨日全天 * 100
"""

import os
from datetime import datetime, time as dtime
from typing import Dict, List, Optional

try:
    from zoneinfo import ZoneInfo
    CN_TZ = ZoneInfo('Asia/Shanghai')
except Exception:  # 旧环境无 zoneinfo 时退化为固定 UTC+8
    from datetime import timedelta, timezone
    CN_TZ = timezone(timedelta(hours=8))


def _cn_now() -> datetime:
    """北京时间（A股时段判定必须用中国时区）"""
    return datetime.now(CN_TZ)

INDEXES = [
    {'code': '999999', 'market': 1, 'name': '上证指数', 'short': '上证'},
    {'code': '399001', 'market': 0, 'name': '深证成指', 'short': '深成指'},
    {'code': '399006', 'market': 0, 'name': '创业板指', 'short': '创业板'},
]

OPEN_MORNING = dtime(9, 30)
CLOSE_MORNING = dtime(11, 30)
OPEN_AFTERNOON = dtime(13, 0)
CLOSE_AFTERNOON = dtime(15, 0)
TOTAL_MINUTES = 240  # 120 + 120


def _trading_progress(now: datetime) -> Optional[float]:
    """
    返回交易进度(0~1)：
    - 盘中：已交易分钟数/240
    - 午休：0.5（上午已完成）
    - 盘后(>15:00)：1.0（当日已完结，直接用当日实际 vs 昨日）
    - 盘前(<9:30)：None（当日无数据）
    """
    t = now.time()
    if OPEN_MORNING <= t <= CLOSE_MORNING:
        minutes = (t.hour - 9) * 60 + t.minute - 30
        return minutes / TOTAL_MINUTES
    if CLOSE_MORNING < t < OPEN_AFTERNOON:
        return 120 / TOTAL_MINUTES  # 午休：上午已完成
    if OPEN_AFTERNOON <= t <= CLOSE_AFTERNOON:
        minutes = 120 + (t.hour - 13) * 60 + t.minute
        return minutes / TOTAL_MINUTES
    if t > CLOSE_AFTERNOON:
        return 1.0  # 盘后：当日已收盘
    return None  # 盘前


def _traded_minutes(now: datetime) -> int:
    """今日已交易分钟数（9:30 起）"""
    t = now.time()
    if t < OPEN_MORNING:
        return 0
    if t <= CLOSE_MORNING:
        return (t.hour - 9) * 60 + t.minute - 30
    if t <= OPEN_AFTERNOON:
        return 120
    return min(120 + (t.hour - 13) * 60 + t.minute, 240)


def _yesterday_same_time_ratio(client, code: str, today: str) -> Optional[float]:
    """
    昨日同时刻成交量占比 = 昨日截至当前分钟累计 vol / 昨日全天 vol。
    用于替代线性时间进度折算——成交量的日内分布并非均匀（通常前重后轻），
    直接用昨日同时刻的成交进度更准确。
    返回 None 表示拿不到昨日分时（非交易日/数据缺失），由调用方回退线性进度。
    """
    from datetime import timedelta
    try:
        # 往回找最近一个交易日（最多 8 天）
        for back in range(1, 9):
            d = _cn_now() - timedelta(days=back)
            date_str = d.strftime('%Y%m%d')
            if date_str >= today.replace('-', ''):
                continue
            mins = client.minutes(symbol=code, date=date_str)
            if mins is None or (hasattr(mins, 'empty') and mins.empty):
                continue
            vol = mins['vol'].astype(float)
            total = float(vol.sum())
            if total <= 0:
                continue
            tm = _traded_minutes(_cn_now())
            if tm <= 0:
                return None
            same = float(vol.head(tm).sum())
            return same / total
    except Exception as e:
        print(f"昨日同时刻比例获取失败 {code}: {e}")
    return None


def get_index_volume_data(date_str: str = None) -> Dict:
    """
    返回三指数成交量数据：
    - date_str 为空或为今天：盘中实时累计 + 预测全天
    - date_str 为历史交易日：返回该日实际成交额 + 前一交易日对比（不预测）
    {
      'items': [
        {'code','name','short','price','volume','amount',
         'yesterday_amount','predicted_amount','predicted_change_pct','progress','trading'},
        ...
      ],
      'trading': bool, 'date': 'YYYY-MM-DD', 'is_history': bool
    }
    """
    try:
        from mootdx.quotes import Quotes
    except Exception as e:
        return {'items': [], 'trading': False, 'error': str(e)}

    now = _cn_now()
    progress = _trading_progress(now)
    today = now.strftime('%Y-%m-%d')

    # 传入的历史日期：YYYYMMDD 或 YYYY-MM-DD 归一化
    is_history = False
    target_date = today
    if date_str:
        ds = str(date_str).replace('-', '')
        if len(ds) == 8:
            target_date = f"{ds[0:4]}-{ds[4:6]}-{ds[6:8]}"
            if target_date != today:
                is_history = True
                progress = 1.0  # 历史日视为已收盘

    items: List[Dict] = []
    for idx in INDEXES:
        item = {
            'code': idx['code'],
            'name': idx['name'],
            'short': idx['short'],
            'price': None,
            'volume': None,           # 当日累计成交量(手)
            'amount': None,           # 当日累计成交额(元)
            'yesterday_amount': None, # 前一交易日全天成交额(元)
            'predicted_amount': None, # 预测全天成交额(元)，历史日=当日实际
            'predicted_change_pct': None,  # 较前一交易日增减%
            'progress': progress,
            'trading': not is_history and progress is not None and 0 < progress < 1,
            'is_history': is_history,
        }
        try:
            client = Quotes.factory(market=idx['market'])
            daily = client.index(symbol=idx['code'])

            if is_history:
                # 历史日：从日线取 target_date 当天与前一交易日
                if daily is not None and not daily.empty:
                    df = daily
                    day_rows = df[df['datetime'].astype(str) >= target_date]
                    if not day_rows.empty:
                        row = day_rows.iloc[0]
                        item['price'] = float(row.get('close') or 0)
                        item['volume'] = float(row.get('vol') or 0)
                        item['amount'] = float(row.get('amount') or 0)
                    prev = df[df['datetime'].astype(str) < target_date]
                    if not prev.empty:
                        item['yesterday_amount'] = float(prev.iloc[-1].get('amount') or 0)
                    item['predicted_amount'] = item['amount']  # 历史已定
            else:
                # 1. 当日累计量
                q = client.quotes(symbol=[idx['code']])
                if q is not None and not q.empty:
                    r = q.iloc[0]
                    item['price'] = float(r.get('price') or 0)
                    item['volume'] = float(r.get('vol') or 0)
                    item['amount'] = float(r.get('amount') or 0)

                # 2. 前一交易日全天成交额（指数日线，取最近一个 < today 的交易日）
                if daily is not None and not daily.empty:
                    df = daily
                    past = df[df['datetime'].astype(str) < today]
                    if not past.empty:
                        row = past.iloc[-1]
                        item['yesterday_amount'] = float(row.get('amount') or 0)

                # 3. 预测全天：优先用"昨日同时刻成交量占比"折算（更贴近日内分布），
                #    拿不到昨日分时则回退线性时间进度
                if item['amount']:
                    same_ratio = _yesterday_same_time_ratio(client, idx['code'], today)
                    if same_ratio and same_ratio > 0:
                        item['predicted_amount'] = item['amount'] / same_ratio
                    elif progress and progress > 0:
                        item['predicted_amount'] = item['amount'] / progress

            if (item['predicted_amount'] and item['yesterday_amount']
                    and item['yesterday_amount'] > 0):
                item['predicted_change_pct'] = (
                    (item['predicted_amount'] - item['yesterday_amount'])
                    / item['yesterday_amount'] * 100
                )
        except Exception as e:
            item['error'] = str(e)[:120]

        items.append(item)

    return {
        'items': items,
        'trading': not is_history and progress is not None and 0 < progress < 1,
        'date': target_date,
        'is_history': is_history,
    }
