#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涨停数据获取脚本（重构版）
使用同花顺接口（主）+ akshare接口（备）
"""

import pandas as pd
from datetime import datetime, timedelta, date, time
from decimal import Decimal
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import DatabaseConfig, LimitUpStock, LadderStats, FetchLog, Block
from ths_fetcher import ThsFetcher
from akshare_fetcher import AkshareFetcher


class LimitUpFetcher:
    """涨停数据获取器"""
    
    def __init__(self, ths_fetcher=None):
        self.db_config = DatabaseConfig()
        self.ths_fetcher = ths_fetcher if ths_fetcher else ThsFetcher()
        self.akshare_fetcher = AkshareFetcher()
    
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
            
            # 删除该日期的旧数据
            session.query(LimitUpStock).filter(
                LimitUpStock.trade_date == trade_date
            ).delete()
            session.query(LadderStats).filter(
                LadderStats.trade_date == trade_date
            ).delete()
            session.query(Block).filter(
                Block.trade_date == trade_date
            ).delete()
            session.commit()
            print(f"✓ 已删除 {date_str} 的旧数据")
            
            # 优先使用同花顺接口获取数据
            ths_data = self.ths_fetcher.get_all_data(date_str)
            
            # 使用akshare作为备用（只有接口调用失败时才使用）
            akshare_data = None
            if ths_data.get('limit_up_pool') is None:
                print("\n同花顺涨停池接口调用失败，使用akshare作为备用...")
                akshare_data = self.akshare_fetcher.get_all_data(date_str)
            
            # 处理并保存数据
            success = self._process_and_save_data(
                session, trade_date, ths_data, akshare_data
            )
            
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
    
    def _process_and_save_data(self, session, trade_date, ths_data, akshare_data):
        """处理并保存数据"""
        stocks_data = []
        ladder_stats = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}
        
        # 1. 保存板块数据
        block_id_dict = {}
        ths_reason_info_dict = {}
        stock_to_block_code = {}
        ths_continue_num_dict = {}
        
        if ths_data.get('block_top'):
            print("\n保存板块数据...")
            for block in ths_data['block_top']:
                block_code = block.get('code', '')
                block_name = block.get('name', '')
                
                if block_code and block_name:
                    # 找出高位股（连板数最高的股票）
                    stock_list = block.get('stock_list', [])
                    high_stock_code = None
                    high_stock_name = None
                    max_continue_num = 0
                    
                    for stock in stock_list:
                        continue_num = stock.get('continue_num', 0) or 0
                        if continue_num > max_continue_num:
                            max_continue_num = continue_num
                            high_stock_code = stock.get('code', '')
                            # 需要从涨停池数据中获取股票名称，这里先保存代码
                    
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
        
        # 2. 从涨停梯队接口获取连板数（最准确）
        if ths_data.get('continuous_limit_up'):
            print("\n处理涨停梯队数据...")
            for ladder_item in ths_data['continuous_limit_up']:
                height = ladder_item.get('height', 1)
                for stock in ladder_item.get('code_list', []):
                    stock_code = stock.get('code', '')
                    if stock_code:
                        ths_continue_num_dict[stock_code] = height
            print(f"✓ 从涨停梯队获取了 {len(ths_continue_num_dict)} 只股票的连板数")
        
        # 3. 构建涨停类型字典
        ths_limit_up_type_dict = {}
        if ths_data.get('limit_up_type'):
            for item in ths_data.get('limit_up_type', []):
                for stock in item.get('code_list', []):
                    ths_limit_up_type_dict[stock.get('code')] = item.get('type', '')
        
        # 4. 构建涨停池字典（涨停价、涨停原因等）
        ths_reason_dict = {}
        ths_high_days_dict = {}
        ths_limit_up_price_dict = {}
        ths_stock_info_dict = {}
        
        if ths_data.get('limit_up_pool'):
            info_list = ths_data['limit_up_pool'].get('info', [])
            print(f"\n处理同花顺涨停池数据: {len(info_list)} 只股票")
            
            for stock_info in info_list:
                stock_code = stock_info.get('code', '')
                if stock_code:
                    ths_reason_dict[stock_code] = stock_info.get('reason_type', '')
                    ths_high_days_dict[stock_code] = stock_info.get('high_days', '首板')
                    ths_limit_up_price_dict[stock_code] = stock_info.get('latest', 0)
                    ths_stock_info_dict[stock_code] = stock_info
        
        # 5. 使用akshare作为备用数据源
        limit_up_df = None
        if akshare_data and akshare_data.get('limit_up_pool') is not None:
            limit_up_df = akshare_data['limit_up_pool']
        
        # 如果没有akshare数据，从同花顺涨停池构建股票列表
        if limit_up_df is None and ths_data.get('limit_up_pool'):
            print("\n从同花顺数据构建股票列表...")
            info_list = ths_data['limit_up_pool'].get('info', [])
            
            if info_list:
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
        
        # 6. 处理股票数据
        if limit_up_df is not None and not limit_up_df.empty:
            print(f"\n处理 {len(limit_up_df)} 只涨停股...")
            
            for idx, row in limit_up_df.iterrows():
                stock_code = str(row.get("代码", ""))
                stock_name = str(row.get("名称", ""))
                
                # 获取连板数（优先级：涨停梯队 > 板块强度 > high_days解析）
                continuous_days = ths_continue_num_dict.get(stock_code, 0)
                if continuous_days == 0:
                    high_days_str = ths_high_days_dict.get(stock_code, row.get("高度板", "首板"))
                    continuous_days = self.parse_continuous_days(high_days_str)
                
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
                
                stock = LimitUpStock(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    trade_date=trade_date,
                    limit_up_reason=limit_reason,
                    limit_up_time=limit_up_time,
                    limit_up_price=Decimal(str(limit_up_price)) if limit_up_price else None,
                    limit_up_type=limit_up_type,
                    block_id=block_id,
                    ths_reason_info=ths_reason_info,
                    seal_amount=Decimal(str(row.get("封板资金", 0))) if pd.notna(row.get("封板资金")) else Decimal('0'),
                    continuous_days=continuous_days,
                    high_days=high_days,
                    sector=self.get_stock_sector(stock_code),
                    change_percent=Decimal(str(row.get("涨跌幅", 0))) if pd.notna(row.get("涨跌幅")) else Decimal('0'),
                    turnover_rate=Decimal(str(row.get("换手率", 0))) if pd.notna(row.get("换手率")) else Decimal('0'),
                    amount=Decimal(str(row.get("成交额", 0))) if pd.notna(row.get("成交额")) else Decimal('0'),
                    is_high_stock=is_high_stock
                )
                
                stocks_data.append(stock)
                
                if continuous_days >= 8:
                    ladder_stats[8] += 1
                else:
                    ladder_stats[continuous_days] += 1
        
        # 6. 批量保存股票数据
        if stocks_data:
            session.bulk_save_objects(stocks_data)
            
            # 更新板块的高位股名称
            print("\n更新板块高位股信息...")
            for stock in stocks_data:
                if stock.block_id:
                    block = session.query(Block).filter(Block.id == stock.block_id).first()
                    if block and block.high_stock_code == stock.stock_code:
                        block.high_stock_name = stock.stock_name
            
            # 保存统计数据
            total_count = sum(ladder_stats.values())
            
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
            
            session.commit()
            
            print(f"\n✓ 数据保存成功！")
            print(f"  涨停总数: {total_count}")
            print(f"  首板: {ladder_stats[1]}")
            print(f"  2连板: {ladder_stats[2]}")
            print(f"  3连板: {ladder_stats[3]}")
            print(f"  4连板: {ladder_stats[4]}")
            print(f"  5连板+: {sum(ladder_stats[i] for i in range(5, 9))}")
            
            return True
        else:
            print("✗ 没有获取到任何数据")
            return False


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
