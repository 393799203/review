#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict
from datetime import date, datetime
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload
from models import LimitUpStock, LadderStats, Block
from app.repositories.base_repository import BaseRepository


class StockRepository(BaseRepository):
    """股票仓库类"""
    
    def __init__(self):
        super().__init__(LimitUpStock)
    
    def get_all_trade_dates(self) -> List[date]:
        """获取所有交易日期"""
        session = self.create_session()
        try:
            dates = session.query(LadderStats.trade_date).order_by(
                desc(LadderStats.trade_date)
            ).all()
            return [d[0] for d in dates]
        finally:
            session.close()
    
    def get_stocks_by_date(self, trade_date: date, only_close: bool = False) -> List[LimitUpStock]:
        """根据日期获取涨停股票
        
        Args:
            trade_date: 交易日期
            only_close: 是否只获取封板的股票（current_status='close'）
        """
        session = self.create_session()
        try:
            query = session.query(LimitUpStock).options(
                joinedload(LimitUpStock.block)
            ).filter(
                LimitUpStock.trade_date == trade_date
            )
            
            if only_close:
                query = query.filter(LimitUpStock.current_status == 'close')
            
            return query.order_by(desc(LimitUpStock.seal_amount)).all()
        finally:
            session.close()
    
    def get_stats_by_date(self, trade_date: date) -> Optional[LadderStats]:
        """根据日期获取统计数据"""
        session = self.create_session()
        try:
            return session.query(LadderStats).filter(
                LadderStats.trade_date == trade_date
            ).first()
        finally:
            session.close()
    
    def get_block_by_id(self, block_id: int) -> Optional[Block]:
        """根据ID获取板块"""
        session = self.create_session()
        try:
            return session.query(Block).filter(Block.id == block_id).first()
        finally:
            session.close()
    
    def update_stock_block(self, stock_code: str, trade_date: date, block_id: int) -> bool:
        """更新股票板块"""
        session = self.create_session()
        try:
            stock = session.query(LimitUpStock).filter(
                LimitUpStock.stock_code == stock_code,
                LimitUpStock.trade_date == trade_date
            ).first()
            if stock:
                stock.block_id = block_id
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_stock_block_by_name(self, stock_code: str, trade_date: date, block_name: str) -> bool:
        """根据板块名称更新股票板块"""
        session = self.create_session()
        try:
            stock = session.query(LimitUpStock).filter(
                LimitUpStock.stock_code == stock_code,
                LimitUpStock.trade_date == trade_date
            ).first()
            
            if not stock:
                return False
            
            block = session.query(Block).filter(
                Block.block_name == block_name,
                Block.trade_date == trade_date
            ).first()
            
            if not block:
                return False
            
            stock.block_id = block.id
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_blocks_by_date(self, trade_date: date, min_limit_up_num: int = 1) -> List[Block]:
        """根据日期获取板块列表"""
        session = self.create_session()
        try:
            return session.query(Block).filter(
                Block.trade_date == trade_date,
                Block.limit_up_num >= min_limit_up_num
            ).order_by(desc(Block.limit_up_num)).all()
        finally:
            session.close()
    
    def get_continuous_blocks(self, min_continuous_num: int = 2, limit: int = 50) -> List[Dict]:
        """获取连续板块"""
        session = self.create_session()
        try:
            blocks = session.query(Block).filter(
                Block.continuous_plate_num >= min_continuous_num
            ).order_by(desc(Block.continuous_plate_num), desc(Block.limit_up_num)).limit(limit).all()
            
            result = []
            for block in blocks:
                result.append({
                    'block_code': block.block_code,
                    'block_name': block.block_name,
                    'trade_date': block.trade_date.strftime('%Y%m%d'),
                    'limit_up_num': block.limit_up_num,
                    'continuous_num': block.continuous_plate_num,
                    'change_rate': float(block.change_rate) if block.change_rate else 0.0,
                    'high': block.high or '',
                    'high_stock_name': block.high_stock_name or ''
                })
            return result
        finally:
            session.close()
    
    def get_max_continuous_days_by_date(self, trade_date: date) -> int:
        """获取指定日期的最大连板数"""
        session = self.create_session()
        try:
            stocks = session.query(LimitUpStock).filter(
                LimitUpStock.trade_date == trade_date
            ).all()
            
            max_level = 0
            for stock in stocks:
                level = min(stock.continuous_days, 8)
                if level > max_level:
                    max_level = level
            return max_level
        finally:
            session.close()
