#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涨停数据获取脚本（重构版）
使用同花顺接口
"""

import pandas as pd
from datetime import datetime, timedelta, date, time
from decimal import Decimal
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import DatabaseConfig, LimitUpStock, LadderStats, FetchLog, Block
from core.data_fetcher import DataFetcher


class LimitUpFetcher:
    """涨停数据获取器"""
    
    def __init__(self, data_fetcher=None):
        self.db_config = DatabaseConfig()
        self.data_fetcher = data_fetcher if data_fetcher else DataFetcher()
    
    def get_db_session(self):
        return self.db_config.create_session()
    
    def parse_time(self, time_str):
        """解析时间字符串"""
        if not time_str or pd.isna(time_str):
            return None
        
        try:
            time_str = str(time_str).strip()
            
            if len(time_str) == 6 and time_str.isdigit():
                hour = int(time_str[0:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
                return time(hour, minute, second)
            
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) >= 2:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    second = int(parts[2]) if len(parts) > 2 else 0
                    return time(hour, minute, second)
        except:
            pass
        
        return None
    
    def parse_timestamp_or_time(self, value):
        """解析Unix时间戳或时间字符串"""
        if not value or pd.isna(value):
            return None
        
        try:
            if isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(int(value))
                return dt.time()
            
            value_str = str(value).strip()
            
            if value_str.isdigit() and len(value_str) >= 10:
                dt = datetime.fromtimestamp(int(value_str))
                return dt.time()
            
            return self.parse_time(value_str)
        except:
            return None
    
    def parse_continuous_days(self, high_days_str: str) -> int:
        """
        从high_days字符串解析连板数
        
        例如:
        - "首板" -> 1
        - "2天2板" -> 2
        - "3天2板" -> 2
        - "3天3板" -> 3
        - "4天2板" -> 2
        """
        if not high_days_str:
            return 1
        
        high_days_str = str(high_days_str).strip()
        
        if high_days_str == "首板":
            return 1
        
        import re
        match = re.search(r'(\d+)天(\d+)板', high_days_str)
        if match:
            return int(match.group(2))
        
        match = re.search(r'(\d+)板', high_days_str)
        if match:
            return int(match.group(1))
        
        return 1
    
    def get_stock_sector(self, stock_code: str) -> str:
        """获取股票所属板块"""
        if stock_code.startswith('688'):
            return "科创板"
        elif stock_code.startswith('300'):
            return "创业板"
        elif stock_code.startswith('00'):
            return "深市A股"
        elif stock_code.startswith('60'):
            return "沪市A股"
        else:
            return "其他"
    
    def get_recent_trading_days(self, count: int = 5):
        """获取最近N个交易日"""
        from trade_calendar import trade_calendar
        return trade_calendar.get_recent_trading_days(count)
    
    def fetch_and_save(self, date_str: str) -> bool:
        """
        爬取指定日期数据并存入数据库
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
        
        Returns:
            是否成功
        """
        session = self.get_db_session()
        start_time = datetime.now()
        
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            if trade_date > datetime.now().date():
                print(f"日期 {date_str} 是未来日期，无法获取数据")
                return False
            
            print(f"\n{'='*80}")
            print(f"开始爬取 {date_str} 的数据...")
            print(f"{'='*80}")
            
            # 保存next_change和next_open_change字段（避免刷新数据时被覆盖）
            next_change_backup = {}
            next_open_change_backup = {}
            old_stocks = session.query(LimitUpStock).filter(
                LimitUpStock.trade_date == trade_date
            ).all()
            for stock in old_stocks:
                if stock.next_change is not None:
                    next_change_backup[stock.stock_code] = stock.next_change
                if stock.next_open_change is not None:
                    next_open_change_backup[stock.stock_code] = stock.next_open_change
            print(f"✓ 已备份 {len(next_change_backup)} 只股票的next_change字段")
            print(f"✓ 已备份 {len(next_open_change_backup)} 只股票的next_open_change字段")
            
            existing_stocks = session.query(LimitUpStock).filter(
                LimitUpStock.trade_date == trade_date
            ).all()
            existing_stock_codes = {s.stock_code: s for s in existing_stocks}
            print(f"✓ 当前数据库中有 {len(existing_stock_codes)} 只涨停股票")
            
            existing_blocks = session.query(Block).filter(
                Block.trade_date == trade_date
            ).all()
            existing_block_codes = {b.block_code: b for b in existing_blocks}
            print(f"✓ 当前数据库中有 {len(existing_block_codes)} 个板块")
            
            existing_stats = session.query(LadderStats).filter(
                LadderStats.trade_date == trade_date
            ).first()
            
            ths_data = self.data_fetcher.get_all_data(date_str)
            
            success = self._process_and_save_data(
                session, trade_date, ths_data, existing_stock_codes, existing_block_codes, existing_stats
            )
            
            # 恢复next_change和next_open_change字段
            if next_change_backup or next_open_change_backup:
                restored_count = 0
                for stock_code in set(list(next_change_backup.keys()) + list(next_open_change_backup.keys())):
                    stock = session.query(LimitUpStock).filter(
                        LimitUpStock.stock_code == stock_code,
                        LimitUpStock.trade_date == trade_date
                    ).first()
                    if stock:
                        if stock_code in next_change_backup:
                            stock.next_change = next_change_backup[stock_code]
                        if stock_code in next_open_change_backup:
                            stock.next_open_change = next_open_change_backup[stock_code]
                        restored_count += 1
                session.commit()
                print(f"✓ 已恢复 {restored_count} 只股票的next_change/next_open_change字段")
            
            if success:
                # 记录日志
                fetch_log = FetchLog(
                    fetch_date=trade_date,
                    status='success',
                    stocks_count=session.query(LimitUpStock).filter(LimitUpStock.trade_date == trade_date).count(),
                    duration_seconds=int((datetime.now() - start_time).total_seconds())
                )
                session.add(fetch_log)
                session.commit()
                
                elapsed_time = (datetime.now() - start_time).total_seconds()
                print(f"\n{'='*80}")
                print(f"✓ 数据爬取完成！总耗时: {elapsed_time:.2f} 秒")
                print(f"{'='*80}")
                return True
            else:
                fetch_log = FetchLog(
                    fetch_date=trade_date,
                    status='failed',
                    error_message='数据为空或处理失败'
                )
                session.add(fetch_log)
                session.commit()
                return False
                
        except Exception as e:
            print(f"✗ 爬取数据失败: {e}")
            import traceback
            traceback.print_exc()
            
            fetch_log = FetchLog(
                fetch_date=trade_date,
                status='failed',
                error_message=str(e)
            )
            session.add(fetch_log)
            session.commit()
            
            return False
        finally:
            session.close()
    
    def _save_block_data(self, session, trade_date, ths_data, existing_block_codes):
        """保存板块数据"""
        block_id_dict = {}
        ths_reason_info_dict = {}
        stock_to_block_code = {}
        ths_continue_num_dict = {}

        if not ths_data.get('block_top'):
            return block_id_dict, ths_reason_info_dict, stock_to_block_code, ths_continue_num_dict

        print("\n保存板块数据...")
        for block in ths_data['block_top']:
            block_code = block.get('code', '')
            block_name = block.get('name', '')

            if not block_code or not block_name:
                continue

            stock_list = block.get('stock_list', [])
            high_stock_code = None
            max_continue_num = 0

            for stock in stock_list:
                continue_num = stock.get('continue_num', 0) or 0
                if continue_num > max_continue_num:
                    max_continue_num = continue_num
                    high_stock_code = stock.get('code', '')

            existing_block = existing_block_codes.get(block_code)

            if existing_block:
                existing_block.block_name = block_name
                existing_block.change_rate = Decimal(str(block.get('change', 0))) if block.get('change') else None
                existing_block.limit_up_num = block.get('limit_up_num', 0) or 0
                existing_block.continuous_plate_num = block.get('continuous_plate_num', 0) or 0
                existing_block.high = block.get('high', '')
                existing_block.high_num = block.get('high_num', 0) or 0
                existing_block.list_days = block.get('days', 0) or 0
                existing_block.high_stock_code = high_stock_code
                existing_block.updated_at = datetime.now()
                session.flush()
                block_id_dict[block_code] = existing_block.id
            else:
                block_obj = Block(
                    block_code=block_code,
                    block_name=block_name,
                    trade_date=trade_date,
                    change_rate=Decimal(str(block.get('change', 0))) if block.get('change') else None,
                    limit_up_num=block.get('limit_up_num', 0) or 0,
                    continuous_plate_num=block.get('continuous_plate_num', 0) or 0,
                    high=block.get('high', ''),
                    high_num=block.get('high_num', 0) or 0,
                    list_days=block.get('days', 0) or 0,
                    high_stock_code=high_stock_code
                )
                session.add(block_obj)
                session.flush()
                block_id_dict[block_code] = block_obj.id

            for stock in stock_list:
                stock_code = stock.get('code', '')
                if stock_code and stock_code not in stock_to_block_code:
                    ths_reason_info_dict[stock_code] = stock.get('reason_info', '')
                    stock_to_block_code[stock_code] = block_code
                    if stock.get('continue_num'):
                        ths_continue_num_dict[stock_code] = stock.get('continue_num')

        session.commit()
        print(f"✓ 保存了 {len(block_id_dict)} 个板块数据")

        return block_id_dict, ths_reason_info_dict, stock_to_block_code, ths_continue_num_dict

    def _build_ladder_data(self, ths_data, ths_continue_num_dict):
        """从涨停梯队接口获取连板数，并构建涨停类型字典"""
        # 从涨停梯队接口获取连板数（最准确）
        if ths_data.get('continuous_limit_up'):
            print("\n处理涨停梯队数据...")
            for ladder_item in ths_data['continuous_limit_up']:
                height = ladder_item.get('height', 1)
                for stock in ladder_item.get('code_list', []):
                    stock_code = stock.get('code', '')
                    if stock_code:
                        ths_continue_num_dict[stock_code] = height
            print(f"✓ 从涨停梯队获取了 {len(ths_continue_num_dict)} 只股票的连板数")

        # 构建涨停类型字典
        ths_limit_up_type_dict = {}
        if ths_data.get('limit_up_type'):
            for item in ths_data.get('limit_up_type', []):
                for stock in item.get('code_list', []):
                    ths_limit_up_type_dict[stock.get('code')] = item.get('type', '')

        return ths_continue_num_dict, ths_limit_up_type_dict

    def _build_pool_dicts(self, ths_data):
        """构建涨停池字典（涨停价、涨停原因等）"""
        ths_reason_dict = {}
        ths_high_days_dict = {}
        ths_limit_up_price_dict = {}
        ths_stock_info_dict = {}

        if not ths_data.get('limit_up_pool'):
            return ths_reason_dict, ths_high_days_dict, ths_limit_up_price_dict, ths_stock_info_dict

        info_list = ths_data['limit_up_pool'].get('info', [])
        print(f"\n处理同花顺涨停池数据: {len(info_list)} 只股票")

        for stock_info in info_list:
            stock_code = stock_info.get('code', '')
            if stock_code:
                ths_reason_dict[stock_code] = stock_info.get('reason_type', '')
                ths_high_days_dict[stock_code] = stock_info.get('high_days', '首板')
                ths_limit_up_price_dict[stock_code] = stock_info.get('latest', 0)
                ths_stock_info_dict[stock_code] = stock_info

        return ths_reason_dict, ths_high_days_dict, ths_limit_up_price_dict, ths_stock_info_dict

    def _build_stock_dataframe(self, ths_data):
        """从同花顺涨停池构建股票DataFrame"""
        if not ths_data.get('limit_up_pool'):
            return None

        print("\n从同花顺数据构建股票列表...")
        info_list = ths_data['limit_up_pool'].get('info', [])

        if not info_list:
            return None

        data_list = []
        for info in info_list:
            data_list.append({
                '代码': info.get('code', ''),
                '名称': info.get('name', ''),
                '涨跌幅': info.get('change_rate', 0),
                '最新价': info.get('latest', 0),
                '封板资金': info.get('order_amount', 0),
                '最后封板时间': info.get('last_limit_up_time', ''),
                '换手率': info.get('turnover_rate', 0),
                '成交额': info.get('currency_value', 0),
                '涨停类型': info.get('limit_up_type', ''),
                '高度板': info.get('high_days', '首板'),
            })

        limit_up_df = pd.DataFrame(data_list)
        print(f"✓ 构建了 {len(limit_up_df)} 只股票的DataFrame")
        return limit_up_df

    def _process_single_stock(self, session, row, trade_date, ths_continue_num_dict,
                               ths_reason_dict, ths_high_days_dict, ths_limit_up_price_dict,
                               ths_limit_up_type_dict, ths_reason_info_dict,
                               block_id_dict, stock_to_block_code):
        """处理单只股票数据"""
        stock_code = str(row.get("代码", ""))
        stock_name = str(row.get("名称", ""))

        # 获取连板数（优先级：涨停梯队 > 默认首板）
        continuous_days = ths_continue_num_dict.get(stock_code, 0)
        if continuous_days == 0:
            continuous_days = 1

        # 获取涨停原因
        limit_reason = ths_reason_dict.get(stock_code, '')
        if not limit_reason:
            limit_reason = str(row.get("所属行业", "")) if pd.notna(row.get("所属行业")) else "未分类"

        # 获取高度板字段
        high_days = ths_high_days_dict.get(stock_code, row.get("高度板", "首板"))

        # 获取涨停价
        limit_up_price = ths_limit_up_price_dict.get(stock_code, 0)
        if not limit_up_price:
            limit_up_price = float(row.get("最新价", 0)) if pd.notna(row.get("最新价")) else 0

        # 获取涨停类型
        limit_up_type = ths_limit_up_type_dict.get(stock_code, row.get("涨停类型", ''))

        # 获取详细涨停原因
        ths_reason_info = ths_reason_info_dict.get(stock_code, '')

        # 获取板块ID
        block_code = stock_to_block_code.get(stock_code, '')
        block_id = block_id_dict.get(block_code) if block_code else None

        # 判断是否是高位股
        is_high_stock = 0
        if block_id:
            block = session.query(Block).filter(Block.id == block_id).first()
            if block and block.high_stock_code == stock_code:
                is_high_stock = 1

        # 解析涨停时间（可能是Unix时间戳或字符串）
        limit_up_time_raw = row.get("最后封板时间")
        limit_up_time = self.parse_timestamp_or_time(limit_up_time_raw)

        # 查找已存在的股票记录
        existing_stock = session.query(LimitUpStock).filter(
            LimitUpStock.stock_code == stock_code,
            LimitUpStock.trade_date == trade_date
        ).first()

        stock_data = {
            'stock_name': stock_name,
            'limit_up_reason': limit_reason,
            'limit_up_time': limit_up_time,
            'limit_up_price': Decimal(str(limit_up_price)) if limit_up_price else None,
            'limit_up_type': limit_up_type,
            'block_id': block_id,
            'ths_reason_info': ths_reason_info,
            'seal_amount': Decimal(str(row.get("封板资金", 0))) if pd.notna(row.get("封板资金")) else Decimal('0'),
            'continuous_days': continuous_days,
            'high_days': high_days,
            'sector': self.get_stock_sector(stock_code),
            'change_percent': Decimal(str(row.get("涨跌幅", 0))) if pd.notna(row.get("涨跌幅")) else Decimal('0'),
            'turnover_rate': Decimal(str(row.get("换手率", 0))) if pd.notna(row.get("换手率")) else Decimal('0'),
            'amount': Decimal(str(row.get("成交额", 0))) if pd.notna(row.get("成交额")) else Decimal('0'),
            'is_high_stock': is_high_stock,
            'current_status': 'close',
            'updated_at': datetime.now()
        }

        if existing_stock:
            for key, value in stock_data.items():
                setattr(existing_stock, key, value)
        else:
            stock = LimitUpStock(
                stock_code=stock_code,
                trade_date=trade_date,
                **stock_data
            )
            session.add(stock)

        # 更新板块的高位股名称
        if is_high_stock and block_id:
            block = session.query(Block).filter(Block.id == block_id).first()
            if block:
                block.high_stock_name = stock_name

        return continuous_days

    def _process_stocks_and_mark_opened(self, session, trade_date, limit_up_df, existing_stock_codes,
                                         ths_continue_num_dict, ths_reason_dict, ths_high_days_dict,
                                         ths_limit_up_price_dict, ths_limit_up_type_dict,
                                         ths_reason_info_dict, block_id_dict, stock_to_block_code):
        """处理所有股票数据并标记开板股票，返回连板统计"""
        ladder_stats = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}

        if limit_up_df is None or limit_up_df.empty:
            return ladder_stats

        print(f"\n处理 {len(limit_up_df)} 只涨停股...")

        for idx, row in limit_up_df.iterrows():
            continuous_days = self._process_single_stock(
                session, row, trade_date, ths_continue_num_dict,
                ths_reason_dict, ths_high_days_dict, ths_limit_up_price_dict,
                ths_limit_up_type_dict, ths_reason_info_dict,
                block_id_dict, stock_to_block_code
            )

            if continuous_days >= 8:
                ladder_stats[8] += 1
            else:
                ladder_stats[continuous_days] += 1

        # 标记开板股票
        current_limit_up_codes = set(str(row.get("代码", "")) for idx, row in limit_up_df.iterrows())

        opened_stocks_count = 0
        for stock_code, existing_stock in existing_stock_codes.items():
            if stock_code not in current_limit_up_codes:
                existing_stock.current_status = 'open'
                existing_stock.updated_at = datetime.now()
                opened_stocks_count += 1

        if opened_stocks_count > 0:
            print(f"✓ 标记了 {opened_stocks_count} 只股票为开板状态")

        return ladder_stats

    def _save_ladder_stats(self, session, trade_date, ladder_stats, existing_stats):
        """保存梯阯统计数据"""
        total_count = sum(ladder_stats.values())

        if total_count == 0:
            return False

        if existing_stats:
            existing_stats.total_count = total_count
            existing_stats.first_board = ladder_stats[1]
            existing_stats.second_board = ladder_stats[2]
            existing_stats.third_board = ladder_stats[3]
            existing_stats.fourth_board = ladder_stats[4]
            existing_stats.fifth_board = ladder_stats[5]
            existing_stats.sixth_board = ladder_stats[6]
            existing_stats.seventh_board = ladder_stats[7]
            existing_stats.eighth_plus_board = ladder_stats[8]
        else:
            stats = LadderStats(
                trade_date=trade_date,
                total_count=total_count,
                first_board=ladder_stats[1],
                second_board=ladder_stats[2],
                third_board=ladder_stats[3],
                fourth_board=ladder_stats[4],
                fifth_board=ladder_stats[5],
                sixth_board=ladder_stats[6],
                seventh_board=ladder_stats[7],
                eighth_plus_board=ladder_stats[8]
            )
            session.add(stats)

        return True

    def _update_next_change(self, session, trade_date):
        """更新昨日涨停股票的次日涨跌幅"""
        prev_trade_date = session.query(LadderStats.trade_date).filter(
            LadderStats.trade_date < trade_date
        ).order_by(LadderStats.trade_date.desc()).first()

        if not prev_trade_date:
            return

        prev_date = prev_trade_date[0]

        from trade_calendar import trade_calendar
        from quotes_utils import get_realtime_quotes, update_stocks_next_change

        should_update = trade_calendar.should_fetch_realtime_quotes(prev_date)

        if should_update:
            now = datetime.now()
            current_date = now.date()
            next_trading_day = trade_calendar.get_next_trading_day(prev_date)

            if next_trading_day and current_date == next_trading_day:
                call_auction_start = now.replace(hour=9, minute=15, second=0, microsecond=0)

                if now < call_auction_start:
                    print(f"当前时间在9:15之前，更新前两日涨停股票的次日涨跌幅")
                    self._update_prev_prev_stocks(session, prev_date)
                else:
                    print(f"当前时间在交易时间内或收盘后，更新 {prev_date} 涨停股票的次日涨跌幅")
                    self._update_yesterday_stocks(session, prev_date, trade_date)
            else:
                print(f"当前日期小于下一个交易日，更新 {prev_date} 涨停股票的次日涨跌幅")
                self._update_yesterday_stocks(session, prev_date, trade_date)
        else:
            next_trading_day = trade_calendar.get_next_trading_day(prev_date)
            print(f"当前时间 < 下一个交易日 {next_trading_day} 的9:15，不更新next_change字段")

    def _update_yesterday_stocks(self, session, prev_date, trade_date):
        """更新昨日涨停股票的次日涨跌幅"""
        from quotes_utils import get_realtime_quotes, update_stocks_next_change

        yesterday_stocks = session.query(LimitUpStock).filter(
            LimitUpStock.trade_date == prev_date
        ).all()

        if yesterday_stocks:
            yesterday_codes = [stock.stock_code for stock in yesterday_stocks]
            quotes_dict = get_realtime_quotes(yesterday_codes, debug=True)

            updated_count = update_stocks_next_change(yesterday_stocks, quotes_dict, debug=True)
            print(f"✓ 更新了 {updated_count} 只 {prev_date} 涨停股票的次日涨跌幅（{trade_date}的价格）")
            
            # 提交事务，保存next_change和next_open_change字段
            session.commit()
            print(f"✓ 已保存 {updated_count} 只股票的次日涨跌幅和竞价溢价到数据库")

    def _update_prev_prev_stocks(self, session, prev_date):
        """更新前日涨停股票的次日涨跌幅"""
        from quotes_utils import get_realtime_quotes, update_stocks_next_change

        prev_prev_trade_date = session.query(LadderStats.trade_date).filter(
            LadderStats.trade_date < prev_date
        ).order_by(LadderStats.trade_date.desc()).first()

        if not prev_prev_trade_date:
            return

        prev_prev_date = prev_prev_trade_date[0]

        prev_prev_stocks = session.query(LimitUpStock).filter(
            LimitUpStock.trade_date == prev_prev_date
        ).all()

        if prev_prev_stocks:
            prev_prev_codes = [stock.stock_code for stock in prev_prev_stocks]
            quotes_dict = get_realtime_quotes(prev_prev_codes, debug=True)

            updated_count = update_stocks_next_change(prev_prev_stocks, quotes_dict, debug=True)
            print(f"✓ 更新了 {updated_count} 只 {prev_prev_date} 涨停股票的次日涨跌幅（{prev_date}的收盘价）")
            
            # 提交事务，保存next_change和next_open_change字段
            session.commit()
            print(f"✓ 已保存 {updated_count} 只股票的次日涨跌幅和竞价溢价到数据库")

    def _process_and_save_data(self, session, trade_date, ths_data, existing_stock_codes=None, existing_block_codes=None, existing_stats=None):
        """处理并保存数据（重构后的主入口方法）"""
        if existing_stock_codes is None:
            existing_stock_codes = {}
        if existing_block_codes is None:
            existing_block_codes = {}

        # 1. 保存板块数据
        block_id_dict, ths_reason_info_dict, stock_to_block_code, ths_continue_num_dict = \
            self._save_block_data(session, trade_date, ths_data, existing_block_codes)

        # 2. 处理涨停梯队数据和涨停类型
        ths_continue_num_dict, ths_limit_up_type_dict = \
            self._build_ladder_data(ths_data, ths_continue_num_dict)

        # 3. 构建涨停池字典
        ths_reason_dict, ths_high_days_dict, ths_limit_up_price_dict, ths_stock_info_dict = \
            self._build_pool_dicts(ths_data)

        # 4. 构建股票DataFrame
        limit_up_df = self._build_stock_dataframe(ths_data)

        # 5. 处理股票数据并标记开板
        ladder_stats = self._process_stocks_and_mark_opened(
            session, trade_date, limit_up_df, existing_stock_codes,
            ths_continue_num_dict, ths_reason_dict, ths_high_days_dict,
            ths_limit_up_price_dict, ths_limit_up_type_dict,
            ths_reason_info_dict, block_id_dict, stock_to_block_code
        )

        # 6. 保存统计数据
        has_data = self._save_ladder_stats(session, trade_date, ladder_stats, existing_stats)

        if not has_data:
            print("✗ 没有获取到任何数据")
            return False

        # 7. 更新昨日涨停股票的次日涨跌幅
        self._update_next_change(session, trade_date)

        session.commit()

        total_count = sum(ladder_stats.values())
        print(f"\n✓ 数据保存成功！")
        print(f"  涨停总数: {total_count}")
        print(f"  首板: {ladder_stats[1]}")
        print(f"  2连板: {ladder_stats[2]}")
        print(f"  3连板: {ladder_stats[3]}")
        print(f"  4连板: {ladder_stats[4]}")
        print(f"  5连板+: {sum(ladder_stats[i] for i in range(5, 9))}")

        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='爬取涨停数据')
    parser.add_argument('--date', type=str, help='指定日期（YYYYMMDD）')
    
    args = parser.parse_args()
    
    fetcher = LimitUpFetcher()
    
    if args.date:
        fetcher.fetch_and_save(args.date)
    else:
        print("请使用 --date 参数指定日期")
