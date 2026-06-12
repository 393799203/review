#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple, List
from datetime import datetime, date
import requests
from app.services.base_service import BaseService
from app.repositories.misc_repository import MiscRepository


def get_limit_up_threshold(stock_code: str) -> float:
    """
    根据股票代码判断涨停阈值

    - 688开头：科创板 → 20%
    - 30开头：创业板 → 20%
    - 其他（00/60等）：沪深主板 → 10%
    """
    code = str(stock_code)
    if code.startswith('688') or code.startswith('30'):
        return 19.9
    return 9.9


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
            
            # ★ 只获取真正涨停的股票（current_status='close') ★
            today_stocks = self.misc_repository.get_stocks_by_date(trade_date, only_close=True)
            yesterday_stocks = self.misc_repository.get_stocks_by_date(prev_date, only_close=True)
            
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
            
            yesterday_premium = {}
            for stock in yesterday_list:
                height = stock.get('continuous_days', 1)
                if height not in yesterday_premium:
                    yesterday_premium[height] = []
                change_percent = stock.get('change_percent')
                threshold = get_limit_up_threshold(stock.get('code', ''))
                if change_percent is not None and change_percent < threshold:
                    yesterday_premium[height].append(change_percent)
            
            yesterday_avg_premium = {}
            for height, changes in yesterday_premium.items():
                if changes:
                    yesterday_avg_premium[height] = round(sum(changes) / len(changes), 2)

            # 竞价溢价（next_open_change）平均
            yesterday_auction_premium = {}
            for stock in yesterday_list:
                height = stock.get('continuous_days', 1)
                open_change = stock.get('open_change')
                if open_change is not None:
                    if height not in yesterday_auction_premium:
                        yesterday_auction_premium[height] = []
                    yesterday_auction_premium[height].append(open_change)
            
            yesterday_avg_auction_premium = {}
            for height, changes in yesterday_auction_premium.items():
                if changes:
                    yesterday_avg_auction_premium[height] = round(sum(changes) / len(changes), 2)
            
            return True, '获取成功', {
                'today': {
                    'date': trade_date.strftime('%Y-%m-%d'),
                    'stocks': today_list
                },
                'yesterday': {
                    'date': prev_date.strftime('%Y-%m-%d'),
                    'stocks': yesterday_list,
                    'avg_premium': yesterday_avg_premium,
                    'avg_auction_premium': yesterday_avg_auction_premium
                }
            }
            
        except Exception as e:
            return False, str(e), None

    def get_market_alerts(self) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取市场动态消息（涨停板实时状态）
        
        从数据库获取所有涨停过的股票（包括已开板的），
        通过实时行情判断当前状态

        Returns:
            tuple: (success, message, data)
        """
        try:
            latest_date = self.misc_repository.get_latest_trade_date()
            if not latest_date:
                return True, '获取成功', []

            stocks = self.misc_repository.get_stocks_by_date(latest_date)
            if not stocks:
                return True, '获取成功', []

            stock_codes = [s.stock_code for s in stocks]

            try:
                from core.quotes_utils import get_realtime_quotes
                quotes_dict = get_realtime_quotes(stock_codes, debug=False)
            except Exception as e:
                print(f"获取实时行情失败: {e}")
                quotes_dict = {}

            alerts = []
            for stock in stocks:
                code = stock.stock_code
                name = stock.stock_name
                continuous_days = stock.continuous_days
                limit_up_time = stock.limit_up_time

                time_str = ''
                if limit_up_time:
                    time_str = limit_up_time.strftime('%H:%M') if hasattr(limit_up_time, 'strftime') else str(limit_up_time)[:5]

                status = stock.current_status or 'close'
                if quotes_dict and code in quotes_dict:
                    current_price = quotes_dict[code].get('price', 0)
                    prev_close = quotes_dict[code].get('prev_close', 0)
                    if prev_close > 0 and current_price > 0:
                        change_percent = (current_price - prev_close) / prev_close * 100
                        if change_percent < 9.8:
                            status = 'open'
                        else:
                            status = 'close'

                alerts.append({
                    'code': code,
                    'name': name,
                    'continuous_days': continuous_days,
                    'time': time_str,
                    'status': status
                })

            alerts.sort(key=lambda x: x['time'] if x['time'] else '00:00', reverse=True)

            return True, '获取成功', alerts

        except Exception as e:
            print(f"获取市场动态失败: {e}")
            return False, str(e), None

    def save_market_alerts(self, alerts_data: List[Dict], trade_date_str: str = None) -> Tuple[bool, str, Optional[List]]:
        """
        保存市场动态消息到数据库

        Args:
            alerts_data: 告警数据列表
            trade_date_str: 交易日期字符串（格式：YYYY-MM-DD），不传则默认使用当天

        Returns:
            tuple: (success, message, data)
        """
        try:
            if not alerts_data:
                return True, '没有数据需要保存', []

            if trade_date_str:
                trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
            else:
                trade_date = datetime.now().date()

            alerts_with_date = [{**alert, 'trade_date': trade_date} for alert in alerts_data]
            saved_alerts = self.misc_repository.save_market_alerts_batch(alerts_with_date)

            return True, f'保存成功，共{len(saved_alerts)}条', [
                {
                    'id': a['id'],
                    'stock_code': a['stock_code'],
                    'stock_name': a['stock_name'],
                    'alert_type': a['alert_type'],
                    'status': a['status'],
                    'created_at': a['created_at'].isoformat() if a.get('created_at') else None
                }
                for a in saved_alerts
            ]

        except Exception as e:
            print(f"保存市场动态失败: {e}")
            return False, str(e), None

    def get_market_alerts_history(self, trade_date_str: str = None, limit: int = 100) -> Tuple[bool, str, Optional[List]]:
        """
        获取历史市场动态消息

        Args:
            trade_date_str: 交易日期字符串，不传则默认查询当天
            limit: 返回数量限制

        Returns:
            tuple: (success, message, data)
        """
        try:
            if trade_date_str:
                trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
            else:
                trade_date = datetime.now().date()

            alerts = self.misc_repository.get_market_alerts(trade_date, limit)

            return True, '获取成功', [
                {
                    'id': a['id'],
                    'trade_date': a['trade_date'].isoformat() if a.get('trade_date') else None,
                    'stock_code': a['stock_code'],
                    'stock_name': a['stock_name'],
                    'continuous_days': a['continuous_days'],
                    'alert_time': a['alert_time'],
                    'alert_type': a['alert_type'],
                    'status': a['status'],
                    'created_at': a['created_at'].isoformat() if a.get('created_at') else None
                }
                for a in alerts
            ]

        except Exception as e:
            print(f"获取历史市场动态失败: {e}")
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
                    
                    filtered_stocks = []
                    if stocks:
                        valid_stocks = [s for s in stocks if s.next_change is not None]
                        if valid_stocks:
                            filtered_stocks = [s for s in valid_stocks if float(s.next_change) < get_limit_up_threshold(s.stock_code)]
                            if filtered_stocks:
                                avg_change = sum(float(s.next_change) for s in filtered_stocks) / len(filtered_stocks)
                            else:
                                avg_change = None
                        else:
                            avg_change = None
                    else:
                        avg_change = None
                    
                    trend_data.append({
                        'date': trade_date.strftime('%Y-%m-%d'),
                        'avg_change_percent': round(avg_change, 2) if avg_change is not None else None,
                        'stock_count': len(filtered_stocks) if filtered_stocks else 0
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
    
    def get_auction_premium_trend(self, continuous_days: int, date_str: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取竞价溢价趋势（不过滤次日是否涨停，所有有数据的都算）
        
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
                    
                    # 竞价溢价：所有有 next_open_change 数据的都算，不排除次日涨停的
                    valid_stocks = [s for s in stocks if s.next_open_change is not None] if stocks else []
                    
                    if valid_stocks:
                        avg_change = sum(float(s.next_open_change) for s in valid_stocks) / len(valid_stocks)
                    else:
                        avg_change = None
                    
                    trend_data.append({
                        'date': trade_date.strftime('%Y-%m-%d'),
                        'avg_change_percent': round(avg_change, 2) if avg_change is not None else None,
                        'stock_count': len(valid_stocks)
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
                    'sector': stock.sector or '',
                    'limit_up_time': stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else '',
                    'seal_amount': float(stock.seal_amount) if stock.seal_amount else 0.0,
                    'seal_amount_wan': round(float(stock.seal_amount) / 10000, 2) if stock.seal_amount else 0.0,
                    'limit_up_price': float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                    'change_percent': float(stock.next_change) if stock.next_change else None,
                    'open_change': float(stock.next_open_change) if stock.next_open_change else None,
                    'turnover_rate': float(stock.turnover_rate) if stock.turnover_rate else 0.0,
                    'reason': stock.limit_up_reason or '',
                    'limit_up_type': stock.limit_up_type or '',
                    'high_days': stock.high_days or '',
                    'detail_reason': stock.ths_reason_info or '',
                    'block_name': stock.block.block_name if stock.block else '',
                    'block_info': {
                        'change_rate': float(stock.block.change_rate) if stock.block and stock.block.change_rate else 0.0,
                        'limit_up_num': stock.block.limit_up_num or 0 if stock.block else 0,
                        'continuous_num': stock.block.continuous_plate_num or 0 if stock.block else 0,
                        'high': stock.block.high or '' if stock.block else '',
                        'list_days': stock.block.list_days or 0 if stock.block else 0,
                        'high_stock_name': stock.block.high_stock_name or '' if stock.block else ''
                    },
                    'is_high_stock': stock.is_high_stock or 0,
                    'current_status': stock.current_status or 'close'
                }
            else:
                stock_data = {
                    'code': stock.stock_code,
                    'name': stock.stock_name,
                    'continuous_days': stock.continuous_days,
                    'sector': stock.sector or '',
                    'limit_up_time': stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else '',
                    'seal_amount': float(stock.seal_amount) if stock.seal_amount else 0.0,
                    'seal_amount_wan': round(float(stock.seal_amount) / 10000, 2) if stock.seal_amount else 0.0,
                    'limit_up_price': float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                    'change_percent': float(stock.change_percent) if stock.change_percent else 0.0,
                    'turnover_rate': float(stock.turnover_rate) if stock.turnover_rate else 0.0,
                    'reason': stock.limit_up_reason or '',
                    'limit_up_type': stock.limit_up_type or '',
                    'high_days': stock.high_days or '',
                    'detail_reason': stock.ths_reason_info or '',
                    'block_name': stock.block.block_name if stock.block else '',
                    'block_info': {
                        'change_rate': float(stock.block.change_rate) if stock.block and stock.block.change_rate else 0.0,
                        'limit_up_num': stock.block.limit_up_num or 0 if stock.block else 0,
                        'continuous_num': stock.block.continuous_plate_num or 0 if stock.block else 0,
                        'high': stock.block.high or '' if stock.block else '',
                        'list_days': stock.block.list_days or 0 if stock.block else 0,
                        'high_stock_name': stock.block.high_stock_name or '' if stock.block else ''
                    },
                    'is_high_stock': stock.is_high_stock or 0,
                    'current_status': stock.current_status or 'close'
                }
            
            stock_list.append(stock_data)
        
        return stock_list
    
    def get_hot_topics(self, days: int = 3) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取热门话题数据
        
        Args:
            days: 获取最近几天的数据，默认3天
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            url = 'https://news.10jqka.com.cn/app/concept_v2_api/open/api/concept/event/jtcsm/v1/event/list'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://news.10jqka.com.cn/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status_code') == 0:
                all_data = data.get('data', [])
                
                processed_topics = []
                for day_data in all_data[:days]:
                    date = day_data.get('date', '')
                    event_list = day_data.get('eventList', [])
                    
                    for event in event_list:
                        processed_topics.append({
                            'date': date,
                            'event_id': event.get('eventId', ''),
                            'title': event.get('title', ''),
                            'heat': event.get('heat', 0),
                            'themes': [theme.get('showName', '') for theme in event.get('themes', [])],
                            'investment_direction': event.get('investmentDirection', ''),
                            'top_stocks': [{
                                'code': stock.get('stockCode', ''),
                                'name': stock.get('stockName', ''),
                                'change_percent': float(stock.get('risePercent', 0)) if stock.get('risePercent') else 0.0,
                                'limit_up_state': stock.get('limitUpState'),
                            } for stock in event.get('topStocks', [])],
                            'create_time': event.get('createTime', 0),
                            'has_topped': event.get('hasTopped', False),
                        })
                
                return True, '获取热门话题成功', processed_topics
            else:
                return False, data.get('status_msg', '获取热门话题失败'), None
                
        except requests.exceptions.Timeout:
            return False, '请求超时', None
        except requests.exceptions.RequestException as e:
            return False, f'请求失败: {str(e)}', None
        except Exception as e:
            return False, f'处理数据失败: {str(e)}', None
