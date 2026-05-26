#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple, List
from datetime import datetime, date
from app.services.base_service import BaseService
from app.repositories.stock_diff_repository import StockDiffRepository
from models import StockDiffRecord


class StockDiffService(BaseService):
    """股票对比服务类"""
    
    def __init__(self):
        super().__init__(StockDiffRepository())
        self.stock_diff_repository = self.repository
    
    def save_stock_diff(self, trade_date_str: str, added_stocks: List[Dict],
                       removed_stocks: List[Dict]) -> Tuple[bool, str, Optional[Dict]]:
        """
        保存股票对比结果
        
        Args:
            trade_date_str: 交易日期字符串
            added_stocks: 新增股票列表
            removed_stocks: 移除股票列表
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if not trade_date_str:
                return False, '缺少交易日期参数', None
            
            trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
            
            self.stock_diff_repository.delete_by_date(trade_date)
            
            records = []
            
            for stock in added_stocks:
                record = StockDiffRecord(
                    trade_date=trade_date,
                    diff_type='added',
                    stock_code=stock.get('code', ''),
                    stock_name=stock.get('name', ''),
                    level=stock.get('level', 1),
                    limit_up_time=datetime.strptime(stock.get('limitUpTime'), '%H:%M:%S').time() if stock.get('limitUpTime') else None
                )
                records.append(record)
            
            for stock in removed_stocks:
                record = StockDiffRecord(
                    trade_date=trade_date,
                    diff_type='removed',
                    stock_code=stock.get('code', ''),
                    stock_name=stock.get('name', ''),
                    level=stock.get('level', 1),
                    limit_up_time=datetime.strptime(stock.get('limitUpTime'), '%H:%M:%S').time() if stock.get('limitUpTime') else None
                )
                records.append(record)
            
            if records:
                self.stock_diff_repository.bulk_save_records(records)
            
            return True, f'保存成功,共{len(records)}条记录', {
                'added_count': len(added_stocks),
                'removed_count': len(removed_stocks)
            }
            
        except Exception as e:
            return False, str(e), None
    
    def load_stock_diff(self, date_str: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        加载股票对比结果
        
        Args:
            date_str: 交易日期字符串
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            records = self.stock_diff_repository.get_by_date(trade_date)
            
            added = []
            removed = []
            
            for record in records:
                stock_data = {
                    'code': record.stock_code,
                    'name': record.stock_name,
                    'level': record.level,
                    'limitUpTime': record.limit_up_time.strftime('%H:%M:%S') if record.limit_up_time else None
                }
                
                if record.diff_type == 'added':
                    added.append(stock_data)
                else:
                    removed.append(stock_data)
            
            return True, '加载成功', {
                'added': added,
                'removed': removed
            }
            
        except Exception as e:
            return False, str(e), None
    
    def clear_stock_diff(self, date_str: str) -> Tuple[bool, str, None]:
        """
        清空指定日期的股票对比结果
        
        Args:
            date_str: 交易日期字符串
            
        Returns:
            tuple: (success, message, None)
        """
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            self.stock_diff_repository.delete_by_date(trade_date)
            
            return True, '清空成功', None
            
        except Exception as e:
            return False, str(e), None
