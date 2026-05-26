#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.stock_data_service import StockDataService


class StockDataController(BaseController):
    """股票数据控制器类"""
    
    def __init__(self):
        super().__init__(StockDataService())
        self.stock_data_service = self.service
    
    def get_kline_data(self, stock_code: str):
        """获取K线数据"""
        try:
            days = int(self.get_query_param('days', 60))
            
            success, message, data = self.stock_data_service.get_kline_data(stock_code, days)
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data
                })
            else:
                return self.error(message, 404)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_intraday_data(self, stock_code: str):
        """获取分时数据"""
        try:
            user_id = self.get_current_user_uid()
            
            success, message, data = self.stock_data_service.get_intraday_data(stock_code, user_id)
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data
                })
            else:
                return self.error(message, 404)
                
        except Exception as e:
            return self.error(str(e), 500)


stock_data_controller = StockDataController()
