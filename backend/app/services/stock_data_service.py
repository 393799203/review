#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple
from app.services.base_service import BaseService
from app.repositories.stock_data_repository import StockDataRepository


class StockDataService(BaseService):
    """股票数据服务类"""
    
    def __init__(self):
        super().__init__(StockDataRepository())
        self.stock_data_repository = self.repository
    
    def get_kline_data(self, stock_code: str, days: int = 60) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取K线数据
        
        Args:
            stock_code: 股票代码
            days: 天数
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            kline_data = self.stock_data_repository.get_kline_data(stock_code, days)
            
            if kline_data:
                return True, '获取成功', kline_data
            else:
                return False, '未找到K线数据', None
                
        except Exception as e:
            return False, str(e), None
    
    def get_intraday_data(self, stock_code: str, user_id: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取分时数据
        
        Args:
            stock_code: 股票代码
            user_id: 用户ID
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            intraday_data = self.stock_data_repository.get_intraday_data(stock_code)
            quote_data = self.stock_data_repository.get_quote_data(stock_code)
            
            is_in_watchlist = False
            if user_id:
                is_in_watchlist = self.stock_data_repository.is_in_watchlist(user_id, stock_code)
            
            if intraday_data:
                result = {
                    **intraday_data,
                    'quote': quote_data,
                    'is_in_watchlist': is_in_watchlist
                }
            else:
                result = {
                    'quote': quote_data,
                    'is_in_watchlist': is_in_watchlist
                }
            
            return True, '获取成功', result
            
        except Exception as e:
            return False, str(e), None
