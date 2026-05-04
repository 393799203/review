#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask后端API
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timedelta
from sqlalchemy import desc
import sys
import os
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import DatabaseConfig, LimitUpStock, LadderStats, init_database, Block
from ths_fetcher import ThsFetcher

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
            }), 400
        
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
                    'error': '该日期没有涨停股票数据或不是交易日'
                }), 404
        
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
                    "list_days": stock.block.list_days or 0
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
                "turnover_rate": float(stock.turnover_rate) if stock.turnover_rate else 0.0
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
        try:
            from trade_calendar import trade_calendar
            
            start_date = trade_date + timedelta(days=1)
            end_date = trade_date + timedelta(days=7)
            trading_days = trade_calendar.get_trading_days(start_date, end_date)
            
            if trading_days:
                next_date = datetime.strptime(trading_days[0], '%Y%m%d').date()
                next_blocks = session.query(Block).filter(
                    Block.trade_date == next_date
                ).order_by(Block.limit_up_num.desc()).limit(5).all()
                
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
                'next_day_blocks': next_day_blocks
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
                "turnover_rate": float(stock.turnover_rate) if stock.turnover_rate else 0.0
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
        
        return jsonify({
            'success': True,
            'data': {
                'prev': prev_date,
                'next': next_date,
                'prev_days': prev_days,
                'next_days': next_days
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
        # 获取前端传递的日期参数
        data = request.get_json()
        date_str = data.get('date')
        
        if not date_str:
            return jsonify({
                'success': False,
                'error': '请提供日期参数'
            }), 400
        
        fetcher = LimitUpFetcher(ths_fetcher=ths_fetcher)
        
        # 重新爬取数据（fetch_and_save内部会删除旧数据）
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
                'error': '数据爬取失败'
            }), 500
            
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
    """获取指定日期的板块强度（按涨停数量排序，取前5）"""
    from trade_calendar import trade_calendar
    
    session = get_db_session()
    
    try:
        trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        # 获取下一个交易日（从断板日期往后找）
        start_date = trade_date + timedelta(days=1)
        end_date = trade_date + timedelta(days=7)  # 往后找7天，确保能找到下一个交易日
        
        trading_days = trade_calendar.get_trading_days(start_date, end_date)
        
        if not trading_days:
            return jsonify({
                'success': False,
                'error': '没有找到下一个交易日'
            }), 404
        
        next_date_str = trading_days[0]  # 第一个就是下一个交易日
        next_date = datetime.strptime(next_date_str, '%Y%m%d').date()
        
        # 查询下一个交易日的板块数据，按涨停数量降序排序，取前5
        blocks = session.query(Block).filter(
            Block.trade_date == next_date
        ).order_by(Block.limit_up_num.desc()).limit(5).all()
        
        if not blocks:
            return jsonify({
                'success': False,
                'error': f'{next_date_str} 没有板块数据'
            }), 404
        
        result = []
        for block in blocks:
            result.append({
                'block_code': block.block_code,
                'block_name': block.block_name,
                'limit_up_num': block.limit_up_num,
                'continuous_plate_num': block.continuous_plate_num,
                'change_rate': float(block.change_rate) if block.change_rate else 0,
                'high': block.high,
                'high_num': block.high_num,
            })
        
        return jsonify({
            'success': True,
            'data': {
                'date': next_date_str,
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


if __name__ == '__main__':
    print("初始化数据库...")
    init_database()
    
    print("\n" + "="*50)
    print("初始化同花顺会话（后台线程）...")
    print("="*50)
    init_thread = threading.Thread(target=init_ths_session, daemon=True)
    init_thread.start()
    
    print("\n启动Web服务器...")
    print("访问地址: http://localhost:5001")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
