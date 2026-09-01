#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from flask import request
from app.controllers.base_controller import BaseController
from app.services.watchlist_service import WatchlistService


class WatchlistController(BaseController):
    """自选股控制器类"""
    
    def __init__(self, data_fetcher=None):
        super().__init__(WatchlistService())
        self.watchlist_service = self.service
        self.data_fetcher = data_fetcher
    
    def get_watchlist(self):
        """获取自选股列表"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        success, message, data = self.watchlist_service.get_watchlist_with_quotes(user_id)
        
        if success:
            return self.success(data)
        else:
            return self.error(message, 500)
    
    def add_to_watchlist(self):
        """添加股票到自选"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        data = self.get_json_data()
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        add_date_str = data.get('add_date')
        add_price = data.get('add_price')
        add_reason = data.get('add_reason', '')
        source = data.get('source', 'wencai')
        add_type = data.get('add_type', 'manual')
        limit_up_reason_category = data.get('limit_up_reason_category', '')
        alert_price = data.get('alert_price')
        signal_date_str = data.get('signal_date')
        
        if not stock_code or not stock_name or not add_date_str:
            return self.error('缺少必要参数', 400)
        
        try:
            add_date = datetime.strptime(add_date_str, '%Y%m%d').date()
        except:
            return self.error('日期格式错误', 400)
        
        signal_date = None
        if signal_date_str:
            try:
                signal_date = datetime.strptime(str(signal_date_str).replace('-', ''), '%Y%m%d').date()
            except:
                signal_date = None
        
        success, message = self.watchlist_service.add_to_watchlist(
            user_id, stock_code, stock_name, add_date, add_price,
            add_reason, source, add_type, limit_up_reason_category, alert_price, signal_date
        )
        
        if success:
            return self.success(message=message)
        else:
            return self.error(message, 400)
    
    def remove_from_watchlist(self, stock_code: str):
        """从自选中删除股票"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        success, message = self.watchlist_service.remove_from_watchlist(user_id, stock_code)
        
        if success:
            return self.success(message=message)
        else:
            if '持仓' in message:
                return self.error(message, 400)
            else:
                return self.error(message, 404)

    def remove_many(self):
        """批量删除自选股"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        data = self.get_json_data()
        stock_codes = data.get('stock_codes', [])
        if not isinstance(stock_codes, list):
            return self.error('参数格式错误：stock_codes 应为数组', 400)
        stock_codes = [str(c).strip() for c in stock_codes if str(c).strip()]
        
        success, message, deleted, skipped = self.watchlist_service.remove_many(
            user_id, stock_codes
        )
        
        if success:
            return self.success({
                'deleted': deleted,
                'skipped': skipped,
            }, message=message)
        else:
            return self.error(message, 400)

    def update_alert_price(self):
        """更新自选股预警价格"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未提供用户ID', 401)
        
        data = self.get_json_data()
        stock_code = data.get('stock_code')
        alert_price = data.get('alert_price')
        
        if not stock_code:
            return self.error('缺少股票代码', 400)
        
        success, message = self.watchlist_service.update_alert_price(
            user_id, str(stock_code), alert_price
        )
        
        if success:
            return self.success(message=message)
        else:
            return self.error(message, 400)
    
    def update_prices(self):
        """更新自选股价格(已废弃)"""
        return self.success(message='价格已在获取列表时实时更新，无需手动刷新')
    
    def search_stock(self):
        """搜索股票"""
        keyword = self.get_query_param('keyword', '').strip()
        
        success, message, data = self.watchlist_service.search_stock(keyword)
        
        if success:
            return self.success(data)
        else:
            return self.error(message, 500)
    
    def get_stock_quote(self, stock_code: str):
        """获取单只股票的实时行情"""
        if not self.data_fetcher:
            return self.error('数据抓取器未初始化', 500)
        
        success, message, data = self.watchlist_service.get_stock_quote(
            stock_code, self.data_fetcher
        )
        
        if success:
            return self.success(data)
        else:
            return self.error(message, 404)


watchlist_controller = None

def init_watchlist_controller(data_fetcher):
    """初始化自选股控制器"""
    global watchlist_controller
    watchlist_controller = WatchlistController(data_fetcher)
    return watchlist_controller
