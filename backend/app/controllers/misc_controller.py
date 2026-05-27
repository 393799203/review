#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.misc_service import MiscService


class MiscController(BaseController):
    """辅助接口控制器类"""
    
    def __init__(self):
        super().__init__(MiscService())
        self.misc_service = self.service
    
    def get_ladder_comparison(self, date_str: str):
        """获取连板晋级对比数据"""
        try:
            success, message, data = self.misc_service.get_ladder_comparison(date_str)
            
            if success:
                from flask import jsonify
                data['success'] = True
                return jsonify(data)
            else:
                return self.success(success=False, error=message)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_premium_trend(self, continuous_days: int):
        """获取溢价率趋势"""
        try:
            date_str = self.get_query_param('date')
            
            success, message, data = self.misc_service.get_premium_trend(continuous_days, date_str)
            
            if success:
                return self.success(data=data)
            else:
                return self.error(message, 400 if '格式' in message else 200)
                
        except Exception as e:
            return self.error(str(e), 500)

    def get_auction_premium_trend(self, continuous_days: int):
        """获取竞价溢价趋势"""
        try:
            date_str = self.get_query_param('date')

            success, message, data = self.misc_service.get_auction_premium_trend(continuous_days, date_str)

            if success:
                return self.success(data=data)
            else:
                return self.error(message, 400 if '格式' in message else 200)

        except Exception as e:
            return self.error(str(e), 500)
    
    def get_hot_stocks(self):
        """获取同花顺热股数据"""
        try:
            list_type = self.get_query_param('list_type', 'normal')

            success, message, data = self.misc_service.get_hot_stocks(list_type)

            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data,
                    'list_type': list_type,
                    'count': len(data)
                })
            else:
                return self.error(message, 400 if '无效' in message else 500)

        except Exception as e:
            return self.error(str(e), 500)

    def get_market_alerts(self):
        """获取市场动态消息"""
        try:
            success, message, data = self.misc_service.get_market_alerts()

            if success:
                return self.success(data=data or [])
            else:
                return self.error(message, 500)

        except Exception as e:
            return self.error(str(e), 500)

    def save_market_alerts(self):
        """保存市场动态消息"""
        try:
            alerts_data = self.get_json_data()
            if not alerts_data:
                return self.error('没有数据', 400)

            trade_date = self.get_query_param('trade_date')

            success, message, data = self.misc_service.save_market_alerts(alerts_data, trade_date)

            if success:
                return self.success(message=message, data=data)
            else:
                return self.error(message, 500)

        except Exception as e:
            return self.error(str(e), 500)

    def get_market_alerts_history(self):
        """获取历史市场动态消息"""
        try:
            trade_date = self.get_query_param('trade_date')
            limit = int(self.get_query_param('limit', 100))

            success, message, data = self.misc_service.get_market_alerts_history(trade_date, limit)

            if success:
                return self.success(data=data or [])
            else:
                return self.error(message, 500)

        except Exception as e:
            return self.error(str(e), 500)

    def get_hot_topics(self):
        """获取热门话题数据"""
        try:
            days = int(self.get_query_param('days', 3))

            success, message, data = self.misc_service.get_hot_topics(days)

            if success:
                return self.success(data=data)
            else:
                return self.error(message, 500)

        except Exception as e:
            return self.error(str(e), 500)


misc_controller = MiscController()
