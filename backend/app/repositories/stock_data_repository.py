#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple
from app.repositories.base_repository import BaseRepository
from core.data_fetcher import DataFetcher
from models import WatchlistStock
from database import get_db_session


class StockDataRepository(BaseRepository):
    """股票数据仓库类"""
    
    def __init__(self):
        super().__init__(WatchlistStock)
        self.data_fetcher = DataFetcher()
    
    def get_kline_data(self, stock_code: str, days: int = 60) -> Optional[Dict]:
        """获取K线数据"""
        stock_code_clean = stock_code.split('.')[0]
        return self.data_fetcher.get_stock_kline(stock_code_clean, days)
    
    def get_intraday_data(self, stock_code: str) -> Optional[Dict]:
        """获取分时数据"""
        stock_code_clean = stock_code.split('.')[0]
        return self.data_fetcher.get_stock_intraday(stock_code_clean)
    
    def get_quote_data(self, stock_code: str) -> Optional[Dict]:
        """获取实时行情"""
        stock_code_clean = stock_code.split('.')[0]
        return self.data_fetcher.get_realtime_quote(stock_code_clean)
    
    def is_in_watchlist(self, user_id: str, stock_code: str) -> bool:
        """检查股票是否在自选中"""
        session = get_db_session()
        try:
            stock_code_clean = stock_code.split('.')[0]
            existing = session.query(WatchlistStock).filter(
                WatchlistStock.user_id == user_id,
                WatchlistStock.stock_code.like(f'{stock_code_clean}%')
            ).first()
            return existing is not None
        finally:
            session.close()
