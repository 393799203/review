#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点数据获取模块
用于获取涨停相关数据，如首次涨停日期等
"""

from app.core.data_fetcher import DataFetcher
from database import get_db_session
from models import LimitUpStock
from datetime import datetime
import logging


class HotspotFetcher:
    """热点数据获取器"""
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.logger = logging.getLogger(__name__)
    
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