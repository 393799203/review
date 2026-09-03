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


def get_index_volume_data() -> Dict:
    """
    返回三指数成交量数据：
    {
      'items': [
        {'code','name','short','price','volume','amount',
         'yesterday_amount','predicted_amount','predicted_change_pct','progress','trading'},
        ...
      ],
      'trading': bool, 'date': 'YYYY-MM-DD'
    }
    """
    try:
        from mootdx.quotes import Quotes
    except Exception as e:
        return {'items': [], 'trading': False, 'error': str(e)}

    now = _cn_now()
    progress = _trading_progress(now)
    today = now.strftime('%Y-%m-%d')

    items: List[Dict] = []
    for idx in INDEXES:
        item = {
            'code': idx['code'],
            'name': idx['name'],
            'short': idx['short'],
            'price': None,
            'volume': None,           # 当日累计成交量(手)
            'amount': None,           # 当日累计成交额(元)
            'yesterday_amount': None, # 昨日全天成交额(元)
            'predicted_amount': None, # 预测全天成交额(元)
            'predicted_change_pct': None,  # 预测全天较昨日增减%
            'progress': progress,
            'trading': progress is not None and 0 < progress < 1,
        }
        try:
            client = Quotes.factory(market=idx['market'])

            # 1. 当日累计量
            q = client.quotes(symbol=[idx['code']])
            if q is not None and not q.empty:
                r = q.iloc[0]
                item['price'] = float(r.get('price') or 0)
                item['volume'] = float(r.get('vol') or 0)
                item['amount'] = float(r.get('amount') or 0)

            # 2. 昨日全天成交额（指数日线，取最近一个 < today 的交易日）
            daily = client.index(symbol=idx['code'])
            if daily is not None and not daily.empty:
                df = daily
                # 计算昨日：取 date < today 的最后一行
                past = df[df['datetime'].astype(str) < today]
                if not past.empty:
                    row = past.iloc[-1]
                    item['yesterday_amount'] = float(row.get('amount') or 0)

            # 3. 预测
            if progress is not None and progress > 0 and item['amount']:
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
        'trading': progress is not None and 0 < progress < 1,
        'date': today,
    }
