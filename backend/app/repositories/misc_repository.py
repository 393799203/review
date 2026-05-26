#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict
from datetime import datetime, date
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from models import LimitUpStock, LadderStats, MarketAlert
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
            return session.query(LimitUpStock).options(
                joinedload(LimitUpStock.block)
            ).filter(
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

    def save_market_alert(self, alert_data: Dict) -> Dict:
        """保存市场动态消息"""
        session = get_db_session()
        try:
            alert = MarketAlert(
                trade_date=alert_data['trade_date'],
                stock_code=alert_data['stock_code'],
                stock_name=alert_data['stock_name'],
                continuous_days=alert_data.get('continuous_days', 1),
                alert_time=alert_data.get('alert_time'),
                alert_type=alert_data['alert_type'],
                status=alert_data['status']
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            return {
                'id': alert.id,
                'trade_date': alert.trade_date,
                'stock_code': alert.stock_code,
                'stock_name': alert.stock_name,
                'continuous_days': alert.continuous_days,
                'alert_time': alert.alert_time,
                'alert_type': alert.alert_type,
                'status': alert.status,
                'created_at': alert.created_at
            }
        finally:
            session.close()

    def save_market_alerts_batch(self, alerts_data: List[Dict]) -> List[Dict]:
        """批量保存市场动态消息（自动去重）"""
        session = get_db_session()
        try:
            from sqlalchemy import text
            saved_alerts = []
            for alert_data in alerts_data:
                trade_date = alert_data['trade_date']
                if isinstance(trade_date, str):
                    trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()

                sql = text("""
                    INSERT INTO market_alerts (trade_date, stock_code, stock_name, continuous_days, alert_time, alert_type, status)
                    VALUES (:trade_date, :stock_code, :stock_name, :continuous_days, :alert_time, :alert_type, :status)
                    ON CONFLICT (stock_code, alert_type) DO UPDATE SET
                        trade_date = EXCLUDED.trade_date,
                        stock_name = EXCLUDED.stock_name,
                        continuous_days = EXCLUDED.continuous_days,
                        alert_time = EXCLUDED.alert_time,
                        status = EXCLUDED.status,
                        created_at = CURRENT_TIMESTAMP
                    RETURNING id, trade_date, stock_code, stock_name, continuous_days, alert_time, alert_type, status, created_at
                """)
                result = session.execute(sql, {
                    'trade_date': trade_date,
                    'stock_code': alert_data['stock_code'],
                    'stock_name': alert_data['stock_name'],
                    'continuous_days': alert_data.get('continuous_days', 1),
                    'alert_time': alert_data.get('alert_time'),
                    'alert_type': alert_data['alert_type'],
                    'status': alert_data['status']
                })
                row = result.fetchone()
                if row:
                    saved_alerts.append({
                        'id': row[0],
                        'trade_date': row[1],
                        'stock_code': row[2],
                        'stock_name': row[3],
                        'continuous_days': row[4],
                        'alert_time': row[5],
                        'alert_type': row[6],
                        'status': row[7],
                        'created_at': row[8]
                    })
            session.commit()
            return saved_alerts
        finally:
            session.close()

    def get_market_alerts(self, trade_date: date = None, limit: int = 100) -> List[Dict]:
        """获取市场动态消息"""
        session = get_db_session()
        try:
            query = session.query(MarketAlert)
            if trade_date:
                query = query.filter(MarketAlert.trade_date == trade_date)
            alerts = query.order_by(desc(MarketAlert.created_at)).limit(limit).all()
            return [
                {
                    'id': a.id,
                    'trade_date': a.trade_date,
                    'stock_code': a.stock_code,
                    'stock_name': a.stock_name,
                    'continuous_days': a.continuous_days,
                    'alert_time': a.alert_time,
                    'alert_type': a.alert_type,
                    'status': a.status,
                    'created_at': a.created_at
                }
                for a in alerts
            ]
        finally:
            session.close()

    def get_market_alerts_by_date_range(self, start_date: date, end_date: date) -> List[Dict]:
        """按日期范围获取市场动态消息"""
        session = get_db_session()
        try:
            alerts = session.query(MarketAlert).filter(
                MarketAlert.trade_date >= start_date,
                MarketAlert.trade_date <= end_date
            ).order_by(desc(MarketAlert.created_at)).all()
            return [
                {
                    'id': a.id,
                    'trade_date': a.trade_date,
                    'stock_code': a.stock_code,
                    'stock_name': a.stock_name,
                    'continuous_days': a.continuous_days,
                    'alert_time': a.alert_time,
                    'alert_type': a.alert_type,
                    'status': a.status,
                    'created_at': a.created_at
                }
                for a in alerts
            ]
        finally:
            session.close()
