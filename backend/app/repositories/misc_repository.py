#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict
from datetime import datetime, date
from sqlalchemy import desc
from models import LimitUpStock, LadderStats
from app.repositories.base_repository import BaseRepository
from database import get_db_session


class MiscRepository(BaseRepository):
    """辅助接口仓库类"""
    
    def __init__(self):
        super().__init__(None)
    
    def get_prev_trade_date(self, trade_date: date) -> Optional[date]:
        """获取上一个交易日"""
        session = get_db_session()
        try:
            prev_trade_date = session.query(LadderStats.trade_date).filter(
                LadderStats.trade_date < trade_date
            ).order_by(desc(LadderStats.trade_date)).first()
            
            return prev_trade_date[0] if prev_trade_date else None
        finally:
            session.close()
    
    def get_stocks_by_date(self, trade_date: date) -> List[LimitUpStock]:
        """获取指定日期的涨停股票"""
        session = get_db_session()
        try:
            return session.query(LimitUpStock).filter(
                LimitUpStock.trade_date == trade_date
            ).all()
        finally:
            session.close()
    
    def get_latest_trade_date(self) -> Optional[date]:
        """获取最新交易日"""
        session = get_db_session()
        try:
            latest_stat = session.query(LadderStats.trade_date).order_by(
                desc(LadderStats.trade_date)
            ).first()
            return latest_stat[0] if latest_stat else None
        finally:
            session.close()
    
    def get_recent_trade_dates(self, end_date: date, limit: int = 10) -> List[date]:
        """获取最近的交易日列表"""
        session = get_db_session()
        try:
            recent_dates = session.query(LadderStats.trade_date).filter(
                LadderStats.trade_date <= end_date
            ).order_by(desc(LadderStats.trade_date)).limit(limit).all()
            
            return [d[0] for d in recent_dates]
        finally:
            session.close()
    
    def get_stocks_by_date_and_continuous(self, trade_date: date, 
                                         continuous_days: int) -> List[LimitUpStock]:
        """获取指定日期和连板数的股票"""
        session = get_db_session()
        try:
            return session.query(LimitUpStock).filter(
                LimitUpStock.trade_date == trade_date,
                LimitUpStock.continuous_days == continuous_days
            ).all()
        finally:
            session.close()
