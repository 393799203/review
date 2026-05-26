#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple, List
from datetime import datetime, date
import requests
from app.services.base_service import BaseService
from app.repositories.misc_repository import MiscRepository


class MiscService(BaseService):
    """辅助接口服务类"""
    
    def __init__(self):
        super().__init__(MiscRepository())
        self.misc_repository = self.repository
    
    def get_ladder_comparison(self, date_str: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取连板晋级对比数据
        
        Args:
            date_str: 日期字符串
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            if trade_date > datetime.now().date():
                return False, '无法获取未来日期的数据', None
            
            prev_date = self.misc_repository.get_prev_trade_date(trade_date)
            
            if not prev_date:
                return False, '没有找到上一个交易日的数据', None
            
            today_stocks = self.misc_repository.get_stocks_by_date(trade_date)
            yesterday_stocks = self.misc_repository.get_stocks_by_date(prev_date)
            
            now = datetime.now()
            is_today = trade_date == now.date()
            
            trading_start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
            
            if not today_stocks:
                if is_today and now < trading_start_time:
                    today_list = []
                else:
                    return False, '该日期暂无涨停股票数据', None
            else:
                today_list = self._format_stock_list(today_stocks)
            
            yesterday_list = self._format_stock_list(yesterday_stocks, include_next_change=True)
            
            latest_trade_date = self.misc_repository.get_latest_trade_date()
            
            should_fetch_realtime = False
            if latest_trade_date and trade_date == latest_trade_date:
                from core.trade_calendar import trade_calendar
                should_fetch_realtime = trade_calendar.should_fetch_realtime_quotes(prev_date)
                
                if should_fetch_realtime:
                    from core.quotes_utils import get_realtime_quotes, update_stock_data_change_percent
                    
                    yesterday_codes = [stock.stock_code for stock in yesterday_stocks]
                    print(f"实时获取昨日涨停股票涨跌幅,股票数量: {len(yesterday_codes)}")
                    
                    quotes_dict = get_realtime_quotes(yesterday_codes, debug=True)
                    update_stock_data_change_percent(yesterday_list, quotes_dict)
            
            return True, '获取成功', {
                'today': {
                    'date': trade_date.strftime('%Y-%m-%d'),
                    'stocks': today_list
                },
                'yesterday': {
                    'date': prev_date.strftime('%Y-%m-%d'),
                    'stocks': yesterday_list
                }
            }
            
        except Exception as e:
            return False, str(e), None
    
    def get_premium_trend(self, continuous_days: int, date_str: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取溢价率趋势
        
        Args:
            continuous_days: 连板数
            date_str: 日期字符串
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if date_str:
                try:
                    end_date = datetime.strptime(date_str, '%Y%m%d').date()
                except ValueError:
                    return False, '日期格式错误,请使用YYYYMMDD格式', None
            else:
                end_date = self.misc_repository.get_latest_trade_date()
                if not end_date:
                    return False, '没有找到交易日数据', None
            
            recent_dates = self.misc_repository.get_recent_trade_dates(end_date, 10)
            
            if not recent_dates:
                return False, '没有找到交易日数据', None
            
            trend_data = []
            
            for trade_date in reversed(recent_dates):
                prev_date = self.misc_repository.get_prev_trade_date(trade_date)
                
                if prev_date:
                    stocks = self.misc_repository.get_stocks_by_date_and_continuous(
                        prev_date, continuous_days
                    )
                    
                    if stocks:
                        valid_stocks = [s for s in stocks if s.next_change is not None]
                        if valid_stocks:
                            avg_change = sum(float(s.next_change) for s in valid_stocks) / len(valid_stocks)
                        else:
                            avg_change = None
                    else:
                        avg_change = None
                    
                    trend_data.append({
                        'date': trade_date.strftime('%Y-%m-%d'),
                        'avg_change_percent': round(avg_change, 2) if avg_change is not None else None,
                        'stock_count': len(stocks) if stocks else 0
                    })
                else:
                    trend_data.append({
                        'date': trade_date.strftime('%Y-%m-%d'),
                        'avg_change_percent': None,
                        'stock_count': 0
                    })
            
            return True, '获取成功', {
                'continuous_days': continuous_days,
                'trend': trend_data
            }
            
        except Exception as e:
            return False, str(e), None
    
    def get_hot_stocks(self, list_type: str = 'normal') -> Tuple[bool, str, Optional[Dict]]:
        """
        获取同花顺热股数据
        
        Args:
            list_type: 榜单类型
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            valid_types = ['normal', 'value', 'trend']
            if list_type not in valid_types:
                return False, f'无效的榜单类型,可选值: {", ".join(valid_types)}', None
            
            if list_type == 'normal':
                url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=normal'
            elif list_type == 'value':
                url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=day&list_type=value'
            else:
                url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=day&list_type=trend'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://dq.10jqka.com.cn/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status_code') == 0:
                stock_list = data.get('data', {}).get('stock_list', [])
                
                processed_stocks = []
                for stock in stock_list:
                    processed_stocks.append({
                        'code': stock.get('code', ''),
                        'name': stock.get('name', ''),
                        'price': float(stock.get('price', 0)) if stock.get('price') else 0.0,
                        'change_percent': float(stock.get('rise_and_fall', 0)) if stock.get('rise_and_fall') else 0.0,
                        'volume_ratio': float(stock.get('volume_ratio', 0)) if stock.get('volume_ratio') else None,
                        'turnover_rate': float(stock.get('turnover_rate', 0)) if stock.get('turnover_rate') else None,
                        'market_value': stock.get('market_value', ''),
                        'industry': ', '.join(stock.get('tag', {}).get('concept_tag', [])) if stock.get('tag', {}).get('concept_tag') else '',
                        'reason': stock.get('analyse', ''),
                        'rank': stock.get('order', 0),
                        'hot_value': int(float(stock.get('rate', 0))) if stock.get('rate') else 0,
                        'heat_degree': stock.get('heat_degree', 0),
                        'popularity_tag': stock.get('tag', {}).get('popularity_tag', ''),
                        'analyse_title': stock.get('analyse_title', ''),
                    })
                
                return True, '获取成功', processed_stocks
            else:
                return False, '获取热股数据失败', None
                
        except Exception as e:
            return False, str(e), None
    
    def _format_stock_list(self, stocks: List, include_next_change: bool = False) -> List[Dict]:
        """格式化股票列表"""
        stock_list = []
        for stock in stocks:
            if include_next_change:
                stock_data = {
                    'code': stock.stock_code,
                    'name': stock.stock_name,
                    'continuous_days': stock.continuous_days,
                    'limit_up_time': stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else '',
                    'seal_amount': float(stock.seal_amount) if stock.seal_amount else 0.0,
                    'limit_up_price': float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                    'change_percent': float(stock.next_change) if stock.next_change else None
                }
            else:
                stock_data = {
                    'code': stock.stock_code,
                    'name': stock.stock_name,
                    'continuous_days': stock.continuous_days,
                    'limit_up_time': stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else '',
                    'seal_amount': float(stock.seal_amount) if stock.seal_amount else 0.0,
                    'limit_up_price': float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                    'change_percent': float(stock.change_percent) if stock.change_percent else 0.0,
                    'turnover_rate': float(stock.turnover_rate) if stock.turnover_rate else 0.0
                }
            
            stock_list.append(stock_data)
        
        return stock_list
