#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask后端API
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from dotenv import load_dotenv
import sys
import os
import threading
import json
import requests
from mootdx.quotes import Quotes

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import DatabaseConfig, LimitUpStock, LadderStats, init_database, Block, WatchlistStock, TradeRecord, AIAnalysisResult, User, StockDiffRecord, ClsNews, UserWencaiStrategy, WatchlistAnalysisResult, ResearchReportAnalysisResult
from data_fetcher import DataFetcher
from statistics_api import register_statistics_routes
from limit_up_analyzer import LimitUpReasonAnalyzer

app = Flask(__name__)
CORS(app)

app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'yunque.ai@qq.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = 'yunque.ai@qq.com'

mail = Mail(app)

db_config = DatabaseConfig()

data_fetcher = DataFetcher()


@app.before_request
def update_user_activity():
    """更新用户最后活动时间"""
    try:
        uid = request.headers.get('X-User-Uid')
        if uid and request.path.startswith('/api/') and not request.path.startswith('/api/health'):
            session = get_db_session()
            try:
                user = session.query(User).filter(User.uid == uid).first()
                if user:
                    user.last_activity = datetime.now()
                    session.commit()
            except:
                pass
            finally:
                session.close()
    except:
        pass


def init_ths_session():
    """初始化同花顺会话并启动心跳"""
    print("初始化同花顺会话...")
    if data_fetcher.init_session():
        data_fetcher.start_heartbeat(interval=60)
        print("✓ 同花顺会话初始化完成")
    else:
        print("✗ 同花顺会话初始化失败，将在请求时重试")


def get_db_session():
    """获取数据库会话"""
    return db_config.create_session()


register_statistics_routes(app, get_db_session)


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok', 
        'message': '服务正常运行',
        'ths_session_ready': data_fetcher.is_ready()
    })


@app.route('/api/ths-status', methods=['GET'])
def ths_status():
    """获取同花顺会话状态"""
    return jsonify({
        'success': True,
        'data': {
            'session_ready': data_fetcher.is_ready(),
            'heartbeat_running': data_fetcher._heartbeat_running
        }
    })


@app.route('/api/dates', methods=['GET'])
def get_available_dates():
    """获取所有可用日期"""
    session = get_db_session()
    try:
        dates = session.query(LadderStats.trade_date).order_by(
            desc(LadderStats.trade_date)
        ).all()
        
        date_list = [d[0].strftime('%Y%m%d') for d in dates]
        
        return jsonify({
            'success': True,
            'data': date_list
        })
    finally:
        session.close()


