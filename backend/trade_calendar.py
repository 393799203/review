#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易日历工具（使用 chinese_calendar 库）
"""

from datetime import datetime, timedelta
from typing import List
from chinese_calendar import is_workday, is_holiday


class TradeCalendar:
    """交易日历工具类"""
    
    def is_trading_day(self, date: datetime) -> bool:
        """
        判断是否为交易日
        
        Args:
            date: 日期对象
            
        Returns:
            是否为交易日
        """
        # 如果是法定节假日，不是交易日
        if is_holiday(date):
            return False
        
        # 如果是周末
        if date.weekday() >= 5:  # 5=周六, 6=周日
            # 检查是否为调休工作日
            if is_workday(date):
                # 调休工作日（周末上班），股市不开市
                return False
            else:
                # 正常周末，不是交易日
                return False
        
        # 正常工作日，是交易日
        return True
    
    def get_trading_days(self, start_date: datetime, end_date: datetime) -> List[str]:
        """
        获取日期范围内的所有交易日
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易日列表（格式：YYYYMMDD）
        """
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_trading_day(current_date):
                trading_days.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)
        
        return trading_days
    
    def get_recent_trading_days(self, count: int = 5, end_date: datetime = None) -> List[str]:
        """
        获取最近N个交易日
        
        Args:
            count: 数量
            end_date: 结束日期，默认为当前日期
            
        Returns:
            交易日列表（格式：YYYYMMDD）
        """
        trading_days = []
        current_date = end_date if end_date else datetime.now()
        
        while len(trading_days) < count:
            if self.is_trading_day(current_date):
                trading_days.append(current_date.strftime('%Y%m%d'))
            current_date -= timedelta(days=1)
        
        return trading_days
    
    def get_adjacent_trading_days(self, date_str: str, prev_count: int = 31, next_count: int = 18) -> dict:
        """
        获取指定日期前后的交易日
        
        Args:
            date_str: 日期字符串（格式：YYYYMMDD）
            prev_count: 前面天数
            next_count: 后面天数
            
        Returns:
            包含prev_dates和next_dates的字典
        """
        date = datetime.strptime(date_str, '%Y%m%d')
        
        # 获取前面的交易日
        prev_dates = []
        current_date = date - timedelta(days=1)
        while len(prev_dates) < prev_count:
            if self.is_trading_day(current_date):
                prev_dates.insert(0, current_date.strftime('%Y%m%d'))
            current_date -= timedelta(days=1)
        
        # 获取后面的交易日
        next_dates = []
        current_date = date + timedelta(days=1)
        while len(next_dates) < next_count:
            if self.is_trading_day(current_date):
                next_dates.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)
        
        return {
            'prev_dates': prev_dates,
            'next_dates': next_dates,
            'is_trading_day': self.is_trading_day(date)
        }


# 创建全局实例
trade_calendar = TradeCalendar()
