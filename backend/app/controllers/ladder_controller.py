#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, date
from flask import request
from app.controllers.base_controller import BaseController
from app.services.ladder_service import LadderService
from database import get_db_session
from models import Block


class LadderController(BaseController):
    """连板天梯控制器类"""
    
    def __init__(self, data_fetcher=None):
        super().__init__(LadderService())
        self.ladder_service = self.service
        self.data_fetcher = data_fetcher
    
    def get_available_dates(self):
        """获取所有可用日期"""
        try:
            dates = self.ladder_service.get_all_dates()
            from flask import jsonify
            return jsonify({
                'success': True,
                'data': dates
            })
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_data_by_date(self, date_str: str):
        """获取指定日期的完整数据"""
        try:
            success, message, data = self.ladder_service.get_data_by_date(
                date_str, self.data_fetcher
            )
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data,
                    'date': date_str
                })
            else:
                return self.error(message, 200)
                
        except Exception as e:
            return self.error(str(e), 400)
    
    def get_latest_date(self):
        """获取最近一个交易日"""
        try:
            from trade_calendar import trade_calendar
            
            trading_days = trade_calendar.get_recent_trading_days(1)
            
            if not trading_days:
                return self.error('无法获取交易日', 500)
            
            latest_date = trading_days[0]
            
            return self.success(latest_date)
            
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_adjacent_trading_days(self, date_str: str):
        """获取指定日期前后一个月的交易日列表"""
        try:
            from trade_calendar import trade_calendar
            from datetime import timedelta
            
            target_date = datetime.strptime(date_str, '%Y%m%d').date()
            today = datetime.now().date()
            
            start_date = target_date - timedelta(days=31)
            end_date = min(target_date + timedelta(days=31), today)
            
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
            
            is_trading_day = trade_calendar.is_trading_day(target_date)
            
            return self.success({
                'prev': prev_date,
                'next': next_date,
                'prev_days': prev_days,
                'next_days': next_days,
                'is_trading_day': is_trading_day
            })
            
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_block_strength_by_date(self, date_str: str):
        """获取板块强度"""
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            min_limit_up_num = int(self.get_query_param('min_limit_up_num', 1))
            
            blocks = self.ladder_service.get_block_strength_by_date(
                trade_date, min_limit_up_num
            )
            
            from flask import jsonify
            return jsonify({
                'success': True,
                'data': {
                    'date': date_str,
                    'blocks': blocks
                }
            })
            
        except Exception as e:
            return self.error(str(e), 400)
    
    def get_continuous_blocks(self):
        """获取连续板块"""
        try:
            date_str = self.get_query_param('date')
            
            from flask import jsonify
            from trade_calendar import trade_calendar
            
            session = get_db_session()
            
            try:
                if date_str:
                    try:
                        base_date = datetime.strptime(date_str, '%Y%m%d').date()
                    except ValueError:
                        return jsonify({
                            'success': False,
                            'error': '日期格式错误，请使用YYYYMMDD格式'
                        }), 400
                else:
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
                
            finally:
                session.close()
            
        except Exception as e:
            return self.error(str(e), 500)
            
        except Exception as e:
            return self.error(str(e), 400)
    
    def update_stock_block(self):
        """更新股票板块"""
        try:
            data = self.get_json_data()
            stock_code = data.get('stock_code')
            trade_date_str = data.get('trade_date')
            block_name = data.get('block_name')
            block_id = data.get('block_id')
            
            if not all([stock_code, trade_date_str]) or (not block_name and not block_id):
                return self.error('缺少必要参数', 400)
            
            trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
            
            success = self.ladder_service.update_stock_block(
                stock_code, trade_date, block_id, block_name
            )
            
            if success:
                return self.success(message='更新成功')
            else:
                return self.error('更新失败', 400)
                
        except Exception as e:
            return self.error(str(e), 400)
    
    def refresh_data(self, date_str: str):
        """刷新数据"""
        try:
            if not date_str:
                return self.error('日期参数不能为空', 400)
            
            # 验证日期格式
            try:
                from datetime import datetime
                datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                return self.error('日期格式错误，请使用 YYYYMMDD 格式', 400)
            
            if not self.data_fetcher:
                return self.error('数据抓取器未初始化', 500)
            
            from fetch_data import LimitUpFetcher
            
            fetcher = LimitUpFetcher(data_fetcher=self.data_fetcher)
            success = fetcher.fetch_and_save(date_str)
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'message': f'数据刷新成功：{date_str}',
                    'date': date_str
                })
            else:
                return self.error('数据刷新失败', 400)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_statistics_by_date(self, date_str: str):
        """获取指定日期的统计数据"""
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            stats = self.ladder_service.get_statistics_by_date(trade_date)
            
            if stats:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': stats
                })
            else:
                return self.error('数据不存在', 404)
                
        except Exception as e:
            return self.error(str(e), 500)


ladder_controller = None

def init_ladder_controller(data_fetcher):
    """初始化连板天梯控制器"""
    global ladder_controller
    ladder_controller = LadderController(data_fetcher)
    return ladder_controller
