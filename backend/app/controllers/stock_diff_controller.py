#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.stock_diff_service import StockDiffService


class StockDiffController(BaseController):
    """股票对比控制器类"""
    
    def __init__(self):
        super().__init__(StockDiffService())
        self.stock_diff_service = self.service
    
    def save_stock_diff(self):
        """保存股票对比结果"""
        try:
            data = self.get_json_data()
            trade_date_str = data.get('trade_date')
            added_stocks = data.get('added', [])
            removed_stocks = data.get('removed', [])
            
            success, message, data = self.stock_diff_service.save_stock_diff(
                trade_date_str, added_stocks, removed_stocks
            )
            
            if success:
                return self.success(message=message, data=data)
            else:
                return self.error(message, 400 if '缺少' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def load_stock_diff(self, date_str: str):
        """加载股票对比结果"""
        try:
            success, message, data = self.stock_diff_service.load_stock_diff(date_str)
            
            if success:
                return self.success(data=data)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def clear_stock_diff(self, date_str: str):
        """清空指定日期的股票对比结果"""
        try:
            success, message, _ = self.stock_diff_service.clear_stock_diff(date_str)
            
            if success:
                return self.success(message=message)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)


stock_diff_controller = StockDiffController()
