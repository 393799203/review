#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask后端API
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import sys
import os
import threading
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import DatabaseConfig, LimitUpStock, LadderStats, init_database, Block, WatchlistStock, TradeRecord, AIAnalysisResult, User, StockDiffRecord, ClsNews
from ths_fetcher import ThsFetcher
from statistics_api import register_statistics_routes
from limit_up_analyzer import LimitUpReasonAnalyzer

app = Flask(__name__)
CORS(app)

db_config = DatabaseConfig()

ths_fetcher = ThsFetcher()


def init_ths_session():
    """初始化同花顺会话并启动心跳"""
    print("初始化同花顺会话...")
    if ths_fetcher.init_session():
        ths_fetcher.start_heartbeat(interval=60)
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
        'ths_session_ready': ths_fetcher.is_ready()
    })


@app.route('/api/ths-status', methods=['GET'])
def ths_status():
    """获取同花顺会话状态"""
    return jsonify({
        'success': True,
        'data': {
            'session_ready': ths_fetcher.is_ready(),
            'heartbeat_running': ths_fetcher._heartbeat_running
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
        
        # 如果没有数据，触发同步
        if not stocks or not stats:
            print(f"日期 {date_str} 没有数据，触发同步...")
            from fetch_data import LimitUpFetcher
            
            fetcher = LimitUpFetcher(ths_fetcher=ths_fetcher)
            success = fetcher.fetch_and_save(date_str)
            
            if success:
                # 重新查询数据
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
        
        # 获取次日板块强度排名
        next_day_blocks = []
        next_day_date = None
        try:
            from trade_calendar import trade_calendar
            
            start_date = trade_date + timedelta(days=1)
            end_date = trade_date + timedelta(days=7)
            trading_days = trade_calendar.get_trading_days(start_date, end_date)
            
            if trading_days:
                next_date = datetime.strptime(trading_days[0], '%Y%m%d').date()
                next_day_date = trading_days[0]  # 保存下一个交易日的日期字符串
                next_blocks = session.query(Block).filter(
                    Block.trade_date == next_date
                ).order_by(Block.limit_up_num.desc()).all()
                
                for rank, block in enumerate(next_blocks, 1):
                    next_day_blocks.append({
                        'block_name': block.block_name,
                        'rank': rank,
                        'limit_up_num': block.limit_up_num
                    })
        except Exception as e:
            print(f"获取次日板块强度失败: {e}")
        
        # 获取昨天的最高连板数据
        yesterday_data = None
        try:
            from trade_calendar import trade_calendar
            prev_trading_days = trade_calendar.get_recent_trading_days(2, end_date=trade_date)
            
            if prev_trading_days and len(prev_trading_days) >= 2:
                prev_date_str = prev_trading_days[1]  # 第二个元素是前一个交易日
                
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
                'yesterday': yesterday_data,
                'next_day_blocks': next_day_blocks,
                'next_day_date': next_day_date
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
            
            fetcher = LimitUpFetcher(ths_fetcher=ths_fetcher)
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
        
        fetcher = LimitUpFetcher(ths_fetcher=ths_fetcher)
        
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

        # 找前一个交易日作为"昨日"
        yesterday = None
        for i in range(1, 31):
            d = base_date - timedelta(days=i)
            if trade_calendar.is_trading_day(d):
                yesterday = d
                break
        if yesterday:
            target_days.append(('yesterday', yesterday))

        # 传入的日期作为"今日"
        target_days.append(('today', base_date))

        # 找下一个交易日作为"明日"
        tomorrow = None
        for i in range(1, 31):
            d = base_date + timedelta(days=i)
            if trade_calendar.is_trading_day(d):
                tomorrow = d
                break
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
        watchlist = session.query(WatchlistStock).order_by(desc(WatchlistStock.created_at)).all()
        
        result = []
        for stock in watchlist:
            stock_total_profit = session.query(func.sum(TradeRecord.profit)).filter(
                TradeRecord.stock_code == stock.stock_code,
                TradeRecord.operation_type == '卖出',
                TradeRecord.profit.isnot(None)
            ).scalar() or 0
            
            buy_records = session.query(TradeRecord).filter(
                TradeRecord.stock_code == stock.stock_code,
                TradeRecord.operation_type == '买入',
                TradeRecord.remaining_quantity > 0
            ).all()
            
            current_quantity = sum(r.remaining_quantity for r in buy_records)
            
            try:
                stock_code_num = stock.stock_code.split('.')[0]
                quote = ths_fetcher.get_realtime_quote(stock_code_num)
                current_price = quote['price'] if quote and 'price' in quote else None
            except Exception as e:
                print(f"更新股票 {stock.stock_code} 价格失败: {e}")
                current_price = None
            
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
                'add_reason': stock.add_reason or '',
                'source': stock.source or '',
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
        data = request.json
        stock_code = data.get('stock_code')
        stock_name = data.get('stock_name')
        add_date_str = data.get('add_date')
        add_price = data.get('add_price')
        add_reason = data.get('add_reason', '')
        source = data.get('source', 'wencai')
        limit_up_reason_category = data.get('limit_up_reason_category', '')
        
        if not stock_code or not stock_name or not add_date_str:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        add_date = datetime.strptime(add_date_str, '%Y%m%d').date()
        
        existing = session.query(WatchlistStock).filter(
            WatchlistStock.stock_code == stock_code
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': '该股票已在自选列表中'
            }), 400
        
        watchlist_stock = WatchlistStock(
            stock_code=stock_code,
            stock_name=stock_name,
            add_date=add_date,
            add_price=add_price,
            add_reason=add_reason,
            source=source,
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
        stock = session.query(WatchlistStock).filter(
            WatchlistStock.stock_code == stock_code
        ).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '股票不在自选列表中'
            }), 404
        
        buy_records = session.query(TradeRecord).filter(
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


@app.route('/api/stock/quote/<stock_code>', methods=['GET'])
def get_stock_quote(stock_code):
    """获取单只股票的实时行情"""
    try:
        quote = ths_fetcher.get_realtime_quote(stock_code)
        
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
        data = request.json
        stock_code = data.get('stock_code')
        buy_price = data.get('buy_price')
        buy_quantity = data.get('buy_quantity', 100)
        
        if not stock_code or not buy_price:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        stock = session.query(WatchlistStock).filter_by(stock_code=stock_code).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '股票不在自选列表中'
            }), 404
        
        trade_record = TradeRecord(
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
        data = request.json
        stock_code = data.get('stock_code')
        sell_price = data.get('sell_price')
        sell_quantity = data.get('sell_quantity')
        
        if not stock_code or not sell_price:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        stock = session.query(WatchlistStock).filter_by(stock_code=stock_code).first()
        
        if not stock:
            return jsonify({
                'success': False,
                'error': '股票不在自选列表中'
            }), 404
        
        buy_records = session.query(TradeRecord).filter(
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
        records = session.query(TradeRecord).order_by(TradeRecord.operation_date.desc()).all()
        
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
        
        kline_data = ths_fetcher.get_stock_kline(stock_code_clean, days)
        
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
    """获取股票当日分时数据"""
    try:
        stock_code_clean = stock_code.split('.')[0]
        
        intraday_data = ths_fetcher.get_stock_intraday(stock_code_clean)
        
        if intraday_data:
            return jsonify({
                'success': True,
                'data': intraday_data
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


@app.route('/api/stock/analyze/<stock_code>', methods=['GET'])
def analyze_limit_up_reason(stock_code):
    """
    分析涨停原因，提取炒作逻辑、关联板块和买入推荐指数
    
    Args:
        stock_code: 股票代码
        force: 是否强制重新分析（跳过缓存）
        
    Returns:
        分析结果
    """
    force = request.args.get('force', 'false').lower() == 'true'
    
    session = get_db_session()
    try:
        # 查询最近一次涨停记录
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
        
        if cached_result and not force:
            print(f"从缓存读取 {stock_data['stock_name']}({stock_code}) {stock_data['trade_date']} 的分析结果")
            analysis = json.loads(cached_result.analysis_result)
        else:
            if force and cached_result:
                print(f"强制重新分析 {stock_data['stock_name']}({stock_code}) {stock_data['trade_date']}")
            else:
                print(f"缓存未命中,开始分析 {stock_data['stock_name']}({stock_code}) {stock_data['trade_date']}")
            
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
        
        session = get_db_session()
        try:
            total_count = session.query(ClsNews).count()
            
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
                
                existing = session.query(ClsNews).filter(ClsNews.news_id == news_id).first()
                
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
            
            existing = session.query(AIAnalysisResult).filter(
                AIAnalysisResult.stock_code == f"NEWS_{news_id}"
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
        
        analyzer = LimitUpReasonAnalyzer()
        
        analysis_result = analyzer.analyze_news_impact(full_text)
        
        session = get_db_session()
        try:
            today = datetime.now().date()
            
            existing_result = session.query(AIAnalysisResult).filter(
                AIAnalysisResult.stock_code == f"NEWS_{news_id}"
            ).first()
            
            if existing_result:
                existing_result.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                existing_result.updated_at = datetime.now()
            else:
                new_result = AIAnalysisResult(
                    stock_code=f"NEWS_{news_id}",
                    stock_name=title[:50] if title else '未知',
                    trade_date=today,
                    analysis_result=json.dumps(analysis_result, ensure_ascii=False)
                )
                session.add(new_result)
            
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


if __name__ == '__main__':
    print("初始化数据库...")
    init_database()
    
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
    
    app.run(host='0.0.0.0', port=5001, debug=True)
