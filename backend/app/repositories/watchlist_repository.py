#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List
from datetime import date
from sqlalchemy import desc, func
from models import WatchlistStock, TradeRecord
from app.repositories.base_repository import BaseRepository


class WatchlistRepository(BaseRepository):
    """自选股仓库类"""
    
    def __init__(self):
        super().__init__(WatchlistStock)
    
    def get_by_user_id(self, user_id: str) -> List[WatchlistStock]:
        """根据用户ID获取自选股列表"""
        session = self.create_session()
        try:
            return session.query(WatchlistStock).filter(
                WatchlistStock.user_id == user_id
            ).order_by(desc(WatchlistStock.created_at)).all()
        finally:
            session.close()
    
    def get_by_user_and_code(self, user_id: str, stock_code: str) -> Optional[WatchlistStock]:
        """根据用户ID和股票代码获取自选股"""
        session = self.create_session()
        try:
            return session.query(WatchlistStock).filter(
                WatchlistStock.user_id == user_id,
                WatchlistStock.stock_code == stock_code
            ).first()
        finally:
            session.close()
    
    def exists_in_watchlist(self, user_id: str, stock_code: str) -> bool:
        """判断股票是否在自选中"""
        session = self.create_session()
        try:
            count = session.query(WatchlistStock).filter(
                WatchlistStock.user_id == user_id,
                WatchlistStock.stock_code == stock_code
            ).count()
            return count > 0
        finally:
            session.close()
    
    def delete_by_user_and_code(self, user_id: str, stock_code: str) -> bool:
        """删除自选股"""
        session = self.create_session()
        try:
            stock = session.query(WatchlistStock).filter(
                WatchlistStock.user_id == user_id,
                WatchlistStock.stock_code == stock_code
            ).first()
            
            if stock:
                session.delete(stock)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_total_profit(self, user_id: str, stock_code: str) -> float:
        """获取股票总盈亏"""
        session = self.create_session()
        try:
            profit = session.query(func.sum(TradeRecord.profit)).filter(
                TradeRecord.user_id == user_id,
                TradeRecord.stock_code == stock_code,
                TradeRecord.operation_type == '卖出',
                TradeRecord.profit.isnot(None)
            ).scalar()
            return float(profit) if profit else 0.0
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
            ).all()
        finally:
            session.close()
    
    def has_position(self, user_id: str, stock_code: str) -> bool:
        """判断是否有持仓"""
        session = self.create_session()
        try:
            count = session.query(TradeRecord).filter(
                TradeRecord.user_id == user_id,
                TradeRecord.stock_code == stock_code,
                TradeRecord.operation_type == '买入',
                TradeRecord.remaining_quantity > 0
            ).count()
            return count > 0
        finally:
            session.close()
