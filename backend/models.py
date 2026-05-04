#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型
"""

from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Numeric, Text, Time, UniqueConstraint, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()


class Block(Base):
    """板块表"""
    __tablename__ = 'blocks'
    __table_args__ = (
        UniqueConstraint('block_code', 'trade_date', name='uq_block_date'),
        Index('idx_blocks_date', 'trade_date'),
        Index('idx_blocks_code', 'block_code'),
        Index('idx_blocks_name', 'block_name'),
        Index('idx_blocks_limit_num', 'limit_up_num'),
        Index('idx_blocks_continuous_num', 'continuous_plate_num'),
    )
    
    id = Column(Integer, primary_key=True)
    block_code = Column(String(20), nullable=False)
    block_name = Column(String(100), nullable=False)
    trade_date = Column(Date, nullable=False)
    change_rate = Column(Numeric(10, 4))
    limit_up_num = Column(Integer, default=0)
    continuous_plate_num = Column(Integer, default=0)
    high = Column(String(20))
    high_num = Column(Integer, default=0)
    list_days = Column(Integer, default=0)
    high_stock_code = Column(String(10))
    high_stock_name = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    stocks = relationship("LimitUpStock", back_populates="block")


class LimitUpStock(Base):
    """涨停股票表"""
    __tablename__ = 'limit_up_stocks'
    __table_args__ = (
        UniqueConstraint('stock_code', 'trade_date', name='uq_stock_date'),
        Index('idx_stocks_date', 'trade_date'),
        Index('idx_stocks_code', 'stock_code'),
        Index('idx_stocks_days', 'continuous_days'),
        Index('idx_stocks_date_days', 'trade_date', 'continuous_days'),
        Index('idx_stocks_date_time', 'trade_date', 'limit_up_time'),
        Index('idx_stocks_block_id', 'block_id'),
        Index('idx_stocks_reason', 'limit_up_reason'),
        Index('idx_stocks_change', 'change_percent'),
        Index('idx_stocks_seal', 'seal_amount'),
        Index('idx_stocks_sector', 'sector'),
    )
    
    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), nullable=False)
    trade_date = Column(Date, nullable=False)
    limit_up_reason = Column(String(200))
    limit_up_time = Column(Time)
    limit_up_price = Column(Numeric(10, 2))
    limit_up_type = Column(String(20))
    block_id = Column(Integer, ForeignKey('blocks.id'))
    ths_reason_info = Column(Text)
    seal_amount = Column(Numeric(15, 2))
    continuous_days = Column(Integer, default=1)
    high_days = Column(String(20))
    sector = Column(String(50))
    change_percent = Column(Numeric(10, 4))
    turnover_rate = Column(Numeric(10, 4))
    amount = Column(Numeric(20, 2))
    is_high_stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    block = relationship("Block", back_populates="stocks")


class LadderStats(Base):
    """连板天梯统计表"""
    __tablename__ = 'ladder_stats'
    
    id = Column(Integer, primary_key=True)
    trade_date = Column(Date, nullable=False, unique=True)
    total_count = Column(Integer, default=0)
    first_board = Column(Integer, default=0)
    second_board = Column(Integer, default=0)
    third_board = Column(Integer, default=0)
    fourth_board = Column(Integer, default=0)
    fifth_board = Column(Integer, default=0)
    sixth_board = Column(Integer, default=0)
    seventh_board = Column(Integer, default=0)
    eighth_plus_board = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


class FetchLog(Base):
    """数据抓取日志表"""
    __tablename__ = 'fetch_logs'
    __table_args__ = (
        Index('idx_logs_date', 'fetch_date'),
        Index('idx_logs_status', 'status'),
        Index('idx_logs_time', 'fetch_time'),
    )
    
    id = Column(Integer, primary_key=True)
    fetch_date = Column(Date, nullable=False)
    fetch_time = Column(DateTime, default=datetime.now)
    status = Column(String(20), nullable=False)
    stocks_count = Column(Integer, default=0)
    error_message = Column(Text)
    duration_seconds = Column(Integer)


class WatchlistStock(Base):
    """自选股表"""
    __tablename__ = 'watchlist_stocks'
    __table_args__ = (
        UniqueConstraint('stock_code', name='uq_watchlist_stock'),
        Index('idx_watchlist_created', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), nullable=False)
    add_date = Column(Date, nullable=False)
    add_price = Column(Numeric(10, 2))
    current_price = Column(Numeric(10, 2))
    profit_amount = Column(Numeric(10, 2))
    profit_ratio = Column(Numeric(10, 4))
    add_reason = Column(String(200))
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DatabaseConfig:
    """数据库配置"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            self.host = os.getenv('DB_HOST', 'localhost')
            self.port = os.getenv('DB_PORT', '5432')
            self.database = os.getenv('DB_NAME', 'stock_review')
            self.user = os.getenv('DB_USER', 'postgres')
            self.password = os.getenv('DB_PASSWORD', 'postgres')
    
    def get_database_url(self):
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def create_engine(self):
        return create_engine(self.get_database_url(), echo=False)
    
    def create_session(self):
        engine = self.create_engine()
        Session = sessionmaker(bind=engine)
        return Session()


def init_database():
    """初始化数据库"""
    config = DatabaseConfig()
    engine = config.create_engine()
    
    Base.metadata.create_all(engine)
    
    print("数据库表创建成功！")


if __name__ == "__main__":
    init_database()
