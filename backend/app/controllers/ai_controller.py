#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.ai_service import AIService


class AIController(BaseController):
    """AI分析控制器类"""
    
    def __init__(self):
        super().__init__(AIService())
        self.ai_service = self.service
    
    def analyze_limit_up_stock(self, stock_code: str):
        """分析涨停股票"""
        try:
            force = self.get_query_param('force', 'false').lower() == 'true'
            date_str = self.get_query_param('date')
            check_only = self.get_query_param('check_only', 'false').lower() == 'true'
            
            success, message, data = self.ai_service.analyze_limit_up_stock(
                stock_code, force, date_str, check_only
            )
            
            if success:
                if check_only:
                    return self.success(**data)
                else:
                    cached = data.pop('cached', False)
                    return self.success(data=data, cached=cached)
            else:
                return self.error(message, 404 if '未找到' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def analyze_news(self):
        """分析新闻"""
        try:
            data = self.get_json_data()
            news_id = data.get('news_id')
            title = data.get('title', '')
            content = data.get('content', '')
            force = data.get('force', False)
            
            success, message, data = self.ai_service.analyze_news(
                news_id, title, content, force
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 400 if '缺少' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def analyze_watchlist_stock(self):
        """分析自选股"""
        try:
            data = self.get_json_data()
            stock_code = data.get('stock_code', '')
            stock_name = data.get('stock_name', '')
            force = data.get('force', False)
            check_only = data.get('check_only', False)
            
            if not stock_code:
                return self.error('缺少股票代码', 400)
            
            success, message, data = self.ai_service.analyze_watchlist_stock(
                stock_code, stock_name, force, check_only
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def analyze_report(self):
        """分析研报"""
        try:
            data = self.get_json_data()
            info_code = data.get('info_code')
            title = data.get('title', '')
            stock_name = data.get('stock_name', '')
            stock_code = data.get('stock_code', '')
            rating = data.get('rating', '')
            rating_change = data.get('rating_change', '')
            force = data.get('force', False)
            
            predict_eps = {
                'this_year': data.get('predict_this_year_eps', ''),
                'next_year': data.get('predict_next_year_eps', ''),
                'next_two_year': data.get('predict_next_two_year_eps', '')
            }
            
            predict_pe = {
                'this_year': data.get('predict_this_year_pe', ''),
                'next_year': data.get('predict_next_year_pe', ''),
                'next_two_year': data.get('predict_next_two_year_pe', '')
            }
            
            success, message, data = self.ai_service.analyze_report(
                info_code, title, stock_name, stock_code,
                rating, rating_change, predict_eps, predict_pe, force
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 400 if '缺少' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)

    def analyze_hot_topic(self):
        """分析热门话题"""
        try:
            data = self.get_json_data()
            topic_title = data.get('topic_title', '')
            themes = data.get('themes', [])
            investment_direction = data.get('investment_direction', '')
            force = data.get('force', False)
            
            if not topic_title:
                return self.error('缺少话题标题', 400)
            
            success, message, data = self.ai_service.analyze_hot_topic(
                topic_title, themes, investment_direction, force
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)

    def comfort_stock(self):
        """AI安慰分析持仓股票"""
        try:
            data = self.get_json_data()
            stock_code = data.get('stock_code', '')
            stock_name = data.get('stock_name', '')
            buy_price = float(data.get('buy_price', 0))
            current_price = float(data.get('current_price', 0))
            position_profit = float(data.get('position_profit', 0))
            position_profit_ratio = float(data.get('position_profit_ratio', 0))
            
            success, message, data = self.ai_service.comfort_stock(
                stock_code, stock_name, buy_price, current_price,
                position_profit, position_profit_ratio
            )
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data
                })
            else:
                return self.error(message, 400 if '缺少' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)


ai_controller = AIController()
