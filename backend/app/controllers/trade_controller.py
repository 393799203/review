#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.trade_service import TradeService


class TradeController(BaseController):
    """交易记录控制器类"""
    
    def __init__(self):
        super().__init__(TradeService())
        self.trade_service = self.service
    
    def buy_stock(self):
        """买入股票"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        data = self.get_json_data()
        stock_code = data.get('stock_code')
        buy_price = data.get('buy_price')
        quantity = data.get('buy_quantity', 100)
        
        if not stock_code or not buy_price:
            return self.error('缺少必要参数', 400)
        
        success, message = self.trade_service.buy_stock(
            user_id, stock_code, buy_price, quantity
        )
        
        if success:
            return self.success(message=message)
        else:
            if '不在自选列表中' in message:
                return self.error(message, 404)
            else:
                return self.error(message, 500)
    
    def sell_stock(self):
        """卖出股票"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        data = self.get_json_data()
        stock_code = data.get('stock_code')
        sell_price = data.get('sell_price')
        quantity = data.get('sell_quantity')
        
        if not stock_code or not sell_price:
            return self.error('缺少必要参数', 400)
        
        success, message = self.trade_service.sell_stock(
            user_id, stock_code, sell_price, quantity
        )
        
        if success:
            return self.success(message=message)
        else:
            if '不在自选列表中' in message:
                return self.error(message, 404)
            elif '未持仓' in message or '超过持仓数量' in message:
                return self.error(message, 400)
            else:
                return self.error(message, 500)
    
    def get_trade_records(self):
        """获取交易记录"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        success, message, data = self.trade_service.get_trade_records(user_id)
        
        if success:
            return self.success(data)
        else:
            return self.error(message, 500)


trade_controller = TradeController()
