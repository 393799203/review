#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List
from datetime import datetime
from sqlalchemy import desc
from models import TradeRecord, WatchlistStock
from app.repositories.base_repository import BaseRepository


class TradeRepository(BaseRepository):
    """交易记录仓库类"""
    
    def __init__(self):
        super().__init__(TradeRecord)
    
    def get_by_user_id(self, user_id: str) -> List[TradeRecord]:
        """根据用户ID获取交易记录"""
        session = self.create_session()
        try:
            return session.query(TradeRecord).filter(
                TradeRecord.user_id == user_id
            ).order_by(TradeRecord.operation_date.desc()).all()
        finally:
            session.close()
    
    def get_buy_records(self, user_id: str, stock_code: str) -> List[TradeRecord]:
        """获取买入记录"""
        session = self.create_session()
        try:
            return session.query(TradeRecord).filter(
                TradeRecord.user_id == user_id,
                TradeRecord.stock_code == stock_code,
                TradeRecord.operation_type == '买入',
                TradeRecord.remaining_quantity > 0
            ).order_by(TradeRecord.operation_date).all()
        finally:
            session.close()
    
    def create_buy_record(self, user_id: str, stock_code: str, stock_name: str,
                         buy_price: float, quantity: int) -> TradeRecord:
        """创建买入记录"""
        return self.create(
            user_id=user_id,
            stock_code=stock_code,
            stock_name=stock_name,
            operation_type='买入',
            price=buy_price,
            quantity=quantity,
            remaining_quantity=quantity,
            amount=buy_price * quantity,
            operation_date=datetime.now()
        )
    
    def create_sell_record(self, user_id: str, stock_code: str, stock_name: str,
                          sell_price: float, buy_price: float, quantity: int,
                          profit: float, profit_ratio: float) -> TradeRecord:
        """创建卖出记录"""
        return self.create(
            user_id=user_id,
            stock_code=stock_code,
            stock_name=stock_name,
            operation_type='卖出',
            price=sell_price,
            buy_price=buy_price,
            quantity=quantity,
            remaining_quantity=0,
            amount=sell_price * quantity,
            profit=profit,
            profit_ratio=profit_ratio,
            operation_date=datetime.now()
        )
    
    def update_remaining_quantity(self, record_id: int, new_quantity: int) -> bool:
        """更新剩余数量"""
        session = self.create_session()
        try:
            record = session.query(TradeRecord).filter(TradeRecord.id == record_id).first()
            if record:
                record.remaining_quantity = new_quantity
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
