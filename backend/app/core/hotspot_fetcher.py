#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点数据获取模块
用于获取涨停相关数据，如首次涨停日期等
"""

from app.core.data_fetcher import DataFetcher
from database import get_db_session
from models import LimitUpStock
from datetime import datetime, timedelta
import logging
import requests

HOTSPOT_URL = (
    "http://zx.10jqka.com.cn/event/api/getharden/"
    "date/{date}/orderby/date/orderway/desc/charset/GBK/"
)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "Chrome/117.0.0.0 Safari/537.36"
)


class HotspotFetcher:
    """热点数据获取器"""

    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _UA})

    def get_hot_data(self, date_str: str) -> list:
        """抓取同花顺某日涨停热点数据（代码/名称/涨幅/题材标签等）"""
        url = HOTSPOT_URL.format(date=date_str)
        try:
            r = self.session.get(url, timeout=15)
            data = r.json()
            if data.get("errocode", 0) != 0:
                self.logger.warning(f"[热点] {date_str} 错误: {data.get('errormsg', '')}")
                return []
            return data.get("data") or []
        except Exception as e:
            self.logger.error(f"[热点] {date_str} 请求失败: {e}")
            return []

    def get_multi_day_hot_data(self, dates: list) -> dict:
        """抓取多个交易日的热点数据，返回 {date: rows}"""
        result = {}
        for d in dates:
            rows = self.get_hot_data(d)
            if rows:
                result[d] = rows
        return result

    def get_trading_days_before(self, base_date_str: str, count: int) -> list:
        """获取基准日期之前的 count 个交易日（跳过周末，YYYYMMDD）"""
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

    def get_first_limit_up_date(self, stock_code):
        """
        获取股票首次涨停日期
        
        Args:
            stock_code: 股票代码
            
        Returns:
            dict: {
                'first_date': '首次涨停日期（YYYY-MM-DD）',
                'limit_up_count': 涨停次数,
                'message': '附加信息'
            }
        """
        try:
            # 清理股票代码（去掉交易所后缀）
            stock_code_clean = stock_code.split('.')[0]
            
            session = get_db_session()
            
            # 查询该股票的所有涨停记录，按日期排序
            records = session.query(LimitUpStock).filter_by(
                stock_code=stock_code_clean
            ).order_by(LimitUpStock.date.asc()).all()
            
            if not records:
                session.close()
                return {
                    'first_date': None,
                    'limit_up_count': 0,
                    'message': '该股票没有涨停记录'
                }
            
            first_date = records[0].date
            limit_up_count = len(records)
            
            session.close()
            
            return {
                'first_date': first_date.strftime('%Y-%m-%d') if isinstance(first_date, datetime) else str(first_date),
                'limit_up_count': limit_up_count,
                'message': f'首次涨停于{first_date}, 共涨停{limit_up_count}次'
            }
            
        except Exception as e:
            self.logger.error(f"获取首次涨停日期失败: {e}")
            return {
                'first_date': None,
                'limit_up_count': 0,
                'message': str(e)
            }
    
    def get_stock_continuous_days(self, stock_code, date_str):
        """
        获取股票在指定日期的连板天数
        
        Args:
            stock_code: 股票代码
            date_str: 日期字符串
            
        Returns:
            int: 连板天数
        """
        try:
            stock_code_clean = stock_code.split('.')[0]
            
            session = get_db_session()
            
            record = session.query(LimitUpStock).filter_by(
                stock_code=stock_code_clean,
                date=date_str
            ).first()
            
            session.close()
            
            if record:
                return record.continuous_days or 1
            else:
                return 0
                
        except Exception as e:
            self.logger.error(f"获取连板天数失败: {e}")
            return 0
    
    def get_block_stocks(self, block_name, date_str):
        """
        获取指定板块在指定日期的涨停股票列表
        
        Args:
            block_name: 板块名称
            date_str: 日期字符串
            
        Returns:
            list: 股票列表
        """
        try:
            session = get_db_session()
            
            stocks = session.query(LimitUpStock).filter_by(
                date=date_str,
                block=block_name
            ).all()
            
            result = []
            for stock in stocks:
                result.append({
                    'stock_code': stock.stock_code,
                    'stock_name': stock.stock_name,
                    'continuous_days': stock.continuous_days,
                    'limit_up_time': stock.limit_up_time,
                    'block': stock.block
                })
            
            session.close()
            return result
            
        except Exception as e:
            self.logger.error(f"获取板块股票失败: {e}")
            return []