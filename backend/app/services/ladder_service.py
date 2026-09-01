#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Tuple
from datetime import date, datetime
from app.services.base_service import BaseService
from app.repositories.stock_repository import StockRepository
from models import LimitUpStock, LadderStats


class LadderService(BaseService):
    """连板天梯服务类"""
    
    LEVEL_LABELS = {
        1: "首板", 2: "2连板", 3: "3连板", 4: "4连板",
        5: "5连板", 6: "6连板", 7: "7连板", 8: "8连板及以上"
    }
    
    def __init__(self):
        super().__init__(StockRepository())
        self.stock_repository = self.repository
    
    def get_all_dates(self) -> List[str]:
        """获取所有可用日期"""
        dates = self.stock_repository.get_all_trade_dates()
        return [d.strftime('%Y%m%d') for d in dates]
    
    def get_data_by_date(self, date_str: str, data_fetcher=None) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取指定日期的完整数据
        
        Args:
            date_str: 日期字符串(YYYYMMDD)
            data_fetcher: 数据抓取器实例
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            if trade_date > datetime.now().date():
                return False, '无法获取未来日期的数据', None
            
            now = datetime.now()
            is_today = trade_date == now.date()
            
            # ★ 只获取真正涨停的股票（current_status='close') ★
            stocks = self.stock_repository.get_stocks_by_date(trade_date, only_close=True)
            stats = self.stock_repository.get_stats_by_date(trade_date)
            
            trading_start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
            trading_end_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
            is_trading_hours = is_today and trading_start_time <= now <= trading_end_time
            
            if not stocks or not stats:
                if is_today and now < trading_start_time:
                    yesterday_data = self._get_yesterday_data(trade_date)
                    return True, '今日暂无数据', {
                        'ladder': [],
                        'statistics': self._get_empty_statistics(),
                        'yesterday': yesterday_data,
                        'opened': []
                    }
                else:
                    if data_fetcher:
                        success = self._fetch_and_save_data(date_str, data_fetcher)
                        if success:
                            # ★ 只获取真正涨停的股票（current_status='close') ★
                            stocks = self.stock_repository.get_stocks_by_date(trade_date, only_close=True)
                            stats = self.stock_repository.get_stats_by_date(trade_date)
                        else:
                            return False, '该日期暂无涨停股票数据', None
                    else:
                        return False, '该日期暂无涨停股票数据', None
            
            ladder = self._build_ladder(stocks, trade_date, is_trading_hours)
            statistics = self._build_statistics(stats)
            yesterday_data = self._get_yesterday_data(trade_date)
            opened_data = self._get_opened_stocks(trade_date)
            
            return True, '获取成功', {
                'ladder': ladder,
                'statistics': statistics,
                'yesterday': yesterday_data,
                'opened': opened_data
            }
            
        except Exception as e:
            return False, str(e), None
    
    def _get_opened_stocks(self, trade_date) -> List[Dict]:
        """获取当天开板股票列表（current_status='open'），供前端市场动态对比出开板提示"""
        try:
            all_stocks = self.stock_repository.get_stocks_by_date(trade_date)
            opened = [
                s for s in all_stocks if (s.current_status or 'close') == 'open'
            ]
            return [{
                'code': s.stock_code,
                'name': s.stock_name,
                'continuous_days': s.continuous_days,
                'limit_up_time': s.limit_up_time.strftime('%H:%M') if s.limit_up_time else '',
                'current_status': 'open'
            } for s in opened]
        except Exception:
            return []
    
    def _build_ladder(self, stocks: List[LimitUpStock], trade_date: date = None, is_trading_hours: bool = False) -> List[Dict]:
        """构建连板天梯数据"""
        ladder_dict = {}

        # 盘中实时时，对首板以上且 reason 为空/"未分类"的股票，批量查询上一交易日 reason
        prev_reason_map = {}
        if is_trading_hours and trade_date:
            need_fallback_codes = [
                stock.stock_code for stock in stocks
                if stock.continuous_days >= 2
                and (not stock.limit_up_reason or stock.limit_up_reason == '未分类')
            ]
            if need_fallback_codes:
                prev_reason_map = self._get_prev_reasons(trade_date, need_fallback_codes)
        
        for stock in stocks:
            level = stock.continuous_days
            
            if level not in ladder_dict:
                ladder_dict[level] = {
                    'level': level,
                    'label': self.LEVEL_LABELS.get(level, f"{level}连板"),
                    'stocks': []
                }

            # 回退逻辑：盘中实时，首板以上，reason 为空/"未分类"
            reason = stock.limit_up_reason or ''
            if (is_trading_hours and level >= 2
                and (not reason or reason == '未分类')
                and stock.stock_code in prev_reason_map):
                fallback_reason = prev_reason_map[stock.stock_code]
                if fallback_reason and fallback_reason != '未分类':
                    reason = fallback_reason
            
            stock_data = {
                'code': stock.stock_code,
                'name': stock.stock_name,
                'continuous_days': stock.continuous_days,
                'limit_up_time': stock.limit_up_time.strftime('%H:%M') if stock.limit_up_time else '',
                'seal_amount': float(stock.seal_amount) if stock.seal_amount else 0.0,
                'seal_amount_wan': round(float(stock.seal_amount) / 10000, 2) if stock.seal_amount else 0.0,
                'limit_up_price': float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                'change_percent': float(stock.change_percent) if stock.change_percent else 0.0,
                'turnover_rate': float(stock.turnover_rate) if stock.turnover_rate else 0.0,
                'reason': reason,
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
            
            ladder_dict[level]['stocks'].append(stock_data)
        
        ladder = sorted(ladder_dict.values(), key=lambda x: x['level'], reverse=True)
        
        return ladder
    
    def _get_prev_reasons(self, trade_date: date, stock_codes: List[str]) -> Dict[str, str]:
        """获取上一交易日多个股票的涨停关键词"""
        try:
            from core.trade_calendar import trade_calendar

            prev_trading_days = trade_calendar.get_recent_trading_days(2, end_date=trade_date)
            if not prev_trading_days or len(prev_trading_days) < 2:
                return {}

            prev_date_str = prev_trading_days[1]
            prev_date = datetime.strptime(prev_date_str, '%Y%m%d').date()

            return self.stock_repository.get_prev_reasons_by_codes(prev_date, stock_codes)
        except Exception as e:
            print(f"获取上一交易日涨停关键词失败: {e}")
            return {}
    
    def _format_stock_data(self, stock: LimitUpStock) -> Dict:
        """格式化股票数据"""
        block_info = {}
        block_name = ""
        if stock.block:
            block_name = stock.block.block_name
            block_info = {
                "change_rate": float(stock.block.change_rate) if stock.block.change_rate else 0.0,
                "limit_up_num": stock.block.limit_up_num or 0,
                "continuous_num": stock.block.continuous_plate_num or 0,
                "high": stock.block.high or "",
                "list_days": stock.block.list_days or 0,
                "high_stock_name": stock.block.high_stock_name or ""
            }
        
        return {
            "code": stock.stock_code,
            "name": stock.stock_name,
            "reason": stock.limit_up_reason or "未分类",
            "limit_up_time": stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else "",
            "limit_up_price": float(stock.limit_up_price) if stock.limit_up_price else 0.0,
            "limit_up_type": stock.limit_up_type or "",
            "high_days": stock.high_days or "",
            "block_name": block_name,
            "block_info": block_info,
            "detail_reason": stock.ths_reason_info or "",
            "seal_amount": float(stock.seal_amount) if stock.seal_amount else 0.0,
            "seal_amount_wan": round(float(stock.seal_amount) / 10000, 2) if stock.seal_amount else 0.0,
            "continuous_days": stock.continuous_days,
            "sector": stock.sector or "未知",
            "change_percent": float(stock.change_percent) if stock.change_percent else 0.0,
            "turnover_rate": float(stock.turnover_rate) if stock.turnover_rate else 0.0,
            "is_high_stock": stock.is_high_stock or 0
        }
    
    def _build_statistics(self, stats: LadderStats) -> Dict:
        """构建统计数据"""
        if not stats:
            return self._get_empty_statistics()
        
        return {
            'total_count': stats.total_count,
            'first_board': stats.first_board,
            'second_board': stats.second_board,
            'third_board': stats.third_board,
            'fourth_board': stats.fourth_board,
            'fifth_plus_board': (stats.fifth_board + stats.sixth_board + 
                               stats.seventh_board + stats.eighth_plus_board)
        }
    
    def _get_empty_statistics(self) -> Dict:
        """获取空统计数据"""
        return {
            'total_count': 0,
            'first_board': 0,
            'second_board': 0,
            'third_board': 0,
            'fourth_board': 0,
            'fifth_plus_board': 0
        }
    
    def _get_yesterday_data(self, trade_date: date) -> Optional[Dict]:
        """获取昨天数据"""
        try:
            from core.trade_calendar import trade_calendar
            
            prev_trading_days = trade_calendar.get_recent_trading_days(2, end_date=trade_date)
            
            if prev_trading_days and len(prev_trading_days) >= 2:
                prev_date_str = prev_trading_days[1]
                prev_date = datetime.strptime(prev_date_str, '%Y%m%d').date()
                
                max_level = self.stock_repository.get_max_continuous_days_by_date(prev_date)
                
                if max_level > 0:
                    return {
                        'date': prev_date_str,
                        'max_level': max_level,
                        'label': self.LEVEL_LABELS.get(max_level, f"{max_level}连板")
                    }
        except Exception as e:
            print(f"获取昨天数据失败: {e}")
        
        return None
    
    def _fetch_and_save_data(self, date_str: str, data_fetcher) -> bool:
        """抓取并保存数据"""
        try:
            from core.fetch_data import LimitUpFetcher
            
            fetcher = LimitUpFetcher(data_fetcher=data_fetcher)
            success = fetcher.fetch_and_save(date_str)
            
            if success:
                print(f"日期 {date_str} 数据同步成功")
            else:
                print(f"日期 {date_str} 数据同步失败")
            
            return success
        except Exception as e:
            print(f"日期 {date_str} 数据同步失败: {e}")
            return False
    
    def get_block_strength_by_date(self, trade_date: date, min_limit_up_num: int = 1) -> List[Dict]:
        """获取板块强度"""
        blocks = self.stock_repository.get_blocks_by_date(trade_date, min_limit_up_num)
        
        result = []
        for index, block in enumerate(blocks, 1):
            result.append({
                'block_code': block.block_code,
                'block_name': block.block_name,
                'limit_up_num': block.limit_up_num,
                'continuous_plate_num': block.continuous_plate_num,
                'change_rate': float(block.change_rate) if block.change_rate else 0.0,
                'high': block.high or '',
                'high_num': block.high_num or 0,
                'rank': index,
                'high_stock_code': block.high_stock_code or '',
                'high_stock_name': block.high_stock_name or ''
            })
        
        return result
    
    def get_continuous_blocks(self, min_continuous_num: int = 2, limit: int = 50) -> List[Dict]:
        """获取连续板块"""
        return self.stock_repository.get_continuous_blocks(min_continuous_num, limit)
    
    def get_statistics_by_date(self, trade_date: date) -> Optional[Dict]:
        """获取指定日期的统计数据"""
        stats = self.stock_repository.get_stats_by_date(trade_date)
        
        if not stats:
            return None
        
        return {
            'total_count': stats.total_count,
            'first_board': stats.first_board,
            'second_board': stats.second_board,
            'third_board': stats.third_board,
            'fourth_board': stats.fourth_board,
            'fifth_plus_board': stats.fifth_board + stats.sixth_board + 
                               stats.seventh_board + stats.eighth_plus_board
        }

    def update_stock_block(self, stock_code: str, trade_date: date, block_id: int = None, block_name: str = None) -> bool:
        """更新股票板块"""
        if block_name:
            return self.stock_repository.update_stock_block_by_name(stock_code, trade_date, block_name)
        else:
            return self.stock_repository.update_stock_block(stock_code, trade_date, block_id)
