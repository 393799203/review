#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from app.services.base_service import BaseService
from app.repositories.trade_repository import TradeRepository
from app.repositories.watchlist_repository import WatchlistRepository
from models import TradeRecord, WatchlistStock


class TradeService(BaseService):
    """交易记录服务类"""
    
    def __init__(self):
        super().__init__(TradeRepository())
        self.trade_repository = self.repository
        self.watchlist_repository = WatchlistRepository()
    
    def buy_stock(self, user_id: str, stock_code: str, buy_price: float,
                  quantity: int = 100) -> Tuple[bool, str]:
        """
        买入股票
        
        Args:
            user_id: 用户ID
            stock_code: 股票代码
            buy_price: 买入价格
            quantity: 买入数量
            
        Returns:
            tuple: (success, message)
        """
        stock = self.watchlist_repository.get_by_user_and_code(user_id, stock_code)
        
        if not stock:
            return False, '股票不在自选列表中'
        
        try:
            self.trade_repository.create_buy_record(
                user_id, stock_code, stock.stock_name, buy_price, quantity
            )
            return True, f'成功买入 {stock.stock_name}'
        except Exception as e:
            return False, str(e)
    
    def sell_stock(self, user_id: str, stock_code: str, sell_price: float,
                   quantity: int = None) -> Tuple[bool, str]:
        """
        卖出股票
        
        Args:
            user_id: 用户ID
            stock_code: 股票代码
            sell_price: 卖出价格
            quantity: 卖出数量(None表示全部卖出)
            
        Returns:
            tuple: (success, message)
        """
        stock = self.watchlist_repository.get_by_user_and_code(user_id, stock_code)
        
        if not stock:
            return False, '股票不在自选列表中'
        
        buy_records = self.trade_repository.get_buy_records(user_id, stock_code)
        
        if not buy_records:
            return False, '该股票未持仓，无法卖出'
        
        total_quantity = sum(r.remaining_quantity for r in buy_records)
        
        if not quantity:
            quantity = total_quantity
        
        if quantity > total_quantity:
            return False, f'卖出数量不能超过持仓数量（{total_quantity}股）'
        
        try:
            total_profit = 0
            remaining_to_sell = quantity
            total_buy_cost = 0
            total_sell_quantity = 0
            
            for record in buy_records:
                if remaining_to_sell <= 0:
                    break
                
                sell_from_this_record = min(remaining_to_sell, record.remaining_quantity)
                buy_price_float = float(record.price)
                profit_from_this = (sell_price - buy_price_float) * sell_from_this_record
                total_profit += profit_from_this
                
                total_buy_cost += buy_price_float * sell_from_this_record
                total_sell_quantity += sell_from_this_record
                
                new_remaining = record.remaining_quantity - sell_from_this_record
                self.trade_repository.update_remaining_quantity(record.id, new_remaining)
                
                remaining_to_sell -= sell_from_this_record
            
            avg_buy_price = total_buy_cost / total_sell_quantity if total_sell_quantity > 0 else 0
            profit_ratio = (sell_price - avg_buy_price) / avg_buy_price if avg_buy_price > 0 else 0
            
            self.trade_repository.create_sell_record(
                user_id, stock_code, stock.stock_name, sell_price,
                avg_buy_price, quantity, total_profit, profit_ratio
            )
            
            return True, f'成功卖出 {stock.stock_name} {quantity}股，盈亏: {total_profit:.2f}元'
            
        except Exception as e:
            return False, str(e)
    
    def get_trade_records(self, user_id: str) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取交易记录
        
        Args:
            user_id: 用户ID
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            records = self.trade_repository.get_by_user_id(user_id)
            
            result = []
            for record in records:
                result.append({
                    'id': record.id,
                    'stock_code': record.stock_code,
                    'stock_name': record.stock_name,
                    'operation_type': record.operation_type,
                    'price': float(record.price) if record.price else None,
                    'buy_price': float(record.buy_price) if record.buy_price else None,
                    'quantity': record.quantity,
                    'remaining_quantity': record.remaining_quantity,
                    'amount': float(record.amount) if record.amount else None,
                    'profit': float(record.profit) if record.profit else None,
                    'profit_ratio': float(record.profit_ratio) if record.profit_ratio else None,
                    'operation_date': record.operation_date.strftime('%Y-%m-%d %H:%M:%S') if record.operation_date else None,
                    'notes': record.notes or '',
                    'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else ''
                })
            
            return True, '获取成功', result
            
        except Exception as e:
            return False, str(e), None
