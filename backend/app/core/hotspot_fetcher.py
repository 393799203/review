#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime, timedelta

HOTSPOT_URL = (
    "http://zx.10jqka.com.cn/event/api/getharden/"
    "date/{date}/orderby/date/orderway/desc/charset/GBK/"
)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "Chrome/117.0.0.0 Safari/537.36"
)


class HotspotFetcher:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})

    def get_hot_data(self, date_str: str) -> list:
        url = HOTSPOT_URL.format(date=date_str)
        try:
            r = self.session.get(url, timeout=15)
            data = r.json()
            if data.get("errocode", 0) != 0:
                print(f"  [热点] {date_str} 错误: {data.get('errormsg', '')}")
                return []
            return data.get("data") or []
        except Exception as e:
            print(f"  [热点] {date_str} 请求失败: {e}")
            return []

    def get_multi_day_hot_data(self, dates: list) -> dict:
        result = {}
        for d in dates:
            rows = self.get_hot_data(d)
            if rows:
                result[d] = rows
        return result

    def get_trading_days_before(self, base_date_str: str, count: int) -> list:
        try:
            base = datetime.strptime(base_date_str, "%Y%m%d")
        except ValueError:
            return []

        days = []
        cursor = base - timedelta(days=1)
        max_lookback = 10
        while len(days) < count and max_lookback > 0:
            ds = cursor.strftime("%Y%m%d")
            if cursor.weekday() < 5:
                days.append(ds)
            cursor = cursor - timedelta(days=1)
            max_lookback -= 1
        return days

    def _is_trading_day(self, date_str: str) -> bool:
        try:
            d = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            return False
        return d.weekday() < 5


hotspot_fetcher = HotspotFetcher()
