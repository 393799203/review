#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盈亏统计API
"""

from flask import jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from models import TradeRecord

def register_statistics_routes(app, get_db_session):
    """注册统计相关路由"""
    
    @app.route('/api/statistics/profit', methods=['GET'])
    def get_profit_statistics():
        """获取盈亏统计数据"""
        session = get_db_session()
        
        try:
            period = request.args.get('period', 'day')
            
            if period == 'day':
                data = get_daily_profit(session)
            elif period == 'week':
                data = get_weekly_profit(session)
            elif period == 'month':
                data = get_monthly_profit(session)
            else:
                data = get_daily_profit(session)
            
            return jsonify({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        finally:
            session.close()
    
    def get_daily_profit(session):
        """获取每日盈亏统计"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        results = session.query(
            func.date(TradeRecord.operation_date).label('date'),
            func.sum(TradeRecord.profit).label('profit'),
            func.sum(TradeRecord.amount).label('amount'),
            func.count(TradeRecord.id).label('count')
        ).filter(
            and_(
                func.date(TradeRecord.operation_date) >= start_date,
                func.date(TradeRecord.operation_date) <= end_date,
                TradeRecord.operation_type == '卖出',
                TradeRecord.profit.isnot(None)
            )
        ).group_by(
            func.date(TradeRecord.operation_date)
        ).order_by(
            func.date(TradeRecord.operation_date)
        ).all()
        
        data = []
        for result in results:
            data.append({
                'date': str(result.date),
                'profit': float(result.profit) if result.profit else 0,
                'amount': float(result.amount) if result.amount else 0,
                'count': result.count
            })
        
        return data
    
    def get_weekly_profit(session):
        """获取每周盈亏统计"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
        
        results = session.query(
            TradeRecord.operation_date,
            TradeRecord.profit,
            TradeRecord.amount
        ).filter(
            and_(
                func.date(TradeRecord.operation_date) >= start_date,
                func.date(TradeRecord.operation_date) <= end_date,
                TradeRecord.operation_type == '卖出',
                TradeRecord.profit.isnot(None)
            )
        ).all()
        
        weekly_data = {}
        for result in results:
            if result.operation_date:
                operation_date = result.operation_date.date() if hasattr(result.operation_date, 'date') else result.operation_date
                week_start = operation_date - timedelta(days=operation_date.weekday())
                week_key = week_start.strftime('%Y-%m-%d')
                
                if week_key not in weekly_data:
                    weekly_data[week_key] = {
                        'profit': 0,
                        'amount': 0,
                        'count': 0
                    }
                
                weekly_data[week_key]['profit'] += float(result.profit) if result.profit else 0
                weekly_data[week_key]['amount'] += float(result.amount) if result.amount else 0
                weekly_data[week_key]['count'] += 1
        
        data = []
        for week_key in sorted(weekly_data.keys()):
            data.append({
                'date': week_key,
                'profit': weekly_data[week_key]['profit'],
                'amount': weekly_data[week_key]['amount'],
                'count': weekly_data[week_key]['count']
            })
        
        return data
    
    def get_monthly_profit(session):
        """获取每月盈亏统计"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)
        
        results = session.query(
            TradeRecord.operation_date,
            TradeRecord.profit,
            TradeRecord.amount
        ).filter(
            and_(
                func.date(TradeRecord.operation_date) >= start_date,
                func.date(TradeRecord.operation_date) <= end_date,
                TradeRecord.operation_type == '卖出',
                TradeRecord.profit.isnot(None)
            )
        ).all()
        
        monthly_data = {}
        for result in results:
            if result.operation_date:
                operation_date = result.operation_date.date() if hasattr(result.operation_date, 'date') else result.operation_date
                month_key = operation_date.strftime('%Y-%m')
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'profit': 0,
                        'amount': 0,
                        'count': 0
                    }
                
                monthly_data[month_key]['profit'] += float(result.profit) if result.profit else 0
                monthly_data[month_key]['amount'] += float(result.amount) if result.amount else 0
                monthly_data[month_key]['count'] += 1
        
        data = []
        for month_key in sorted(monthly_data.keys()):
            data.append({
                'date': month_key,
                'profit': monthly_data[month_key]['profit'],
                'amount': monthly_data[month_key]['amount'],
                'count': monthly_data[month_key]['count']
            })
        
        return data