@app.route('/api/data/<date_str>', methods=['GET'])
def get_data_by_date(date_str):
    """获取指定日期的完整数据（涨停股票列表+统计数据），如果没有数据则自动同步"""
    session = get_db_session()
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        # 检查日期是否是未来日期
        if trade_date > datetime.now().date():
            return jsonify({
                'success': False,
                'error': '无法获取未来日期的数据'
            }), 200
        
        # 检查是否有该日期的数据
        stocks = session.query(LimitUpStock).filter(
            LimitUpStock.trade_date == trade_date
        ).order_by(desc(LimitUpStock.seal_amount)).all()
        
        stats = session.query(LadderStats).filter(
            LadderStats.trade_date == trade_date
        ).first()
        
        now = datetime.now()
        is_today = trade_date == now.date()
        trading_start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if not stocks or not stats:
            if is_today and now < trading_start_time:
                yesterday_data = None
                try:
                    from trade_calendar import trade_calendar
                    prev_trading_days = trade_calendar.get_recent_trading_days(2, end_date=trade_date)
                    
                    if prev_trading_days and len(prev_trading_days) >= 2:
                        prev_date_str = prev_trading_days[1]
                        prev_date = datetime.strptime(prev_date_str, '%Y%m%d').date()
                        
                        prev_stocks = session.query(LimitUpStock).filter(
                            LimitUpStock.trade_date == prev_date
                        ).all()
                        
                        if prev_stocks:
                            max_level = 0
                            for stock in prev_stocks:
                                level = min(stock.continuous_days, 8)
                                if level > max_level:
                                    max_level = level
                            
                            level_labels = {
                                1: "首板", 2: "2连板", 3: "3连板", 4: "4连板",
                                5: "5连板", 6: "6连板", 7: "7连板", 8: "8连板及以上"
                            }
                            
                            yesterday_data = {
                                'date': prev_date_str,
                                'max_level': max_level,
                                'label': level_labels.get(max_level, f"{max_level}连板")
                            }
                except Exception as e:
                    print(f"获取昨天数据失败: {e}")
                
                return jsonify({
                    'success': True,
                    'data': {
                        'ladder': [],
                        'statistics': {
                            'total_count': 0,
                            'first_board': 0,
                            'second_board': 0,
                            'third_board': 0,
                            'fourth_board': 0,
                            'fifth_plus_board': 0
                        },
                        'yesterday': yesterday_data
                    },
                    'message': '今日暂无数据'
                }), 200
            else:
                print(f"日期 {date_str} 没有数据，触发同步...")
                from fetch_data import LimitUpFetcher
                
                fetcher = LimitUpFetcher(data_fetcher=data_fetcher)
                success = fetcher.fetch_and_save(date_str)
                
                if success:
                    stocks = session.query(LimitUpStock).filter(
                        LimitUpStock.trade_date == trade_date
                    ).order_by(desc(LimitUpStock.seal_amount)).all()
                    
                    stats = session.query(LadderStats).filter(
                        LadderStats.trade_date == trade_date
                    ).first()
                    
                    print(f"日期 {date_str} 数据同步成功，获取到 {len(stocks)} 只股票")
                else:
                    print(f"日期 {date_str} 数据同步失败")
                    return jsonify({
                        'success': False,
                        'error': '该日期暂无涨停股票数据'
                    }), 200
        
        ladder_dict = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}
        
        for stock in stocks:
            block_info = {}
            block_name = ""
            if stock.block:
                block_name = stock.block.block_name
                block_info = {
                    "change_rate": float(stock.block.change_rate) if stock.block.change_rate else 0.0,
                    "limit_up_num": stock.block.limit_up_num or 0,
                    "continuous_num": stock.block.continuous_plate_num or 0,
                    "high": stock.block.high or "",
                    "list_days": stock.block.list_days or 0,
                    "high_stock_name": stock.block.high_stock_name or ""
                }
            
            stock_data = {
                "code": stock.stock_code,
                "name": stock.stock_name,
                "reason": stock.limit_up_reason or "未分类",
                "limit_up_time": stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else "",
                "limit_up_price": float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                "limit_up_type": stock.limit_up_type or "",
                "high_days": stock.high_days or "",
                "block_name": block_name,
                "block_info": block_info,
                "detail_reason": stock.ths_reason_info or "",
                "seal_amount": float(stock.seal_amount) if stock.seal_amount else 0.0,
                "seal_amount_wan": round(float(stock.seal_amount) / 10000, 2) if stock.seal_amount else 0.0,
                "continuous_days": stock.continuous_days,
                "sector": stock.sector or "未知",
                "change_percent": float(stock.change_percent) if stock.change_percent else 0.0,
                "turnover_rate": float(stock.turnover_rate) if stock.turnover_rate else 0.0,
                "is_high_stock": stock.is_high_stock or 0
            }
            
            days = stock.continuous_days
            level = min(days, 8)
            ladder_dict[level].append(stock_data)
        
        level_labels = {
            1: "首板", 2: "2连板", 3: "3连板", 4: "4连板",
            5: "5连板", 6: "6连板", 7: "7连板", 8: "8连板及以上"
        }
        
        ladder = []
        for level in sorted(ladder_dict.keys(), reverse=True):
            if ladder_dict[level]:
                ladder.append({
                    "level": level,
                    "label": level_labels[level],
                    "stocks": ladder_dict[level]
                })
        
        # 构建统计数据
        statistics = {
            'total_count': stats.total_count if stats else 0,
            'first_board': stats.first_board if stats else 0,
            'second_board': stats.second_board if stats else 0,
            'third_board': stats.third_board if stats else 0,
            'fourth_board': stats.fourth_board if stats else 0,
            'fifth_plus_board': (stats.fifth_board + stats.sixth_board + 
                               stats.seventh_board + stats.eighth_plus_board) if stats else 0
        }
        
        yesterday_data = None
        try:
            from trade_calendar import trade_calendar
            prev_trading_days = trade_calendar.get_recent_trading_days(2, end_date=trade_date)
            
            if prev_trading_days and len(prev_trading_days) >= 2:
                prev_date_str = prev_trading_days[1]
                
                prev_date = datetime.strptime(prev_date_str, '%Y%m%d').date()
                
                prev_stocks = session.query(LimitUpStock).filter(
                    LimitUpStock.trade_date == prev_date
                ).all()
                
                if prev_stocks:
                    max_level = 0
                    for stock in prev_stocks:
                        level = min(stock.continuous_days, 8)
                        if level > max_level:
                            max_level = level
                    
                    level_labels = {
                        1: "首板", 2: "2连板", 3: "3连板", 4: "4连板",
                        5: "5连板", 6: "6连板", 7: "7连板", 8: "8连板及以上"
                    }
                    
                    yesterday_data = {
                        'date': prev_date_str,
                        'max_level': max_level,
                        'label': level_labels.get(max_level, f"{max_level}连板")
                    }
        except Exception as e:
            print(f"获取昨天数据失败: {e}")
        
        return jsonify({
            'success': True,
            'data': {
                'ladder': ladder,
                'statistics': statistics,
                'yesterday': yesterday_data
            },
            'date': date_str
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    finally:
        session.close()


@app.route('/api/ladder/<date_str>', methods=['GET'])
def get_ladder_by_date(date_str):
    """获取指定日期的连板天梯（已废弃，请使用 /api/data/<date_str>）"""
    session = get_db_session()
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        # 检查是否有该日期的数据
        stocks = session.query(LimitUpStock).filter(
            LimitUpStock.trade_date == trade_date
        ).order_by(desc(LimitUpStock.seal_amount)).all()
        
        # 如果没有数据，触发同步
        if not stocks:
            print(f"日期 {date_str} 没有数据，触发同步...")
            from fetch_data import LimitUpFetcher
            
            fetcher = LimitUpFetcher(data_fetcher=data_fetcher)
            success = fetcher.fetch_and_save(date_str)
            
            if success:
                # 重新查询数据
                stocks = session.query(LimitUpStock).filter(
                    LimitUpStock.trade_date == trade_date
                ).order_by(desc(LimitUpStock.seal_amount)).all()
                print(f"日期 {date_str} 数据同步成功，获取到 {len(stocks)} 只股票")
            else:
                print(f"日期 {date_str} 数据同步失败")
        
        ladder_dict = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}
        
        for stock in stocks:
            stock_data = {
                "code": stock.stock_code,
                "name": stock.stock_name,
                "reason": stock.limit_up_reason or "未分类",
                "limit_up_time": stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else "",
                "limit_up_price": float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                "limit_up_type": stock.limit_up_type or "",
                "high_days": stock.high_days or "",
                "block_name": stock.ths_board or "",
                "detail_reason": stock.ths_reason_info or "",
                "seal_amount": float(stock.seal_amount) if stock.seal_amount else 0.0,
                "seal_amount_wan": round(float(stock.seal_amount) / 10000, 2) if stock.seal_amount else 0.0,
                "continuous_days": stock.continuous_days,
                "sector": stock.sector or "未知",
                "change_percent": float(stock.change_percent) if stock.change_percent else 0.0,
                "turnover_rate": float(stock.turnover_rate) if stock.turnover_rate else 0.0,
                "is_high_stock": stock.is_high_stock or 0
            }
            
            days = stock.continuous_days
            level = min(days, 8)
            ladder_dict[level].append(stock_data)
        
        level_labels = {
            1: "首板", 2: "2连板", 3: "3连板", 4: "4连板",
            5: "5连板", 6: "6连板", 7: "7连板", 8: "8连板及以上"
        }
        
        ladder = []
        for level in sorted(ladder_dict.keys(), reverse=True):
            if ladder_dict[level]:
                ladder.append({
                    "level": level,
                    "label": level_labels[level],
                    "stocks": ladder_dict[level]
                })
        
        return jsonify({
            'success': True,
            'data': ladder,
            'date': date_str
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    finally:
        session.close()


@app.route('/api/statistics/<date_str>', methods=['GET'])
def get_statistics(date_str):
    """获取指定日期的统计数据（已废弃，请使用 /api/data/<date_str>）"""
    session = get_db_session()
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        stats = session.query(LadderStats).filter(
            LadderStats.trade_date == trade_date
        ).first()
        
        if not stats:
            return jsonify({
                'success': False,
                'error': '数据不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'total_count': stats.total_count,
                'first_board': stats.first_board,
                'second_board': stats.second_board,
                'third_board': stats.third_board,
                'fourth_board': stats.fourth_board,
                'fifth_plus_board': stats.fifth_board + stats.sixth_board + 
                                   stats.seventh_board + stats.eighth_plus_board
            }
        })
    finally:
        session.close()



@app.route('/api/latest', methods=['GET'])
def get_latest_date():
    """获取最近一个交易日（根据当前日期计算）"""
    from trade_calendar import trade_calendar
    
    try:
        trading_days = trade_calendar.get_recent_trading_days(1)
        
        if not trading_days:
            return jsonify({
                'success': False,
                'error': '无法获取交易日'
            }), 500
        
        latest_date = trading_days[0]
        
        return jsonify({
            'success': True,
            'data': latest_date
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/adjacent-trading-days/<date_str>', methods=['GET'])
def get_adjacent_trading_days(date_str):
    """获取指定日期前后一个月的交易日列表"""
    from trade_calendar import trade_calendar
    from datetime import datetime, timedelta
    
    try:
        date = datetime.strptime(date_str, '%Y%m%d').date()
        today = datetime.now().date()
        
        start_date = date - timedelta(days=31)
        end_date = min(date + timedelta(days=31), today)
        
        trading_days = trade_calendar.get_trading_days(start_date, end_date)
        
        prev_date = None
        next_date = None
        prev_days = []
        next_days = []
        
        current_idx = -1
        for i, d in enumerate(trading_days):
            if d == date_str:
                current_idx = i
                break
        
        if current_idx >= 0:
            if current_idx > 0:
                prev_date = trading_days[current_idx - 1]
                prev_days = trading_days[:current_idx]
            if current_idx < len(trading_days) - 1:
                next_date = trading_days[current_idx + 1]
                next_days = trading_days[current_idx + 1:]
        else:
            for i, d in enumerate(trading_days):
                if d < date_str:
                    prev_days.append(d)
                else:
                    next_days.append(d)
            
            if prev_days:
                prev_date = prev_days[-1]
            if next_days:
                next_date = next_days[0]
        
        is_trading_day = trade_calendar.is_trading_day(date)
        
        return jsonify({
            'success': True,
            'data': {
                'prev': prev_date,
                'next': next_date,
                'prev_days': prev_days,
                'next_days': next_days,
                'is_trading_day': is_trading_day
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """刷新数据（重新爬取指定日期数据）"""
    from fetch_data import LimitUpFetcher
    from flask import request
    
    try:
        data = request.get_json()
        date_str = data.get('date')
        
        if not date_str:
            return jsonify({
                'success': False,
                'error': '请提供日期参数'
            }), 400
        
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        if trade_date > datetime.now().date():
            return jsonify({
                'success': False,
                'error': '无法获取未来日期的数据'
            }), 200
        
        fetcher = LimitUpFetcher(data_fetcher=data_fetcher)
        
        success = fetcher.fetch_and_save(date_str)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'数据刷新成功：{date_str}',
                'date': date_str
            })
        else:
            return jsonify({
                'success': False,
                'error': '该日期暂无涨停股票数据'
            }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/wencai/breakout/<date_str>', methods=['GET'])
def wencai_breakout(date_str):
    """问财查询：断板日突破120日高点的股票"""
    from wencai_fetcher import wencai_fetcher
    from flask import request
    
    try:
        cookie = request.args.get('cookie', '')
        stocks = wencai_fetcher.get_breakout_stocks(date_str, cookie)
        
        if stocks is None:
            return jsonify({
                'success': False,
                'error': '问财查询失败'
            }), 500
        
        return jsonify({
            'success': True,
            'data': stocks,
            'count': len(stocks)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/wencai/query', methods=['POST'])
def wencai_query():
    """问财自定义查询"""
    from wencai_fetcher import wencai_fetcher
    from flask import request
    
    try:
        data = request.get_json()
        query = data.get('query')
        cookie = data.get('cookie', '')
        
        if not query:
            return jsonify({
                'success': False,
                'error': '请提供查询语句'
            }), 400
        
        result = wencai_fetcher.custom_query(query, cookie)
        
        if result is None:
            return jsonify({
                'success': False,
                'error': '问财查询失败'
            }), 500
        
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/wencai/strategies', methods=['GET'])
def get_wencai_strategies():
    """获取用户的问财策略列表"""
    session = get_db_session()
    
    try:
        user_uid = request.headers.get('X-User-Uid')
        
        if not user_uid:
            return jsonify({
                'success': False,
                'error': '未授权'
            }), 401
        
        strategies = session.query(UserWencaiStrategy).filter(
            UserWencaiStrategy.user_id == user_uid
        ).order_by(UserWencaiStrategy.is_default.desc(), UserWencaiStrategy.created_at.asc()).all()
        
        result = []
        for strategy in strategies:
            result.append({
                'id': strategy.id,
                'strategy_name': strategy.strategy_name,
                'strategy_type': strategy.strategy_type,
                'query_template': strategy.query_template,
                'description': strategy.description,
                'is_default': strategy.is_default,
                'created_at': strategy.created_at.isoformat() if strategy.created_at else None,
                'updated_at': strategy.updated_at.isoformat() if strategy.updated_at else None
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/wencai/strategies', methods=['POST'])
def create_wencai_strategy():
    """创建新的问财策略"""
    session = get_db_session()
    
    try:
        user_uid = request.headers.get('X-User-Uid')
        
        if not user_uid:
            return jsonify({
                'success': False,
                'error': '未授权'
            }), 401
        
        data = request.get_json()
        strategy_name = data.get('strategy_name')
        strategy_type = data.get('strategy_type', 'custom')
        query_template = data.get('query_template')
        description = data.get('description', '')
        is_default = data.get('is_default', 0)
        
        if not strategy_name or not query_template:
            return jsonify({
                'success': False,
                'error': '策略名称和查询模板不能为空'
            }), 400
        
        if is_default:
            session.query(UserWencaiStrategy).filter(
                UserWencaiStrategy.user_id == user_uid,
                UserWencaiStrategy.is_default == 1
            ).update({'is_default': 0})
        
        strategy = UserWencaiStrategy(
            user_id=user_uid,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
            query_template=query_template,
            description=description,
            is_default=is_default
        )
        
        session.add(strategy)
        session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'id': strategy.id,
                'strategy_name': strategy.strategy_name,
                'strategy_type': strategy.strategy_type,
                'query_template': strategy.query_template,
                'description': strategy.description,
                'is_default': strategy.is_default
            }
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/wencai/strategies/<int:strategy_id>', methods=['PUT'])
def update_wencai_strategy(strategy_id):
    """更新问财策略"""
    session = get_db_session()
    
    try:
        user_uid = request.headers.get('X-User-Uid')
        
        if not user_uid:
            return jsonify({
                'success': False,
                'error': '未授权'
            }), 401
        
        strategy = session.query(UserWencaiStrategy).filter(
            UserWencaiStrategy.id == strategy_id,
            UserWencaiStrategy.user_id == user_uid
        ).first()
        
        if not strategy:
            return jsonify({
                'success': False,
                'error': '策略不存在'
            }), 404
        
        data = request.get_json()
        
        if 'strategy_name' in data:
            strategy.strategy_name = data['strategy_name']
        if 'strategy_type' in data:
            strategy.strategy_type = data['strategy_type']
        if 'query_template' in data:
            strategy.query_template = data['query_template']
        if 'description' in data:
            strategy.description = data['description']
        if 'is_default' in data:
            if data['is_default']:
                session.query(UserWencaiStrategy).filter(
                    UserWencaiStrategy.user_id == user_uid,
                    UserWencaiStrategy.is_default == 1
                ).update({'is_default': 0})
            strategy.is_default = data['is_default']
        
        session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'id': strategy.id,
                'strategy_name': strategy.strategy_name,
                'strategy_type': strategy.strategy_type,
                'query_template': strategy.query_template,
                'description': strategy.description,
                'is_default': strategy.is_default
            }
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/wencai/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_wencai_strategy(strategy_id):
    """删除问财策略"""
    session = get_db_session()
    
    try:
        user_uid = request.headers.get('X-User-Uid')
        
        if not user_uid:
            return jsonify({
                'success': False,
                'error': '未授权'
            }), 401
        
        strategy = session.query(UserWencaiStrategy).filter(
            UserWencaiStrategy.id == strategy_id,
            UserWencaiStrategy.user_id == user_uid
        ).first()
        
        if not strategy:
            return jsonify({
                'success': False,
                'error': '策略不存在'
            }), 404
        
        session.delete(strategy)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': '策略已删除'
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/block-strength/<date_str>', methods=['GET'])
def get_block_strength(date_str):
    """获取指定日期的板块强度（按涨停数量排序）"""
    session = get_db_session()
    
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        # 查询指定日期的板块数据，按涨停数量降序排序
        blocks = session.query(Block).filter(
            Block.trade_date == trade_date
        ).order_by(Block.limit_up_num.desc()).all()
        
        if not blocks:
            return jsonify({
                'success': True,
                'data': {
                    'date': date_str,
                    'blocks': []
                }
            })
        
        result = []
        for index, block in enumerate(blocks, 1):
            result.append({
                'block_code': block.block_code,
                'block_name': block.block_name,
                'limit_up_num': block.limit_up_num,
                'continuous_plate_num': block.continuous_plate_num,
                'change_rate': float(block.change_rate) if block.change_rate else 0,
                'high': block.high,
                'high_num': block.high_num,
                'rank': index,
                'high_stock_code': block.high_stock_code,
                'high_stock_name': block.high_stock_name,
            })
        
        return jsonify({
            'success': True,
            'data': {
                'date': date_str,
                'blocks': result
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/block-strength/continuous', methods=['GET'])
def get_block_strength_continuous():
    """获取连续三天的板块强度（昨日、今日、明日）"""
    from trade_calendar import trade_calendar

    session = get_db_session()

    try:
        # 获取传入的日期参数，默认为数据库最新日期
        date_str = request.args.get('date')
        if date_str:
            try:
                base_date = datetime.strptime(date_str, '%Y%m%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': '日期格式错误，请使用YYYYMMDD格式'
                }), 400
        else:
            # 没有传入日期，使用数据库最新日期
            latest_block = session.query(Block).order_by(Block.trade_date.desc()).first()
            if not latest_block:
                return jsonify({
                    'success': True,
                    'data': {}
                })
            base_date = latest_block.trade_date

        target_days = []

        yesterday = trade_calendar.get_prev_trading_day(base_date)
        if yesterday:
            target_days.append(('yesterday', yesterday))

        target_days.append(('today', base_date))

        tomorrow = trade_calendar.get_next_trading_day(base_date)
        if tomorrow:
            target_days.append(('tomorrow', tomorrow))

        result_data = {}

        for label, trade_date in target_days:
            date_str = trade_date.strftime('%Y%m%d')
            blocks = session.query(Block).filter(
                Block.trade_date == trade_date
            ).order_by(Block.limit_up_num.desc()).limit(20).all()

            block_list = []
            for index, block in enumerate(blocks, 1):
                block_list.append({
                    'block_code': block.block_code,
                    'block_name': block.block_name,
                    'limit_up_num': block.limit_up_num,
                    'continuous_plate_num': block.continuous_plate_num,
                    'change_rate': float(block.change_rate) if block.change_rate else 0,
                    'high': block.high,
                    'high_num': block.high_num,
                    'rank': index,
                    'high_stock_code': block.high_stock_code,
                    'high_stock_name': block.high_stock_name,
                })

            result_data[label] = {
                'date': date_str,
                'blocks': block_list
            }

        return jsonify({
            'success': True,
            'data': result_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/stock/block', methods=['PUT'])
def update_stock_block():
    """更新股票的所属板块"""
    session = get_db_session()
    
    try:
        data = request.json
        stock_code = data.get('stock_code')
        trade_date_str = data.get('trade_date')
        block_name = data.get('block_name')
        
        if not stock_code or not trade_date_str or not block_name:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
        
        # 查找股票记录
        stock = session.query(LimitUpStock).filter(
            LimitUpStock.stock_code == stock_code,
            LimitUpStock.trade_date == trade_date
        ).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '找不到股票记录'
            }), 404
        
        # 记录原板块ID
        old_block_id = stock.block_id
        
        # 查找新板块
        new_block = session.query(Block).filter(
            Block.block_name == block_name,
            Block.trade_date == trade_date
        ).first()
        
        if not new_block:
            return jsonify({
                'success': False,
                'error': '找不到板块记录'
            }), 404
        
        # 如果板块没有变化，直接返回
        if old_block_id == new_block.id:
            return jsonify({
                'success': True,
                'message': '板块未变更'
            })
        
        # 更新股票的板块
        stock.block_id = new_block.id
        
        # 处理原板块的龙头更新
        if old_block_id:
            old_block = session.query(Block).filter(Block.id == old_block_id).first()
            if old_block:
                # 清除原板块所有股票的龙头标记
                session.query(LimitUpStock).filter(
                    LimitUpStock.block_id == old_block_id
                ).update({'is_high_stock': 0})
                
                # 查找原板块中连板数最高的股票作为新龙头
                new_leader = session.query(LimitUpStock).filter(
                    LimitUpStock.block_id == old_block_id
                ).order_by(
                    LimitUpStock.continuous_days.desc(),
                    LimitUpStock.seal_amount.desc()
                ).first()
                
                if new_leader:
                    # 标记新龙头
                    new_leader.is_high_stock = 1
                    # 更新板块龙头信息
                    old_block.high_stock_code = new_leader.stock_code
                    old_block.high_stock_name = new_leader.stock_name
                else:
                    # 板块没有股票了，清空龙头信息
                    old_block.high_stock_code = None
                    old_block.high_stock_name = None
        
        # 处理新板块的龙头更新
        # 清除当前股票的龙头标记
        stock.is_high_stock = 0
        
        # 查找新板块当前的龙头
        current_leader = session.query(LimitUpStock).filter(
            LimitUpStock.block_id == new_block.id,
            LimitUpStock.is_high_stock == 1
        ).first()
        
        if current_leader:
            # 如果存在龙头，比较连板数
            if stock.continuous_days > current_leader.continuous_days:
                # 当前股票连板数更高，成为新龙头
                current_leader.is_high_stock = 0
                stock.is_high_stock = 1
                new_block.high_stock_code = stock.stock_code
                new_block.high_stock_name = stock.stock_name
            elif stock.continuous_days == current_leader.continuous_days:
                # 连板数相同，比较封单金额
                if (stock.seal_amount or 0) > (current_leader.seal_amount or 0):
                    current_leader.is_high_stock = 0
                    stock.is_high_stock = 1
                    new_block.high_stock_code = stock.stock_code
                    new_block.high_stock_name = stock.stock_name
        else:
            # 新板块没有龙头，查找连板数最高的股票
            potential_leader = session.query(LimitUpStock).filter(
                LimitUpStock.block_id == new_block.id
            ).order_by(
                LimitUpStock.continuous_days.desc(),
                LimitUpStock.seal_amount.desc()
            ).first()
            
            if potential_leader:
                # 标记为龙头
                potential_leader.is_high_stock = 1
                new_block.high_stock_code = potential_leader.stock_code
                new_block.high_stock_name = potential_leader.stock_name
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': '更新成功'
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """获取自选股列表（自动更新价格）"""
    session = get_db_session()
    
    try:
        user_id = request.headers.get('X-User-Uid')
        if not user_id:
            return jsonify({
                'success': False,
                'error': '未提供用户ID'
            }), 401
        
        watchlist = session.query(WatchlistStock).filter(
            WatchlistStock.user_id == user_id
        ).order_by(desc(WatchlistStock.created_at)).all()
        
        stock_codes = [stock.stock_code.split('.')[0] for stock in watchlist]
        
        quotes_dict = {}
        if stock_codes:
            sh_codes = [code for code in stock_codes if code.startswith('6')]
            sz_codes = [code for code in stock_codes if code.startswith(('0', '3'))]
            
            if sh_codes:
                try:
                    client = Quotes.factory(market=1)
                    quotes = client.quotes(symbol=sh_codes)
                    
                    if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                        for idx, row in quotes.iterrows():
                            code = row['code']
                            quotes_dict[code] = {
                                'price': float(row.get('price', 0) or 0),
                                'high': float(row.get('high', 0) or 0),
                                'low': float(row.get('low', 0) or 0),
                                'prev_close': float(row.get('last_close', 0) or 0),
                            }
                except Exception as e:
                    print(f"批量获取沪市实时行情失败: {e}")
            
            if sz_codes:
                try:
                    client = Quotes.factory(market=0)
                    quotes = client.quotes(symbol=sz_codes)
                    
                    if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                        for idx, row in quotes.iterrows():
                            code = row['code']
                            quotes_dict[code] = {
                                'price': float(row.get('price', 0) or 0),
                                'high': float(row.get('high', 0) or 0),
                                'low': float(row.get('low', 0) or 0),
                                'prev_close': float(row.get('last_close', 0) or 0),
                            }
                except Exception as e:
                    print(f"批量获取深市实时行情失败: {e}")
        
        result = []
        for stock in watchlist:
            stock_total_profit = session.query(func.sum(TradeRecord.profit)).filter(
                TradeRecord.user_id == user_id,
                TradeRecord.stock_code == stock.stock_code,
                TradeRecord.operation_type == '卖出',
                TradeRecord.profit.isnot(None)
            ).scalar() or 0
            
            buy_records = session.query(TradeRecord).filter(
                TradeRecord.user_id == user_id,
                TradeRecord.stock_code == stock.stock_code,
                TradeRecord.operation_type == '买入',
                TradeRecord.remaining_quantity > 0
            ).all()
            
            current_quantity = sum(r.remaining_quantity for r in buy_records)
            
            stock_code_num = stock.stock_code.split('.')[0]
            quote = quotes_dict.get(stock_code_num)
            current_price = quote['price'] if quote else None
            prev_close = quote['prev_close'] if quote else None
            
            if current_price and prev_close and prev_close > 0:
                day_change_pct = (current_price - prev_close) / prev_close * 100
            else:
                day_change_pct = None
            
            if current_quantity > 0:
                total_cost = sum(float(r.price) * r.remaining_quantity for r in buy_records)
                avg_buy_price = total_cost / current_quantity
                
                if current_price:
                    position_profit = (current_price - avg_buy_price) * current_quantity
                    position_profit_ratio = (current_price - avg_buy_price) / avg_buy_price
                else:
                    position_profit = None
                    position_profit_ratio = None
                
                position_status = '持仓'
                buy_date = min(r.operation_date for r in buy_records)
            else:
                position_profit = None
                position_profit_ratio = None
                position_status = '空仓'
                avg_buy_price = None
                buy_date = None
            
            result.append({
                'id': stock.id,
                'stock_code': stock.stock_code,
                'stock_name': stock.stock_name,
                'add_date': stock.add_date.strftime('%Y%m%d') if stock.add_date else '',
                'add_price': float(stock.add_price) if stock.add_price else None,
                'current_price': float(current_price) if current_price else None,
                'day_change_pct': float(day_change_pct) if day_change_pct is not None else None,
                'add_reason': stock.add_reason or '',
                'source': stock.source or '',
                'add_type': stock.add_type or 'manual',
                'limit_up_reason_category': stock.limit_up_reason_category or '',
                'position_status': position_status,
                'buy_price': float(avg_buy_price) if avg_buy_price else None,
                'buy_date': buy_date.strftime('%Y-%m-%d') if buy_date else None,
                'buy_quantity': current_quantity,
                'position_profit': float(position_profit) if position_profit is not None else None,
                'position_profit_ratio': float(position_profit_ratio) if position_profit_ratio is not None else None,
                'total_profit': float(stock_total_profit),
                'created_at': stock.created_at.strftime('%Y-%m-%d %H:%M:%S') if stock.created_at else ''
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/watchlist', methods=['POST'])
def add_to_watchlist():
    """添加股票到自选"""
    session = get_db_session()
    
    try:
        user_id = request.headers.get('X-User-Uid')
        if not user_id:
            return jsonify({
                'success': False,
                'error': '未提供用户ID'
            }), 401
        
        data = request.json
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        add_date_str = data.get('add_date')
        add_price = data.get('add_price')
        add_reason = data.get('add_reason', '')
        source = data.get('source', 'wencai')
        add_type = data.get('add_type', 'manual')
        limit_up_reason_category = data.get('limit_up_reason_category', '')
        
        if not stock_code or not stock_name or not add_date_str:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        add_date = datetime.strptime(add_date_str, '%Y%m%d').date()
        
        existing = session.query(WatchlistStock).filter(
            WatchlistStock.user_id == user_id,
            WatchlistStock.stock_code == stock_code
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': '该股票已在自选列表中'
            }), 400
        
        watchlist_stock = WatchlistStock(
            user_id=user_id,
            stock_code=stock_code,
            stock_name=stock_name,
            add_date=add_date,
            add_price=add_price,
            add_reason=add_reason,
            source=source,
            add_type=add_type,
            limit_up_reason_category=limit_up_reason_category
        )
        
        session.add(watchlist_stock)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': '添加成功'
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/watchlist/<stock_code>', methods=['DELETE'])
def remove_from_watchlist(stock_code):
    """从自选中删除股票"""
    session = get_db_session()
    
    try:
        user_id = request.headers.get('X-User-Uid')
        if not user_id:
            return jsonify({
                'success': False,
                'error': '未提供用户ID'
            }), 401
        
        stock = session.query(WatchlistStock).filter(
            WatchlistStock.user_id == user_id,
            WatchlistStock.stock_code == stock_code
        ).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '股票不在自选列表中'
            }), 404
        
        buy_records = session.query(TradeRecord).filter(
            TradeRecord.user_id == user_id,
            TradeRecord.stock_code == stock_code,
            TradeRecord.operation_type == '买入',
            TradeRecord.remaining_quantity > 0
        ).all()
        
        if buy_records:
            return jsonify({
                'success': False,
                'error': '该股票正在持仓中，请先卖出后再删除'
            }), 400
        
        session.delete(stock)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/watchlist/update-prices', methods=['POST'])
def update_watchlist_prices():
    """更新自选股价格（已废弃，价格在获取列表时实时更新）"""
    return jsonify({
        'success': True,
        'message': '价格已在获取列表时实时更新，无需手动刷新'
    })


@app.route('/api/stock/search', methods=['GET'])
def search_stock():
    """搜索股票"""
    try:
        keyword = request.args.get('keyword', '').strip()
        
        if not keyword:
            return jsonify({
                'success': True,
                'data': []
            })
        
        import requests as req_module
        from urllib.parse import quote
        
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": keyword,
            "type": "14",
            "token": "D43BF722C8E33BCE90EFB9D8653D9A5B",
            "count": 20,
            "cb": ""
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        
        response = req_module.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'搜索失败，状态码: {response.status_code}'
            }), 500
        
        try:
            text = response.text.strip()
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1]
            data = json.loads(text)
        except Exception as json_err:
            return jsonify({
                'success': False,
                'error': '搜索接口返回数据格式错误'
            }), 500
        
        stocks = []
        if data and 'QuotationCodeTable' in data:
            table_data = data['QuotationCodeTable']
            if table_data and 'Data' in table_data and isinstance(table_data['Data'], list):
                for item in table_data['Data']:
                    code = item.get('Code', '')
                    name = item.get('Name', '')
                    market_code = item.get('MktNum', '')
                    
                    if code and name:
                        stocks.append({
                            'code': code,
                            'name': name,
                            'market_code': market_code,
                            'display': f"{code} {name}"
                        })
        
        return jsonify({
            'success': True,
            'data': stocks
        })
        
    except Exception as e:
        print(f"搜索股票异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stock/quote/<stock_code>', methods=['GET'])
def get_stock_quote(stock_code):
    """获取单只股票的实时行情"""
    try:
        quote = data_fetcher.get_realtime_quote(stock_code)
        
        if quote:
            return jsonify({
                'success': True,
                'data': quote
            })
        else:
            return jsonify({
                'success': False,
                'error': '未找到该股票'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/watchlist/buy', methods=['POST'])
def buy_stock():
    """买入股票"""
    session = get_db_session()
    
    try:
        user_id = request.headers.get('X-User-Uid')
        if not user_id:
            return jsonify({
                'success': False,
                'error': '未提供用户ID'
            }), 401
        
        data = request.json
        stock_code = data.get('stock_code')
        buy_price = data.get('buy_price')
        buy_quantity = data.get('buy_quantity', 100)
        
        if not stock_code or not buy_price:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        stock = session.query(WatchlistStock).filter_by(
            user_id=user_id,
            stock_code=stock_code
        ).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '股票不在自选列表中'
            }), 404
        
        trade_record = TradeRecord(
            user_id=user_id,
            stock_code=stock_code,
            stock_name=stock.stock_name,
            operation_type='买入',
            price=buy_price,
            quantity=buy_quantity,
            remaining_quantity=buy_quantity,
            amount=buy_price * buy_quantity,
            operation_date=datetime.now()
        )
        session.add(trade_record)
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功买入 {stock.stock_name}'
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/watchlist/sell', methods=['POST'])
def sell_stock():
    """卖出股票"""
    session = get_db_session()
    
    try:
        user_id = request.headers.get('X-User-Uid')
        if not user_id:
            return jsonify({
                'success': False,
                'error': '未提供用户ID'
            }), 401
        
        data = request.json
        stock_code = data.get('stock_code')
        sell_price = data.get('sell_price')
        sell_quantity = data.get('sell_quantity')
        
        if not stock_code or not sell_price:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        stock = session.query(WatchlistStock).filter_by(
            user_id=user_id,
            stock_code=stock_code
        ).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '股票不在自选列表中'
            }), 404
        
        buy_records = session.query(TradeRecord).filter(
            TradeRecord.user_id == user_id,
            TradeRecord.stock_code == stock_code,
            TradeRecord.operation_type == '买入',
            TradeRecord.remaining_quantity > 0
        ).order_by(TradeRecord.operation_date).all()
        
        if not buy_records:
            return jsonify({
                'success': False,
                'error': '该股票未持仓，无法卖出'
            }), 400
        
        total_quantity = sum(r.remaining_quantity for r in buy_records)
        
        if not sell_quantity:
            sell_quantity = total_quantity
        
        if sell_quantity > total_quantity:
            return jsonify({
                'success': False,
                'error': f'卖出数量不能超过持仓数量（{total_quantity}股）'
            }), 400
        
        total_profit = 0
        remaining_to_sell = sell_quantity
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
            
            record.remaining_quantity -= sell_from_this_record
            remaining_to_sell -= sell_from_this_record
        
        avg_buy_price = total_buy_cost / total_sell_quantity if total_sell_quantity > 0 else 0
        profit_ratio = (sell_price - avg_buy_price) / avg_buy_price if avg_buy_price > 0 else 0
        
        trade_record = TradeRecord(
            user_id=user_id,
            stock_code=stock_code,
            stock_name=stock.stock_name,
            operation_type='卖出',
            price=sell_price,
            buy_price=avg_buy_price,
            quantity=sell_quantity,
            remaining_quantity=0,
            amount=sell_price * sell_quantity,
            profit=total_profit,
            profit_ratio=profit_ratio,
            operation_date=datetime.now()
        )
        session.add(trade_record)
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功卖出 {stock.stock_name} {sell_quantity}股，盈亏: {total_profit:.2f}元'
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/trade-records', methods=['GET'])
def get_trade_records():
    """获取交易记录"""
    session = get_db_session()
    
    try:
        user_id = request.headers.get('X-User-Uid')
        if not user_id:
            return jsonify({
                'success': False,
                'error': '未提供用户ID'
            }), 401
        
        records = session.query(TradeRecord).filter(
            TradeRecord.user_id == user_id
        ).order_by(TradeRecord.operation_date.desc()).all()
        
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
                'amount': float(record.amount) if record.amount else None,
                'profit': float(record.profit) if record.profit is not None else None,
                'profit_ratio': float(record.profit_ratio) if record.profit_ratio is not None else None,
                'operation_date': record.operation_date.strftime('%Y-%m-%d %H:%M:%S') if record.operation_date else '',
                'notes': record.notes or ''
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/stock/kline/<stock_code>', methods=['GET'])
def get_stock_kline(stock_code):
    """获取股票K线数据"""
    try:
        days = request.args.get('days', 60, type=int)
        
        stock_code_clean = stock_code.split('.')[0]
        
        kline_data = data_fetcher.get_stock_kline(stock_code_clean, days)
        
        if kline_data:
            return jsonify({
                'success': True,
                'data': kline_data
            })
        else:
            return jsonify({
                'success': False,
                'error': '未找到K线数据'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stock/intraday/<stock_code>', methods=['GET'])
def get_stock_intraday(stock_code):
    """获取股票当日分时数据和实时行情"""
    try:
        stock_code_clean = stock_code.split('.')[0]
        
        intraday_data = data_fetcher.get_stock_intraday(stock_code_clean)
        quote_data = data_fetcher.get_realtime_quote(stock_code_clean)
        
        is_in_watchlist = False
        user_id = request.headers.get('X-User-Uid')
        if user_id:
            session = get_db_session()
            try:
                existing = session.query(WatchlistStock).filter(
                    WatchlistStock.user_id == user_id,
                    WatchlistStock.stock_code.like(f'{stock_code_clean}%')
                ).first()
                is_in_watchlist = existing is not None
            finally:
                session.close()
        
        if intraday_data:
            return jsonify({
                'success': True,
                'data': {
                    **intraday_data,
                    'quote': quote_data,
                    'is_in_watchlist': is_in_watchlist
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '未找到分时数据或今日无交易数据'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_stock_code_by_name(keyword):
    """根据股票名称或代码获取股票代码"""
    if not keyword:
        return ''
    
    if keyword.isdigit() or (keyword[0].isdigit() and '.' in keyword):
        return keyword
    
    try:
        import requests as req_module
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": keyword,
            "type": "14",
            "token": "D43BF722C8E33BCE90EFB9D8653D9A5B",
            "count": 1,
            "cb": ""
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
        }
        response = req_module.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            text = response.text.strip()
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1]
            data = json.loads(text)
            quotation_data = data.get('QuotationCodeTable', {})
            if quotation_data.get('Data') and len(quotation_data['Data']) > 0:
                return quotation_data['Data'][0].get('Code', '')
    except Exception as e:
        print(f"搜索股票代码失败: {e}")
    
    return keyword


@app.route('/api/reports', methods=['GET'])
def get_reports():
    """获取研报列表"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 50, type=int)
        stock_code = request.args.get('code', '')
        
        if stock_code:
            stock_code = get_stock_code_by_name(stock_code)
        
        result = data_fetcher.get_reports(page, page_size, stock_code)
        
        if result:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': '获取研报数据失败'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stock/analyze/<stock_code>', methods=['GET'])
def analyze_limit_up_reason(stock_code):
    """
    分析涨停原因，提取炒作逻辑、关联板块和买入推荐指数
    
    Args:
        stock_code: 股票代码
        force: 是否强制重新分析（跳过缓存）
        date: 可选，指定日期（YYYYMMDD格式），如果不指定则查询最近一次涨停记录
        
    Returns:
        分析结果
    """
    force = request.args.get('force', 'false').lower() == 'true'
    date_str = request.args.get('date', None)
    check_only = request.args.get('check_only', 'false').lower() == 'true'
    
    session = get_db_session()
    try:
        # 查询涨停记录
        if date_str:
            # 如果指定了日期，查询该日期的涨停记录
            try:
                trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            except:
                return jsonify({
                    'success': False,
                    'error': '日期格式错误，应为YYYYMMDD格式'
                }), 400
            
            stock = session.query(LimitUpStock).filter(
                LimitUpStock.stock_code == stock_code,
                LimitUpStock.trade_date == trade_date
            ).first()
        else:
            # 如果没有指定日期，查询最近一次涨停记录
            stock = session.query(LimitUpStock).filter(
                LimitUpStock.stock_code == stock_code
            ).order_by(desc(LimitUpStock.trade_date)).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '未找到该股票的涨停记录'
            }), 404
        
        # 提取stock数据，避免session关闭后无法访问
        stock_data = {
            'stock_code': stock.stock_code,
            'stock_name': stock.stock_name,
            'trade_date': stock.trade_date,
            'limit_up_reason': stock.limit_up_reason,
            'limit_up_price': stock.limit_up_price,
            'continuous_days': stock.continuous_days,
            'limit_up_time': stock.limit_up_time,
            'seal_amount': stock.seal_amount,
            'turnover_rate': stock.turnover_rate
        }
        
        # 检查是否已有缓存的分析结果
        cached_result = session.query(AIAnalysisResult).filter(
            AIAnalysisResult.stock_code == stock_code,
            AIAnalysisResult.trade_date == stock_data['trade_date']
        ).first()
        
        # 如果只是检查缓存，直接返回结果
        if check_only:
            if cached_result:
                analysis = json.loads(cached_result.analysis_result)
                return jsonify({
                    'success': True,
                    'has_cache': True,
                    'data': {
                        'stock_code': stock_data['stock_code'],
                        'stock_name': stock_data['stock_name'],
                        'trade_date': stock_data['trade_date'].strftime('%Y-%m-%d'),
                        'limit_up_reason': stock_data['limit_up_reason'],
                        'continuous_days': stock_data['continuous_days'],
                        'sectors': analysis.get('sectors', []),
                        'speculation_logic': analysis.get('speculation_logic', []),
                        'stock_attribute': analysis.get('stock_attribute', None),
                        'market_heat': analysis.get('market_heat', 0),
                        'recommendation_score': analysis.get('recommendation_score', 0),
                        'recommendation_reason': analysis.get('recommendation_reason', ''),
                        'analysis_summary': analysis.get('analysis_summary', ''),
                        'keywords': analysis.get('keywords', []),
                        'trading_advice': analysis.get('trading_advice', None),
                        'holding_advice': analysis.get('holding_advice', None)
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'has_cache': False
                })
        
        if cached_result and not force:
            print(f"从缓存读取 {stock_data['stock_name']}({stock_code}) {stock_data['trade_date']} 的分析结果")
            analysis = json.loads(cached_result.analysis_result)
            cached = True
        else:
            if force and cached_result:
                print(f"强制重新分析 {stock_data['stock_name']}({stock_code}) {stock_data['trade_date']}")
            else:
                print(f"缓存未命中,开始分析 {stock_data['stock_name']}({stock_code}) {stock_data['trade_date']}")
            
            cached = False
            
            # 初始化分析器
            analyzer = LimitUpReasonAnalyzer()
            
            # 使用大模型分析涨停原因
            analysis = analyzer.analyze_with_llm(
                stock_data['limit_up_reason'],
                stock_data['stock_code'],
                stock_data['stock_name'],
                stock_data['limit_up_price'],
                stock_data['continuous_days'],
                stock_data['limit_up_time'],
                stock_data['seal_amount'],
                stock_data['turnover_rate']
            )
            
            # 如果分析成功,保存到数据库
            if analysis and analysis.get('recommendation_score', 0) > 0:
                try:
                    if cached_result:
                        # 更新现有记录
                        cached_result.analysis_result = json.dumps(analysis, ensure_ascii=False)
                        cached_result.updated_at = datetime.now()
                        print(f"成功更新分析结果到数据库")
                    else:
                        # 创建新记录
                        new_result = AIAnalysisResult(
                            stock_code=stock_data['stock_code'],
                            stock_name=stock_data['stock_name'],
                            trade_date=stock_data['trade_date'],
                            analysis_result=json.dumps(analysis, ensure_ascii=False)
                        )
                        session.add(new_result)
                        print(f"成功保存分析结果到数据库")
                    session.commit()
                except Exception as e:
                    print(f"保存分析结果失败: {e}")
                    session.rollback()
        
        return jsonify({
            'success': True,
            'cached': cached,
            'data': {
                'stock_code': stock_data['stock_code'],
                'stock_name': stock_data['stock_name'],
                'trade_date': stock_data['trade_date'].strftime('%Y-%m-%d'),
                'limit_up_reason': stock_data['limit_up_reason'],
                'continuous_days': stock_data['continuous_days'],
                'sectors': analysis.get('sectors', []),
                'speculation_logic': analysis.get('speculation_logic', []),
                'stock_attribute': analysis.get('stock_attribute', None),
                'market_heat': analysis.get('market_heat', 0),
                'recommendation_score': analysis.get('recommendation_score', 0),
                'recommendation_reason': analysis.get('recommendation_reason', ''),
                'analysis_summary': analysis.get('analysis_summary', ''),
                'keywords': analysis.get('keywords', []),
                'trading_advice': analysis.get('trading_advice', None),
                'holding_advice': analysis.get('holding_advice', None)
            }
        })
        
    except Exception as e:
        print(f"分析涨停原因失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    import hashlib
    import uuid as uuid_lib
    
    session = get_db_session()
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        nickname = data.get('nickname', username)
        
        if not username or not email or not password:
            return jsonify({
                'success': False,
                'error': '用户名、邮箱和密码不能为空'
            }), 400
        
        existing_user = session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return jsonify({
                'success': False,
                'error': '用户名或邮箱已存在'
            }), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = User(
            uid=str(uuid_lib.uuid4()),
            username=username,
            email=email,
            password_hash=password_hash,
            nickname=nickname
        )
        
        session.add(user)
        session.commit()
        
        send_welcome_email_to_user(email, username)
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': {
                'uid': user.uid,
                'username': user.username,
                'email': user.email,
                'nickname': user.nickname
            }
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    import hashlib
    import secrets
    
    session = get_db_session()
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': '用户名和密码不能为空'
            }), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = session.query(User).filter(
            User.username == username,
            User.password_hash == password_hash
        ).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': '用户名或密码错误'
            }), 401
        
        user.last_login = datetime.now()
        user.login_count = (user.login_count or 0) + 1
        session.commit()
        
        token = secrets.token_hex(32)
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'token': token,
                'user': {
                    'uid': user.uid,
                    'username': user.username,
                    'email': user.email,
                    'nickname': user.nickname,
                    'avatar': user.avatar
                }
            }
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/auth/guest', methods=['POST'])
def guest_login():
    """访客登录"""
    import uuid as uuid_lib
    import secrets
    
    session = get_db_session()
    try:
        guest_user = session.query(User).filter(User.username == 'guest').first()
        
        if not guest_user:
            guest_user = User(
                uid=str(uuid_lib.uuid4()),
                username='guest',
                email='guest@yunque.ai',
                password_hash='',
                nickname='访客用户',
                role='guest'
            )
            session.add(guest_user)
            session.commit()
        
        guest_user.last_login = datetime.now()
        guest_user.login_count = (guest_user.login_count or 0) + 1
        session.commit()
        
        token = secrets.token_hex(32)
        
        return jsonify({
            'success': True,
            'message': '访客登录成功',
            'data': {
                'token': token,
                'user': {
                    'uid': guest_user.uid,
                    'username': guest_user.username,
                    'email': guest_user.email,
                    'nickname': guest_user.nickname,
                    'avatar': guest_user.avatar,
                    'role': 'guest'
                }
            }
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """获取当前登录用户信息"""
    session = get_db_session()
    try:
        uid = request.headers.get('X-User-Uid')

        if not uid:
            return jsonify({
                'success': False,
                'error': '未登录',
                'code': 'UNAUTHORIZED'
            }), 401

        user = session.query(User).filter(User.uid == uid).first()

        if not user:
            return jsonify({
                'success': False,
                'error': '用户不存在',
                'code': 'USER_NOT_FOUND'
            }), 404

        is_vip = False
        vip_status = 'expired'

        if user.is_vip == 1 and user.vip_expire_date:
            if user.vip_expire_date >= datetime.now().date():
                is_vip = True
                vip_status = 'active'
            else:
                vip_status = 'expired'

        settings = {}
        if user.settings:
            try:
                import json
                settings = json.loads(user.settings)
            except:
                settings = {}

        return jsonify({
            'success': True,
            'data': {
                'uid': user.uid,
                'username': user.username,
                'email': user.email,
                'nickname': user.nickname,
                'avatar': user.avatar,
                'role': user.role,
                'isVip': is_vip,
                'vipStatus': vip_status,
                'vipExpireDate': user.vip_expire_date.strftime('%Y-%m-%d') if user.vip_expire_date else None,
                'isActive': bool(user.is_active),
                'lastLogin': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
                'createdAt': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
                'settings': settings
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


def send_welcome_email_to_user(email, username):
    """发送欢迎邮件给用户"""
    try:
        mail_password = os.environ.get('MAIL_PASSWORD')
        if not mail_password:
            print(f"✗ 邮件服务未配置：缺少 MAIL_PASSWORD 环境变量")
            return False
        
        subject = '感谢您注册使用云雀AI涨停复盘智能体'
        
        html_content = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1890ff; text-align: center;">欢迎您，{username}！</h2>
            
            <p style="font-size: 16px; line-height: 1.6; color: #333;">
                感谢您注册使用云雀AI涨停复盘智能体！我们很高兴为您提供专业的股票分析工具。
            </p>
            
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1890ff; margin-top: 0;">🎯 产品主要能力</h3>
                <ul style="line-height: 1.8; color: #555;">
                    <li><strong>🤖 AI智能体分析</strong>：全链路AI智能分析，从数据采集到决策建议，智能体全程辅助</li>
                    <li><strong>涨停复盘</strong>：实时追踪涨停股票，深度分析涨停原因和板块联动</li>
                    <li><strong>连板天梯</strong>：可视化展示连板股票，把握市场情绪和热点</li>
                    <li><strong>板块强度</strong>：智能分析板块热度，识别强势板块和龙头股</li>
                    <li><strong>自选股管理</strong>：个性化自选股池，实时监控股票动态</li>
                    <li><strong>智能问答助手</strong>：基于AI技术的股票分析和投资问答助手</li>
                    <li><strong>数据统计</strong>：全面的市场数据统计和历史回溯</li>
                </ul>
            </div>
            
            <div style="background-color: #e6f7ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1890ff; margin-top: 0;">🤖 AI智能体特色功能</h3>
                <ul style="line-height: 1.8; color: #555;">
                    <li><strong>全链路AI分析</strong>：从行情监控、数据分析到投资建议，AI智能体全程参与</li>
                    <li><strong>智能体问答</strong>：随时向AI智能体咨询股票相关问题，获得专业解答</li>
                    <li><strong>自动化监控</strong>：AI智能体7x24小时监控市场动态，及时发现投资机会</li>
                    <li><strong>个性化推荐</strong>：基于您的投资偏好，智能体提供定制化建议</li>
                </ul>
            </div>
            
            <div style="background-color: #fff7e6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1890ff; margin-top: 0;">👥 适用客户</h3>
                <ul style="line-height: 1.8; color: #555;">
                    <li><strong>短线交易者</strong>：需要实时捕捉涨停板机会的投资者</li>
                    <li><strong>板块轮动投资者</strong>：关注板块联动和市场热点的交易者</li>
                    <li><strong>量化交易者</strong>：需要数据支持和统计分析的专业人士</li>
                    <li><strong>股票分析师</strong>：需要深度分析工具的研究人员</li>
                    <li><strong>个人投资者</strong>：希望提升投资决策水平的散户朋友</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://yunqueai.cloud/news" style="background-color: #1890ff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px;">立即开始使用</a>
            </div>
            
            <p style="font-size: 14px; color: #999; text-align: center; margin-top: 30px;">
                如有任何问题或需求建议，请随时联系我们：yunque.ai@qq.com
            </p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="font-size: 12px; color: #999; text-align: center;">
                此邮件由系统自动发送，如有建议或想法，您可直接回复
            </p>
        </div>
        '''
        
        msg = Message(
            subject=subject,
            recipients=[email],
            html=html_content
        )
        
        with mail.connect() as conn:
            conn.send(msg)
        
        print(f"✓ 已向用户 {username} ({email}) 发送欢迎邮件")
        return True
        
    except Exception as e:
        print(f"✗ 发送欢迎邮件失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@app.route('/api/admin/user-stats', methods=['GET'])
def get_user_stats():
    """获取用户统计信息（管理员接口）"""
    session = get_db_session()
    try:
        uid = request.headers.get('X-User-Uid')
        
        user = session.query(User).filter(User.uid == uid).first()
        
        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'error': '权限不足'
            }), 403
        
        total_users = session.query(func.count(User.uid)).scalar()
        
        online_threshold = datetime.now() - timedelta(minutes=5)
        online_count = session.query(func.count(User.uid)).filter(
            User.last_activity >= online_threshold
        ).scalar()
        
        users = session.query(User).all()
        
        user_list = []
        for u in users:
            is_online = u.last_activity and u.last_activity >= online_threshold
            user_list.append({
                'username': u.username,
                'email': u.email,
                'nickname': u.nickname,
                'role': u.role,
                'login_count': u.login_count or 0,
                'last_login': u.last_login.strftime('%Y-%m-%d %H:%M:%S') if u.last_login else None,
                'last_activity': u.last_activity.strftime('%Y-%m-%d %H:%M:%S') if u.last_activity else None,
                'is_online': is_online,
                'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S') if u.created_at else None
            })
        
        def sort_key(user):
            is_online = 0 if user['is_online'] else 1
            is_admin = 0 if user['role'] == 'admin' else 1
            is_guest = 1 if user['role'] == 'guest' else 0
            login_count = -(user['login_count'] or 0)
            return (is_guest, is_online, is_admin, login_count)
        
        user_list.sort(key=sort_key)
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'online_count': online_count,
                'users': user_list
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/admin/send-welcome-email', methods=['POST'])
def send_welcome_email():
    """发送欢迎邮件（管理员接口）"""
    session = get_db_session()
    try:
        uid = request.headers.get('X-User-Uid')
        
        user = session.query(User).filter(User.uid == uid).first()
        
        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'error': '权限不足'
            }), 403
        
        data = request.get_json()
        target_email = data.get('email')
        username = data.get('username', '用户')
        
        if not target_email:
            return jsonify({
                'success': False,
                'error': '邮箱地址不能为空'
            }), 400
        
        if send_welcome_email_to_user(target_email, username):
            return jsonify({
                'success': True,
                'message': f'已成功向 {target_email} 发送欢迎邮件'
            })
        else:
            return jsonify({
                'success': False,
                'error': '发送邮件失败，请检查邮件服务配置'
            }), 500
        
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'发送邮件失败：{str(e)}'
        }), 500
    finally:
        session.close()


@app.route('/api/admin/send-email', methods=['POST'])
def send_custom_email():
    """发送自定义邮件（管理员接口）"""
    session = get_db_session()
    try:
        uid = request.headers.get('X-User-Uid')
        
        user = session.query(User).filter(User.uid == uid).first()
        
        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'error': '权限不足'
            }), 403
        
        data = request.get_json()
        target_email = data.get('email')
        subject = data.get('subject')
        content = data.get('content')
        
        if not target_email:
            return jsonify({
                'success': False,
                'error': '邮箱地址不能为空'
            }), 400
        
        if not subject:
            return jsonify({
                'success': False,
                'error': '邮件主题不能为空'
            }), 400
        
        if not content:
            return jsonify({
                'success': False,
                'error': '邮件内容不能为空'
            }), 400
        
        mail_password = os.environ.get('MAIL_PASSWORD')
        if not mail_password:
            return jsonify({
                'success': False,
                'error': '邮件服务未配置：缺少 MAIL_PASSWORD 环境变量'
            }), 500
        
        msg = Message(
            subject=subject,
            recipients=[target_email],
            html=content
        )
        
        with mail.connect() as conn:
            conn.send(msg)
        
        print(f"✓ 已向 {target_email} 发送自定义邮件")
        return jsonify({
            'success': True,
            'message': f'已成功向 {target_email} 发送邮件'
        })
        
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'发送邮件失败：{str(e)}'
        }), 500
    finally:
        session.close()


@app.route('/api/auth/settings', methods=['PUT'])
def update_user_settings():
    """更新用户设置"""
    session = get_db_session()
    try:
        uid = request.headers.get('X-User-Uid')

        if not uid:
            return jsonify({
                'success': False,
                'error': '未登录',
                'code': 'UNAUTHORIZED'
            }), 401

        user = session.query(User).filter(User.uid == uid).first()

        if not user:
            return jsonify({
                'success': False,
                'error': '用户不存在',
                'code': 'USER_NOT_FOUND'
            }), 404

        import json
        data = request.json
        settings = data.get('settings', {})

        user.settings = json.dumps(settings)
        user.updated_at = datetime.now()
        session.commit()

        return jsonify({
            'success': True,
            'message': '设置更新成功',
            'data': {
                'settings': settings
            }
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/stock-diff/save', methods=['POST'])
def save_stock_diff():
    """
    保存股票对比结果
    
    请求体:
    {
        "trade_date": "20250512",
        "added": [
            {"code": "000001", "name": "平安银行", "level": 1, "limitUpTime": "09:30:00"}
        ],
        "removed": [
            {"code": "000002", "name": "万科A", "level": 2, "limitUpTime": "10:00:00"}
        ]
    }
    """
    session = get_db_session()
    try:
        data = request.json
        trade_date_str = data.get('trade_date')
        added_stocks = data.get('added', [])
        removed_stocks = data.get('removed', [])
        
        if not trade_date_str:
            return jsonify({
                'success': False,
                'error': '缺少交易日期参数'
            }), 400
        
        trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
        
        session.query(StockDiffRecord).filter(
            StockDiffRecord.trade_date == trade_date
        ).delete()
        
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
            session.bulk_save_objects(records)
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'保存成功，共{len(records)}条记录',
            'data': {
                'added_count': len(added_stocks),
                'removed_count': len(removed_stocks)
            }
        })
        
    except Exception as e:
        session.rollback()
        print(f"保存股票对比结果失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/stock-diff/load/<date_str>', methods=['GET'])
def load_stock_diff(date_str):
    """
    加载股票对比结果
    
    参数:
        date_str: 交易日期，格式为YYYYMMDD
    
    返回:
    {
        "success": true,
        "data": {
            "added": [...],
            "removed": [...]
        }
    }
    """
    session = get_db_session()
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        records = session.query(StockDiffRecord).filter(
            StockDiffRecord.trade_date == trade_date
        ).all()
        
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
        
        return jsonify({
            'success': True,
            'data': {
                'added': added,
                'removed': removed
            }
        })
        
    except Exception as e:
        print(f"加载股票对比结果失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/stock-diff/clear/<date_str>', methods=['DELETE'])
def clear_stock_diff(date_str):
    """
    清空指定日期的股票对比结果
    
    参数:
        date_str: 交易日期，格式为YYYYMMDD
    """
    session = get_db_session()
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        deleted_count = session.query(StockDiffRecord).filter(
            StockDiffRecord.trade_date == trade_date
        ).delete()
        
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已清空{deleted_count}条记录'
        })
        
    except Exception as e:
        session.rollback()
        print(f"清空股票对比结果失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/news/cls-telegraph', methods=['GET'])
def get_cls_telegraph():
    """
    获取财联社电报数据（加红的关键资讯）
    
    参数:
        force: 是否强制从财联社刷新，默认false
        last_ctime: 最后一条新闻的时间，用于分页加载历史数据
        limit: 每次加载数量，默认50
        load_from_api: 是否从财联社API加载历史数据，默认false
        keyword: 搜索关键词，用于搜索标题和内容
    
    返回:
    {
        "success": true,
        "data": [...],
        "has_more": true/false,
        "total": 总数据量
    }
    """
    try:
        force = request.args.get('force', 'false').lower() == 'true'
        last_ctime_str = request.args.get('last_ctime')
        limit = request.args.get('limit', 50, type=int)
        load_from_api = request.args.get('load_from_api', 'false').lower() == 'true'
        keyword = request.args.get('keyword', '').strip()
        
        session = get_db_session()
        try:
            total_count = session.query(ClsNews).count()
            
            # 如果有搜索关键词，执行搜索
            if keyword:
                search_pattern = f"%{keyword}%"
                query = session.query(ClsNews).filter(
                    (ClsNews.title.ilike(search_pattern)) | 
                    (ClsNews.content.ilike(search_pattern))
                ).order_by(ClsNews.ctime.desc())
                
                db_news = query.limit(limit).all()
                
                news_list = []
                for item in db_news:
                    stock_list = []
                    if item.stock_list:
                        try:
                            stock_list = json.loads(item.stock_list)
                        except:
                            pass
                    
                    news_list.append({
                        'id': item.news_id,
                        'title': item.title or '',
                        'content': item.content or '',
                        'ctime': item.ctime.strftime("%Y-%m-%d %H:%M:%S"),
                        'level': 'C',
                        'is_important': item.is_important == 1,
                        'level_text': '加红' if item.is_important == 1 else '普通',
                        'has_stocks': item.has_stocks == 1,
                        'confirmed': item.confirmed == 1,
                        'reading_num': item.reading_num or 0,
                        'stock_list': stock_list
                    })
                
                return jsonify({
                    'success': True,
                    'data': news_list,
                    'from_cache': True,
                    'has_more': False,
                    'total': len(news_list),
                    'keyword': keyword
                })
            
            if not force and not load_from_api:
                query = session.query(ClsNews).order_by(ClsNews.ctime.desc())
                
                if last_ctime_str:
                    try:
                        last_ctime = datetime.strptime(last_ctime_str, '%Y-%m-%d %H:%M:%S')
                        query = query.filter(ClsNews.ctime < last_ctime)
                    except ValueError:
                        pass
                
                db_news = query.limit(limit).all()
                
                if db_news:
                    news_list = []
                    for item in db_news:
                        stock_list = []
                        if item.stock_list:
                            try:
                                stock_list = json.loads(item.stock_list)
                            except:
                                pass
                        
                        news_list.append({
                            'id': item.news_id,
                            'title': item.title or '',
                            'content': item.content or '',
                            'ctime': item.ctime.strftime("%Y-%m-%d %H:%M:%S"),
                            'level': 'C',
                            'is_important': item.is_important == 1,
                            'level_text': '加红' if item.is_important == 1 else '普通',
                            'has_stocks': item.has_stocks == 1,
                            'confirmed': item.confirmed == 1,
                            'reading_num': item.reading_num or 0,
                            'stock_list': stock_list
                        })
                    
                    has_more = len(db_news) >= limit
                    
                    return jsonify({
                        'success': True,
                        'data': news_list,
                        'from_cache': True,
                        'has_more': has_more,
                        'total': total_count
                    })
                else:
                    return jsonify({
                        'success': True,
                        'data': [],
                        'from_cache': True,
                        'has_more': False,
                        'total': total_count
                    })
        finally:
            session.close()
        
        import requests as req_module
        import time as time_module
        import re
        
        url = "https://www.cls.cn/nodeapi/telegraphList"
        params = {
            "app": "CailianpressWeb",
            "os": "web",
            "refresh_type": "2" if last_ctime_str and load_from_api else "1",
            "order": "1",
            "rn": "50",
            "sv": "8.4.6"
        }
        
        if last_ctime_str and load_from_api:
            try:
                session = get_db_session()
                try:
                    last_ctime = datetime.strptime(last_ctime_str, '%Y-%m-%d %H:%M:%S')
                    last_news = session.query(ClsNews).filter(
                        ClsNews.ctime == last_ctime
                    ).first()
                    
                    if last_news:
                        params["last_id"] = last_news.news_id
                finally:
                    session.close()
            except ValueError:
                pass
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Referer": "https://www.cls.cn/telegraph"
        }
        
        response = req_module.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'请求失败: {response.status_code}'
            }), 500
        
        data = response.json()
        roll_data = data.get('data', {}).get('roll_data', [])
        
        session = get_db_session()
        news_list = []
        saved_count = 0
        
        try:
            news_ids = [str(item.get('id')) for item in roll_data if item.get('title') or item.get('content')]
            
            existing_news = session.query(ClsNews).filter(ClsNews.news_id.in_(news_ids)).all()
            existing_dict = {news.news_id: news for news in existing_news}
            
            for item in roll_data:
                title = item.get('title', '')
                content = item.get('content', '')
                stock_list = item.get('stock_list', [])
                confirmed = item.get('confirmed', 0)
                reading_num = item.get('reading_num', 0)
                
                if not title and not content:
                    continue
                
                has_stocks = len(stock_list) > 0
                recommend = item.get('recommend', 0)
                
                is_important = recommend == 1
                
                clean_content = re.sub(r'【[^】]*】', '', content)
                
                ctime_timestamp = item.get('ctime', 0)
                local_time = time_module.localtime(ctime_timestamp)
                ctime_dt = datetime.fromtimestamp(ctime_timestamp)
                news_id = str(item.get('id'))
                
                existing = existing_dict.get(news_id)
                
                if existing:
                    existing.title = title
                    existing.content = clean_content
                    existing.is_important = 1 if is_important else 0
                    existing.has_stocks = 1 if has_stocks else 0
                    existing.confirmed = 1 if confirmed == 1 else 0
                    existing.reading_num = reading_num
                    existing.stock_list = json.dumps([{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list]) if has_stocks else None
                else:
                    news_record = ClsNews(
                        news_id=news_id,
                        title=title,
                        content=clean_content,
                        ctime=ctime_dt,
                        is_important=1 if is_important else 0,
                        has_stocks=1 if has_stocks else 0,
                        confirmed=1 if confirmed == 1 else 0,
                        reading_num=reading_num,
                        stock_list=json.dumps([{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list]) if has_stocks else None
                    )
                    session.add(news_record)
                    saved_count += 1
                
                news_list.append({
                    'id': news_id,
                    'title': title,
                    'content': clean_content,
                    'ctime': time_module.strftime("%Y-%m-%d %H:%M:%S", local_time),
                    'level': item.get('level', 'C'),
                    'is_important': is_important,
                    'level_text': '加红' if is_important else '普通',
                    'has_stocks': has_stocks,
                    'confirmed': confirmed == 1,
                    'reading_num': reading_num,
                    'stock_list': [{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list] if has_stocks else []
                })
            
            session.commit()
            
        finally:
            session.close()
        
        news_list.sort(key=lambda x: x['ctime'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': news_list,
            'saved_count': saved_count,
            'from_cache': False,
            'has_more': len(news_list) >= limit
        })
        
    except Exception as e:
        print(f"获取财联社电报失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/news/analyze', methods=['POST'])
def analyze_news():
    """
    AI分析新闻
    
    请求体:
    {
        "news_id": "xxx",
        "title": "新闻标题",
        "content": "新闻内容",
        "force": false  # 是否强制重新分析
    }
    
    返回:
    {
        "success": true,
        "data": {
            "analysis": "AI分析结果",
            "related_stocks": ["股票1", "股票2"]
        }
    }
    """
    try:
        data = request.json
        news_id = data.get('news_id')
        title = data.get('title', '')
        content = data.get('content', '')
        force = data.get('force', False)
        
        if not title and not content:
            return jsonify({
                'success': False,
                'error': '缺少标题和内容'
            }), 400
        
        full_text = f"{title} {content}"
        
        session = get_db_session()
        try:
            if not force:
                news_record = session.query(ClsNews).filter(ClsNews.news_id == str(news_id)).first()
                
                if news_record and news_record.analysis_result:
                    try:
                        analysis_data = json.loads(news_record.analysis_result)
                        return jsonify({
                            'success': True,
                            'data': analysis_data,
                            'cached': True
                        })
                    except:
                        pass
        finally:
            session.close()
        
        analyzer = LimitUpReasonAnalyzer()
        
        analysis_result = analyzer.analyze_news_impact(full_text)
        
        session = get_db_session()
        try:
            news_record = session.query(ClsNews).filter(ClsNews.news_id == str(news_id)).first()
            if news_record:
                news_record.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                news_record.analyzed_at = datetime.now()
                session.commit()
        finally:
            session.close()
        
        return jsonify({
            'success': True,
            'data': analysis_result,
            'cached': False
        })
        
    except Exception as e:
        print(f"AI分析新闻失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reports/analyze', methods=['POST'])
def analyze_report():
    """
    AI分析研报
    
    请求体:
    {
        "info_code": "研报ID",
        "title": "研报标题",
        "stock_name": "股票名称",
        "stock_code": "股票代码",
        "rating": "评级",
        "rating_change": "评级变化",
        "predict_this_year_eps": "今年EPS预测",
        "predict_next_year_eps": "明年EPS预测",
        "predict_next_two_year_eps": "后年EPS预测",
        "predict_this_year_pe": "今年PE预测",
        "predict_next_year_pe": "明年PE预测",
        "predict_next_two_year_pe": "后年PE预测",
        "force": false
    }
    """
    try:
        data = request.json
        info_code = data.get('info_code')
        title = data.get('title', '')
        stock_name = data.get('stock_name', '')
        stock_code = data.get('stock_code', '')
        rating = data.get('rating', '')
        rating_change = data.get('rating_change', '')
        predict_this_year_eps = data.get('predict_this_year_eps', '')
        predict_next_year_eps = data.get('predict_next_year_eps', '')
        predict_next_two_year_eps = data.get('predict_next_two_year_eps', '')
        predict_this_year_pe = data.get('predict_this_year_pe', '')
        predict_next_year_pe = data.get('predict_next_year_pe', '')
        predict_next_two_year_pe = data.get('predict_next_two_year_pe', '')
        force = data.get('force', False)
        
        if not info_code:
            return jsonify({
                'success': False,
                'error': '缺少研报ID'
            }), 400
        
        if not title:
            return jsonify({
                'success': False,
                'error': '缺少研报标题'
            }), 400
        
        session = get_db_session()
        try:
            existing = session.query(ResearchReportAnalysisResult).filter(
                ResearchReportAnalysisResult.info_code == info_code
            ).first()
            
            if existing and not force:
                try:
                    analysis_data = json.loads(existing.analysis_result)
                    return jsonify({
                        'success': True,
                        'data': analysis_data,
                        'cached': True
                    })
                except:
                    pass
        finally:
            session.close()
        
        prompt = f"""分析以下研报对股票的影响：

研报标题：{title}
股票名称：{stock_name}
股票代码：{stock_code}
机构评级：{rating or '无'}
评级变化：{rating_change or '无'}
EPS预测：今年{predict_this_year_eps or '--'}，明年{predict_next_year_eps or '--'}，后年{predict_next_two_year_eps or '--'}
PE预测：今年{predict_this_year_pe or '--'}，明年{predict_next_year_pe or '--'}，后年{predict_next_two_year_pe or '--'}

返回JSON:
{{"analysis":"研报核心观点(100字内)","related_sectors":[{{"name":"相关板块","relevance":0.9}}],"related_stocks":[{{"code":"代码","name":"名称","reason":"原因"}}],"market_impact":"对股价的潜在影响(利好/利空/中性)","investment_suggestion":"投资建议和风险提示"}}

要求:最多3个板块,5只个股,直接返回JSON。"""
        
        analyzer = LimitUpReasonAnalyzer()
        
        analysis_result = analyzer.analyze_news_impact(prompt)
        
        session = get_db_session()
        try:
            today = datetime.now().date()
            
            existing_result = session.query(ResearchReportAnalysisResult).filter(
                ResearchReportAnalysisResult.info_code == info_code
            ).first()
            
            if existing_result:
                existing_result.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                existing_result.rating = rating
                existing_result.rating_change = rating_change
                existing_result.updated_at = datetime.now()
            else:
                new_result = ResearchReportAnalysisResult(
                    info_code=info_code,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    title=title,
                    rating=rating,
                    rating_change=rating_change,
                    analysis_result=json.dumps(analysis_result, ensure_ascii=False),
                    analysis_date=today
                )
                session.add(new_result)
            
            session.commit()
        finally:
            session.close()
        
        return jsonify({
            'success': True,
            'data': analysis_result,
            'cached': False
        })
        
    except Exception as e:
        print(f"AI分析研报失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stock/analyze', methods=['POST'])
def analyze_stock():
    """
    AI分析自选股
    
    请求体:
    {
        "stock_code": "股票代码",
        "stock_name": "股票名称",
        "force": false,
        "check_only": false
    }
    """
    try:
        data = request.json
        stock_code = data.get('stock_code', '')
        stock_name = data.get('stock_name', '')
        force = data.get('force', False)
        check_only = data.get('check_only', False)
        
        if not stock_code:
            return jsonify({
                'success': False,
                'error': '缺少股票代码'
            }), 400
        
        session = get_db_session()
        try:
            today = datetime.now().date()
            
            existing = session.query(WatchlistAnalysisResult).filter(
                WatchlistAnalysisResult.stock_code == stock_code,
                WatchlistAnalysisResult.analysis_date == today
            ).first()
            
            if existing and not force:
                try:
                    analysis_data = json.loads(existing.analysis_result)
                    return jsonify({
                        'success': True,
                        'has_cache': True,
                        'data': analysis_data,
                        'cached': True
                    })
                except:
                    pass
            
            if check_only:
                return jsonify({
                    'success': True,
                    'has_cache': False
                })
        finally:
            session.close()
        
        # 获取实时行情数据
        quote_data = data_fetcher.get_realtime_quote(stock_code)
        
        # 构造股票状态信息
        stock_status = ""
        if quote_data:
            price = quote_data.get('price', 0)
            open_price = quote_data.get('open', 0)
            high = quote_data.get('high', 0)
            low = quote_data.get('low', 0)
            prev_close = quote_data.get('prev_close', 0)
            change_percent = quote_data.get('change_percent', 0)
            volume = quote_data.get('volume', 0)
            amount = quote_data.get('amount', 0)
            
            status_parts = []
            if change_percent > 0:
                status_parts.append(f"涨幅{change_percent:.2f}%")
            elif change_percent < 0:
                status_parts.append(f"跌幅{abs(change_percent):.2f}%")
            else:
                status_parts.append("平盘")
            
            if price and open_price:
                status_parts.append(f"今开{open_price:.2f}元")
            if high and low:
                status_parts.append(f"最高{high:.2f}元")
                status_parts.append(f"最低{low:.2f}元")
            if volume:
                status_parts.append(f"成交量{(volume/10000):.0f}万手")
            if amount:
                status_parts.append(f"成交额{(amount/100000000):.2f}亿")
            
            stock_status = f" 现价{price:.2f}元 {', '.join(status_parts)}"
        
        analyzer = LimitUpReasonAnalyzer()
        
        analysis_result = analyzer.analyze_with_llm(
            limit_up_reason=f"自选股投资分析：{stock_name}{stock_status}",
            stock_code=stock_code,
            stock_name=stock_name,
            limit_up_price=quote_data.get('price') if quote_data else None,
            continuous_days=None,
            limit_up_time=None,
            seal_amount=None,
            turnover_rate=None
        )
        
        session = get_db_session()
        try:
            today = datetime.now().date()
            
            existing_result = session.query(WatchlistAnalysisResult).filter(
                WatchlistAnalysisResult.stock_code == stock_code,
                WatchlistAnalysisResult.analysis_date == today
            ).first()
            
            if existing_result:
                existing_result.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                existing_result.updated_at = datetime.now()
            else:
                new_result = WatchlistAnalysisResult(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    analysis_date=today,
                    analysis_result=json.dumps(analysis_result, ensure_ascii=False)
                )
                session.add(new_result)
            
            session.commit()
        finally:
            session.close()
        
        return jsonify({
            'success': True,
            'data': analysis_result,
            'cached': False
        })
        
    except Exception as e:
        print(f"AI分析股票失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stock/comfort', methods=['POST'])
def comfort_stock():
    """
    AI安慰分析持仓股票
    
    请求体:
    {
        "stock_code": "股票代码",
        "stock_name": "股票名称",
        "buy_price": 买入价格,
        "current_price": 当前价格,
        "position_profit": 持仓盈亏,
        "position_profit_ratio": 持仓盈亏比例
    }
    """
    try:
        data = request.json
        stock_code = data.get('stock_code', '')
        stock_name = data.get('stock_name', '')
        buy_price = data.get('buy_price', 0)
        current_price = data.get('current_price', 0)
        position_profit = data.get('position_profit', 0)
        position_profit_ratio = data.get('position_profit_ratio', 0)
        
        if not stock_code:
            return jsonify({
                'success': False,
                'error': '缺少股票代码'
            }), 400
        
        profit_status = ""
        if position_profit_ratio > 0:
            profit_status = f"盈利{position_profit:.2f}元（+{(position_profit_ratio * 100):.2f}%）"
        elif position_profit_ratio < 0:
            profit_status = f"亏损{abs(position_profit):.2f}元（{(position_profit_ratio * 100):.2f}%）"
        else:
            profit_status = "持平"
        
        prompt = f"""你是一位温暖专业的投资顾问,需要安慰和分析投资者的持仓。

股票: {stock_name}({stock_code})
买入价: {buy_price:.2f}元
现价: {current_price:.2f}元
持仓: {profit_status}

请返回JSON格式分析:
{{
  "emotion_comfort": "情感安慰(温暖话语,50-80字)",
  "rational_analysis": "理性分析(客观判断,50-80字)",
  "operation_advice": "操作建议(具体可行,30-50字)",
  "risk_warning": "风险提示(30-50字)",
  "future_outlook": "未来展望(客观判断,30-50字)",
  "overall_suggestion": "总体建议(持有/加仓/减仓/止损)"
}}

语气要温暖专业,避免过度乐观或悲观。只返回JSON,不要其他内容。"""
        
        api_key = "sk-rjknkdqxefbxebrbfawaokciapqzjejqzqfvlehyhohiknys"
        api_url = "https://api.siliconflow.cn/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-ai/DeepSeek-V4-Flash",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if content:
                try:
                    analysis_data = json.loads(content)
                    return jsonify({
                        'success': True,
                        'data': {
                            'analysis': analysis_data
                        }
                    })
                except json.JSONDecodeError:
                    return jsonify({
                        'success': True,
                        'data': {
                            'analysis': {
                                'emotion_comfort': content,
                                'rational_analysis': '',
                                'operation_advice': '',
                                'risk_warning': '',
                                'future_outlook': '',
                                'overall_suggestion': ''
                            }
                        }
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': 'AI返回内容为空'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': f'AI调用失败: {response.status_code}'
            }), 500
        
    except Exception as e:
        print(f"AI安慰分析失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    return jsonify({
        'success': True,
        'message': '登出成功'
    })


def sync_cls_news():
    """后台定时同步财联社新闻"""
    import requests as req_module
    import time as time_module
    import re
    
    while True:
        try:
            time_module.sleep(300)
            
            url = "https://www.cls.cn/nodeapi/telegraphList"
            params = {
                "app": "CailianpressWeb",
                "os": "web",
                "refresh_type": "1",
                "order": "1",
                "rn": "50",
                "sv": "8.4.6"
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.cls.cn/telegraph"
            }
            
            response = req_module.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                roll_data = data.get('data', {}).get('roll_data', [])
                
                session = get_db_session()
                try:
                    new_count = 0
                    update_count = 0
                    for item in roll_data:
                        title = item.get('title', '')
                        content = item.get('content', '')
                        stock_list = item.get('stock_list', [])
                        confirmed = item.get('confirmed', 0)
                        reading_num = item.get('reading_num', 0)
                        
                        if not title and not content:
                            continue
                        
                        has_stocks = len(stock_list) > 0
                        recommend = item.get('recommend', 0)
                        is_important = recommend == 1
                        clean_content = re.sub(r'【[^】]*】', '', content)
                        
                        ctime_timestamp = item.get('ctime', 0)
                        ctime_dt = datetime.fromtimestamp(ctime_timestamp)
                        news_id = str(item.get('id'))
                        
                        existing = session.query(ClsNews).filter(ClsNews.news_id == news_id).first()
                        
                        if existing:
                            if (existing.title != title or 
                                existing.content != clean_content or
                                existing.is_important != (1 if is_important else 0) or
                                existing.has_stocks != (1 if has_stocks else 0) or
                                existing.confirmed != (1 if confirmed == 1 else 0)):
                                
                                existing.title = title
                                existing.content = clean_content
                                existing.is_important = 1 if is_important else 0
                                existing.has_stocks = 1 if has_stocks else 0
                                existing.confirmed = 1 if confirmed == 1 else 0
                                existing.reading_num = reading_num
                                existing.stock_list = json.dumps([{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list]) if has_stocks else None
                                update_count += 1
                        else:
                            news_record = ClsNews(
                                news_id=news_id,
                                title=title,
                                content=clean_content,
                                ctime=ctime_dt,
                                is_important=1 if is_important else 0,
                                has_stocks=1 if has_stocks else 0,
                                confirmed=1 if confirmed == 1 else 0,
                                reading_num=reading_num,
                                stock_list=json.dumps([{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list]) if has_stocks else None
                            )
                            session.add(news_record)
                            new_count += 1
                    
                    session.commit()
                    if new_count > 0 or update_count > 0:
                        print(f"[财联社同步] 新增 {new_count} 条新闻，更新 {update_count} 条")
                finally:
                    session.close()
        except Exception as e:
            print(f"[财联社同步] 同步失败: {str(e)}")


@app.route('/api/weixin/signature', methods=['GET'])
def weixin_signature():
    """微信JS-SDK签名接口"""
    try:
        import hashlib
        import time
        import random
        import string
        
        url = request.args.get('url', '')
        
        WEIXIN_APP_ID = os.environ.get('WEIXIN_APP_ID', '')
        WEIXIN_APP_SECRET = os.environ.get('WEIXIN_APP_SECRET', '')
        
        if not WEIXIN_APP_ID or not WEIXIN_APP_SECRET:
            return jsonify({
                'success': False,
                'message': '微信配置未设置'
            })
        
        access_token_url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WEIXIN_APP_ID}&secret={WEIXIN_APP_SECRET}'
        token_response = requests.get(access_token_url, timeout=5)
        token_data = token_response.json()
        
        if 'access_token' not in token_data:
            return jsonify({
                'success': False,
                'message': '获取access_token失败'
            })
        
        access_token = token_data['access_token']
        
        jsapi_ticket_url = f'https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={access_token}&type=jsapi'
        ticket_response = requests.get(jsapi_ticket_url, timeout=5)
        ticket_data = ticket_response.json()
        
        if ticket_data.get('errcode', 0) != 0:
            return jsonify({
                'success': False,
                'message': '获取jsapi_ticket失败'
            })
        
        jsapi_ticket = ticket_data['ticket']
        
        noncestr = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        timestamp = int(time.time())
        
        string1 = f'jsapi_ticket={jsapi_ticket}&noncestr={noncestr}&timestamp={timestamp}&url={url}'
        signature = hashlib.sha1(string1.encode('utf-8')).hexdigest()
        
        return jsonify({
            'success': True,
            'appId': WEIXIN_APP_ID,
            'timestamp': timestamp,
            'nonceStr': noncestr,
            'signature': signature
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/user/settings', methods=['GET', 'POST'])
def handle_user_settings():
    """获取或更新用户设置"""
    session = get_db_session()
    try:
        uid = request.headers.get('X-User-Uid')
        if not uid:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        user = session.query(User).filter(User.uid == uid).first()
        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        
        if request.method == 'GET':
            import json
            settings = {}
            if user.settings:
                try:
                    settings = json.loads(user.settings)
                except:
                    settings = {}
            
            return jsonify({
                'success': True,
                'settings': settings
            })
        
        elif request.method == 'POST':
            import json
            new_settings = request.get_json()
            
            current_settings = {}
            if user.settings:
                try:
                    current_settings = json.loads(user.settings)
                except:
                    current_settings = {}
            
            current_settings.update(new_settings)
            user.settings = json.dumps(current_settings, ensure_ascii=False)
            session.commit()
            
            return jsonify({
                'success': True,
                'message': '设置已保存'
            })
    
    except Exception as e:
        print(f"处理用户设置失败: {e}")
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/ladder-comparison/<date_str>', methods=['GET'])
def get_ladder_comparison(date_str):
    """
    获取连板晋级对比数据
    
    返回今天和昨天的涨停数据，前端自行对比
    """
    session = get_db_session()
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        if trade_date > datetime.now().date():
            return jsonify({
                'success': False,
                'error': '无法获取未来日期的数据'
            }), 200
        
        prev_trade_date = session.query(LadderStats.trade_date).filter(
            LadderStats.trade_date < trade_date
        ).order_by(desc(LadderStats.trade_date)).first()
        
        if not prev_trade_date:
            return jsonify({
                'success': False,
                'error': '没有找到上一个交易日的数据'
            }), 200
        
        prev_date = prev_trade_date[0]
        
        today_stocks = session.query(LimitUpStock).filter(
            LimitUpStock.trade_date == trade_date
        ).all()
        
        yesterday_stocks = session.query(LimitUpStock).filter(
            LimitUpStock.trade_date == prev_date
        ).all()
        
        now = datetime.now()
        is_today = trade_date == now.date()
        
        trading_start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if not today_stocks:
            if is_today and now < trading_start_time:
                today_list = []
            else:
                return jsonify({
                    'success': False,
                    'error': '该日期暂无涨停股票数据'
                }), 200
        else:
            today_list = []
            for stock in today_stocks:
                today_list.append({
                    'code': stock.stock_code,
                    'name': stock.stock_name,
                    'continuous_days': stock.continuous_days,
                    'limit_up_time': stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else '',
                    'seal_amount': float(stock.seal_amount) if stock.seal_amount else 0.0,
                    'limit_up_price': float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                    'change_percent': float(stock.change_percent) if stock.change_percent else 0.0,
                    'turnover_rate': float(stock.turnover_rate) if stock.turnover_rate else 0.0
                })
        
        yesterday_list = []
        for stock in yesterday_stocks:
            yesterday_list.append({
                'code': stock.stock_code,
                'name': stock.stock_name,
                'continuous_days': stock.continuous_days,
                'limit_up_time': stock.limit_up_time.strftime('%H:%M:%S') if stock.limit_up_time else '',
                'seal_amount': float(stock.seal_amount) if stock.seal_amount else 0.0,
                'limit_up_price': float(stock.limit_up_price) if stock.limit_up_price else 0.0,
                'change_percent': float(stock.next_change) if stock.next_change else None
            })
        
        latest_trade_date = session.query(LadderStats.trade_date).order_by(desc(LadderStats.trade_date)).first()
        
        print(f"最新交易日查询结果: {latest_trade_date}")
        
        should_fetch_realtime = False
        if latest_trade_date:
            latest_date = latest_trade_date[0]
            print(f"最新交易日: {latest_date}, 用户选择日期: {trade_date}")
            
            if trade_date == latest_date:
                from trade_calendar import trade_calendar
                from quotes_utils import get_realtime_quotes, update_stock_data_change_percent
                
                should_fetch_realtime = trade_calendar.should_fetch_realtime_quotes(prev_date)
                
                if should_fetch_realtime:
                    print(f"满足实时获取条件: 当前日期 < 下一个交易日")
                else:
                    next_trading_day = trade_calendar.get_next_trading_day(prev_date)
                    print(f"不满足实时获取条件: 下一个交易日={next_trading_day}")
            else:
                print(f"用户选择的日期 {trade_date} != 最新交易日 {latest_date}")
        else:
            print("没有找到最新交易日")
        
        if should_fetch_realtime:
            yesterday_codes = [stock.stock_code for stock in yesterday_stocks]
            print(f"实时获取昨日涨停股票涨跌幅，股票数量: {len(yesterday_codes)}")
            
            quotes_dict = get_realtime_quotes(yesterday_codes, debug=True)
            update_stock_data_change_percent(yesterday_list, quotes_dict)
        else:
            print(f"从数据库读取历史数据，不实时获取")
        
        return jsonify({
            'success': True,
            'today': {
                'date': trade_date.strftime('%Y-%m-%d'),
                'stocks': today_list
            },
            'yesterday': {
                'date': prev_date.strftime('%Y-%m-%d'),
                'stocks': yesterday_list
            }
        })
        
    except Exception as e:
        print(f"获取连板晋级对比数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/api/hot-stocks', methods=['GET'])
def get_hot_stocks():
    """
    获取同花顺热股数据
    
    Args:
        list_type: 榜单类型 (normal/value/trend)
        
    Returns:
        热股列表数据
    """
    list_type = request.args.get('list_type', 'normal')
    
    valid_types = ['normal', 'value', 'trend']
    if list_type not in valid_types:
        return jsonify({
            'success': False,
            'error': f'无效的榜单类型，可选值: {", ".join(valid_types)}'
        }), 400
    
    try:
        if list_type == 'normal':
            url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=normal'
        elif list_type == 'value':
            url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=day&list_type=value'
        else:
            url = 'https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=day&list_type=trend'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://dq.10jqka.com.cn/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status_code') == 0:
            stock_list = data.get('data', {}).get('stock_list', [])
            
            processed_stocks = []
            for stock in stock_list:
                processed_stocks.append({
                    'code': stock.get('code', ''),
                    'name': stock.get('name', ''),
                    'price': float(stock.get('price', 0)) if stock.get('price') else 0.0,
                    'change_percent': float(stock.get('rise_and_fall', 0)) if stock.get('rise_and_fall') else 0.0,
                    'volume_ratio': float(stock.get('volume_ratio', 0)) if stock.get('volume_ratio') else None,
                    'turnover_rate': float(stock.get('turnover_rate', 0)) if stock.get('turnover_rate') else None,
                    'market_value': stock.get('market_value', ''),
                    'industry': ', '.join(stock.get('tag', {}).get('concept_tag', [])) if stock.get('tag', {}).get('concept_tag') else '',
                    'reason': stock.get('analyse', ''),
                    'rank': stock.get('order', 0),
                    'hot_value': int(float(stock.get('rate', 0))) if stock.get('rate') else 0,
                    'heat_degree': stock.get('heat_degree', 0),
                    'popularity_tag': stock.get('tag', {}).get('popularity_tag', ''),
                    'analyse_title': stock.get('analyse_title', ''),
                })
            
            return jsonify({
                'success': True,
                'data': processed_stocks,
                'list_type': list_type,
                'count': len(processed_stocks)
            })
        else:
            return jsonify({
                'success': False,
                'error': data.get('status_msg', '获取数据失败')
            }), 200
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': '请求超时，请稍后重试'
        }), 200
    except requests.exceptions.RequestException as e:
        print(f"请求同花顺热股数据失败: {e}")
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        }), 200
    except Exception as e:
        print(f"获取同花顺热股数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("初始化数据库...")
    init_database()
    
    try:
        session = get_db_session()
        session.execute("ALTER TABLE ai_analysis_results ALTER COLUMN stock_code TYPE VARCHAR(50)")
        session.commit()
        print("已更新 ai_analysis_results.stock_code 字段长度为 50")
    except Exception as e:
        print(f"更新字段长度时出错（可能已是正确长度）: {e}")
    finally:
        session.close()
    
    print("\n" + "="*50)
    print("初始化同花顺会话（后台线程）...")
    print("="*50)
    init_thread = threading.Thread(target=init_ths_session, daemon=True)
    init_thread.start()
    
    print("\n" + "="*50)
    print("启动财联社新闻同步（后台线程，每5分钟）...")
    print("="*50)
    sync_thread = threading.Thread(target=sync_cls_news, daemon=True)
    sync_thread.start()
    
    print("\n启动Web服务器...")
    print("访问地址: http://localhost:5001")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
