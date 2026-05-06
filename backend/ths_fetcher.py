#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺数据获取器
"""

import requests
import time
import random
import threading
import re
from typing import Dict, List, Optional


class ThsFetcher:
    """同花顺数据获取器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html',
            'Origin': 'https://data.10jqka.com.cn',
        })
        
        self._heartbeat_thread = None
        self._heartbeat_running = False
        self._session_ready = False
        
    def init_session(self):
        """初始化会话（访问主页建立会话）"""
        try:
            print("建立同花顺会话...")
            self.session.get('https://data.10jqka.com.cn/', timeout=10)
            time.sleep(random.uniform(0.5, 1.5))
            self._session_ready = True
            print("✓ 同花顺会话建立成功")
            return True
        except Exception as e:
            print(f"✗ 建立会话失败: {e}")
            return False
    
    def start_heartbeat(self, interval: int = 60):
        """
        启动心跳线程
        
        Args:
            interval: 心跳间隔（秒），默认60秒
        """
        if self._heartbeat_running:
            print("心跳线程已在运行")
            return
        
        self._heartbeat_running = True
        
        def heartbeat():
            while self._heartbeat_running:
                try:
                    time.sleep(interval)
                    if self._heartbeat_running:
                        response = self.session.get('https://data.10jqka.com.cn/', timeout=10)
                        if response.status_code == 200:
                            print(f"[心跳] 同花顺会话保持成功")
                        else:
                            print(f"[心跳] 同花顺会话响应异常: {response.status_code}")
                except Exception as e:
                    print(f"[心跳] 同花顺会话保持失败: {e}")
        
        self._heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        self._heartbeat_thread.start()
        print(f"✓ 心跳线程已启动，间隔 {interval} 秒")
    
    def stop_heartbeat(self):
        """停止心跳线程"""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        print("心跳线程已停止")
    
    def is_ready(self) -> bool:
        """检查会话是否就绪"""
        return self._session_ready
    
    def get_continuous_limit_up(self, date_str: str) -> Optional[List[Dict]]:
        """
        获取涨停梯队数据
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            涨停梯队数据列表
        """
        url = 'https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up'
        params = {
            'filter': 'HS,GEM2STAR',
            'date': date_str
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('status_code') == 0:
                    stocks = data.get('data', [])
                    print(f"✓ 同花顺涨停梯队接口获取到 {len(stocks)} 个梯队数据")
                    return stocks
        except Exception as e:
            print(f"✗ 获取同花顺涨停梯队数据失败: {e}")
        
        return None
    
    def get_limit_up_pool(self, date_str: str, page: int = 1, limit: int = 150) -> Optional[Dict]:
        """
        获取涨停池数据
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            page: 页码
            limit: 每页数量
            
        Returns:
            涨停池数据
        """
        url = 'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool'
        params = {
            'page': page,
            'limit': limit,
            'field': '199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004',
            'filter': 'HS,GEM2STAR',
            'order_field': 330324,
            'order_type': 0,
            'date': date_str,
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('status_code') == 0 and 'data' in data:
                    info_list = data['data'].get('info', [])
                    print(f"✓ 同花顺涨停池接口获取到 {len(info_list)} 只股票")
                    return data['data']
        except Exception as e:
            print(f"✗ 获取同花顺涨停池数据失败: {e}")
        
        return None
    
    def get_limit_up_type(self, date_str: str) -> Optional[List[Dict]]:
        """
        获取涨停类型数据（一字板、T字板等）
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            涨停类型数据列表
        """
        url = 'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_type'
        params = {
            'filter': 'HS,GEM2STAR',
            'date': date_str
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('status_code') == 0:
                    type_list = data.get('data', [])
                    print(f"✓ 同花顺涨停类型接口获取到 {len(type_list)} 种类型")
                    return type_list
        except Exception as e:
            print(f"✗ 获取同花顺涨停类型数据失败: {e}")
        
        return None
    
    def get_block_top(self, date_str: str) -> Optional[List[Dict]]:
        """
        获取板块强度数据
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            板块强度数据列表
        """
        url = 'https://data.10jqka.com.cn/dataapi/limit_up/block_top'
        params = {
            'filter': 'HS,GEM2STAR',
            'date': date_str
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('status_code') == 0:
                    blocks = data.get('data', [])
                    print(f"✓ 同花顺板块强度接口获取到 {len(blocks)} 个板块")
                    return blocks
        except Exception as e:
            print(f"✗ 获取同花顺板块强度数据失败: {e}")
        
        return None
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict]:
        """
        获取单只股票的实时行情（通过新浪财经API，速度快）
        
        Args:
            stock_code: 股票代码（6位数字）
            
        Returns:
            实时行情数据字典
        """
        try:
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"
            
            url = f"http://hq.sinajs.cn/list={symbol}"
            
            headers = {
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.get(url, headers=headers, timeout=5)
            response.encoding = 'gbk'
            
            pattern = re.compile(r'="(.*)"')
            match = pattern.search(response.text)
            
            if match:
                data_str = match.group(1)
                data_list = data_str.split(',')
                
                if len(data_list) >= 32:
                    price = float(data_list[3]) if data_list[3] else None
                    prev_close = float(data_list[2]) if data_list[2] else None
                    
                    return {
                        'code': stock_code,
                        'name': data_list[0],
                        'open': float(data_list[1]) if data_list[1] else None,
                        'prev_close': prev_close,
                        'price': price,
                        'high': float(data_list[4]) if data_list[4] else None,
                        'low': float(data_list[5]) if data_list[5] else None,
                        'volume': float(data_list[8]) if data_list[8] else 0,
                        'amount': float(data_list[9]) if data_list[9] else 0,
                        'change_amount': price - prev_close if price and prev_close else 0,
                        'change_percent': ((price - prev_close) / prev_close * 100) if price and prev_close else 0,
                    }
            
            return None
            
        except Exception as e:
            print(f"✗ 获取股票 {stock_code} 实时行情失败: {e}")
            return None
    
    def get_stock_kline(self, stock_code: str, days: int = 60) -> Optional[List[Dict]]:
        """
        获取股票历史K线数据
        
        Args:
            stock_code: 股票代码（6位数字）
            days: 获取最近多少天的数据，默认60天
            
        Returns:
            K线数据列表
        """
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            import time
            import random
            
            data_sources = [
                ('新浪财经', self._get_kline_sina),
                ('东方财富', self._get_kline_eastmoney),
                ('腾讯财经', self._get_kline_tencent),
            ]
            
            for source_name, source_func in data_sources:
                try:
                    print(f"尝试从 {source_name} 获取 {stock_code} K线数据...")
                    result = source_func(stock_code, days, ak, datetime, timedelta)
                    if result:
                        print(f"✓ 成功从 {source_name} 获取K线数据，共 {len(result)} 条记录")
                        return result
                except Exception as e:
                    print(f"✗ {source_name} 数据源失败: {e}")
                    time.sleep(random.uniform(0.5, 1.5))
                    continue
            
            print(f"✗ 所有数据源都无法获取股票 {stock_code} K线数据")
            return None
            
        except Exception as e:
            print(f"✗ 获取股票 {stock_code} K线数据失败: {e}")
            return None
    
    def _get_kline_tencent(self, stock_code: str, days: int, ak, datetime, timedelta) -> Optional[List[Dict]]:
        """从腾讯财经获取K线数据"""
        import time
        import random
        
        try:
            time.sleep(random.uniform(0.3, 0.8))
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
            
            df = ak.stock_zh_a_hist_tx(
                symbol=stock_code,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is not None and not df.empty:
                df = df.tail(days)
                
                kline_data = []
                for _, row in df.iterrows():
                    try:
                        kline_data.append({
                            'date': str(row['date']),
                            'open': float(row['open']) if row['open'] else 0,
                            'close': float(row['close']) if row['close'] else 0,
                            'high': float(row['high']) if row['high'] else 0,
                            'low': float(row['low']) if row['low'] else 0,
                            'volume': float(row['volume']) if row['volume'] else 0,
                            'amount': 0,
                            'change_percent': 0,
                            'change_amount': 0,
                            'turnover': 0,
                        })
                    except (ValueError, TypeError) as e:
                        print(f"解析腾讯财经数据行失败: {e}, row: {row}")
                        continue
                
                if kline_data:
                    return kline_data
            
        except Exception as e:
            if 'Connection' in str(e) or 'RemoteDisconnected' in str(e):
                time.sleep(random.uniform(2, 4))
            raise e
        
        return None
    
    def _get_kline_sina(self, stock_code: str, days: int, ak, datetime, timedelta) -> Optional[List[Dict]]:
        """从新浪财经获取K线数据"""
        import time
        import random
        
        try:
            time.sleep(random.uniform(0.3, 0.8))
            
            df = ak.stock_zh_a_daily(symbol=f"sh{stock_code}" if stock_code.startswith('6') else f"sz{stock_code}")
            
            if df is not None and not df.empty:
                df = df.tail(days)
                
                kline_data = []
                for _, row in df.iterrows():
                    kline_data.append({
                        'date': row['date'],
                        'open': float(row['open']),
                        'close': float(row['close']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'volume': float(row['volume']),
                        'amount': 0,
                        'change_percent': 0,
                        'change_amount': 0,
                        'turnover': 0,
                    })
                
                return kline_data
            
        except Exception as e:
            if 'Connection' in str(e) or 'RemoteDisconnected' in str(e):
                time.sleep(random.uniform(2, 4))
            raise e
        
        return None
    
    def _get_kline_eastmoney(self, stock_code: str, days: int, ak, datetime, timedelta) -> Optional[List[Dict]]:
        """从东方财富获取K线数据"""
        import time
        import random
        
        try:
            # 添加随机延迟，避免触发频率限制
            time.sleep(random.uniform(0.3, 0.8))
            
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is not None and not df.empty:
                df = df.tail(days)
                
                kline_data = []
                for _, row in df.iterrows():
                    kline_data.append({
                        'date': row['日期'],
                        'open': float(row['开盘']),
                        'close': float(row['收盘']),
                        'high': float(row['最高']),
                        'low': float(row['最低']),
                        'volume': float(row['成交量']),
                        'amount': float(row['成交额']),
                        'change_percent': float(row['涨跌幅']) if row['涨跌幅'] else 0,
                        'change_amount': float(row['涨跌额']) if row['涨跌额'] else 0,
                        'turnover': float(row['换手率']) if row['换手率'] else 0,
                    })
                
                return kline_data
            
        except Exception as e:
            # 如果是连接错误，等待更长时间后重试
            if 'Connection' in str(e) or 'RemoteDisconnected' in str(e):
                time.sleep(random.uniform(2, 4))
            raise e
        
        return None
    
    def get_stock_intraday(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票最近交易日分时数据
        
        Args:
            stock_code: 股票代码（6位数字）
            
        Returns:
            包含分时数据和昨日收盘价的字典
        """
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            import time
            import random
            
            data_sources = [
                ('腾讯财经', self._get_intraday_tencent),
                ('新浪财经', self._get_intraday_sina),
                ('东方财富', self._get_intraday_eastmoney),
            ]
            
            for source_name, source_func in data_sources:
                try:
                    print(f"尝试从 {source_name} 获取 {stock_code} 分时数据...")
                    result = source_func(stock_code, ak, datetime, timedelta)
                    if result:
                        print(f"✓ 成功从 {source_name} 获取分时数据")
                        return result
                except Exception as e:
                    print(f"✗ {source_name} 数据源失败: {e}")
                    time.sleep(random.uniform(0.5, 1.5))
                    continue
            
            print(f"✗ 所有数据源都无法获取股票 {stock_code} 分时数据")
            return None
            
        except Exception as e:
            print(f"✗ 获取股票 {stock_code} 分时数据失败: {e}")
            return None
    
    def _get_intraday_tencent(self, stock_code: str, ak, datetime, timedelta) -> Optional[Dict]:
        """从腾讯财经获取分时数据"""
        import time
        import random
        
        try:
            time.sleep(random.uniform(0.3, 0.8))
            
            df = ak.stock_zh_a_minute(symbol=f"sh{stock_code}" if stock_code.startswith('6') else f"sz{stock_code}", period='1', adjust="qfq")
            
            if df is not None and not df.empty:
                for days_ago in range(0, 7):
                    date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
                    date_data = df[df['day'].str.startswith(date)]
                    
                    if not date_data.empty:
                        intraday_data = []
                        for _, row in date_data.iterrows():
                            intraday_data.append({
                                'time': row['day'],
                                'price': float(row['close']),
                                'volume': float(row['volume']),
                                'amount': 0,
                            })
                        
                        yesterday_close = float(date_data.iloc[0]['open'])
                        
                        return {
                            'intraday': intraday_data,
                            'yesterday_close': yesterday_close
                        }
            
        except Exception as e:
            if 'Connection' in str(e) or 'RemoteDisconnected' in str(e):
                time.sleep(random.uniform(2, 4))
            raise e
        
        return None
    
    def _get_intraday_eastmoney(self, stock_code: str, ak, datetime, timedelta) -> Optional[Dict]:
        """从东方财富获取分时数据"""
        import time
        import random
        
        for days_ago in range(0, 7):
            date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            try:
                # 添加随机延迟，避免触发频率限制
                time.sleep(random.uniform(0.3, 0.8))
                
                df = ak.stock_zh_a_hist_min_em(
                    symbol=stock_code,
                    start_date=f'{date} 09:30:00',
                    end_date=f'{date} 15:00:00',
                    period='1',
                    adjust='qfq'
                )
                
                if df is not None and not df.empty:
                    intraday_data = []
                    for _, row in df.iterrows():
                        intraday_data.append({
                            'time': row['时间'],
                            'price': float(row['收盘']),
                            'volume': float(row['成交量']),
                            'amount': float(row['成交额']),
                        })
                    
                    yesterday_close = self._get_yesterday_close(stock_code, ak, datetime, timedelta, df)
                    
                    return {
                        'intraday': intraday_data,
                        'yesterday_close': yesterday_close
                    }
                    
            except Exception as e:
                # 如果是连接错误，等待更长时间后重试
                if 'Connection' in str(e) or 'RemoteDisconnected' in str(e):
                    time.sleep(random.uniform(2, 4))
                continue
        
        return None
    
    def _get_intraday_sina(self, stock_code: str, ak, datetime, timedelta) -> Optional[Dict]:
        """从新浪财经获取分时数据"""
        import time
        import random
        
        try:
            time.sleep(random.uniform(0.3, 0.8))
            
            market = 'sh' if stock_code.startswith(('6', '5')) else 'sz'
            symbol = f"{market}{stock_code}"
            
            df = ak.stock_zh_a_minute(symbol=symbol, period='1', adjust="qfq")
            
            if df is not None and not df.empty:
                for days_ago in range(0, 7):
                    date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
                    date_data = df[df['day'].str.startswith(date)]
                    
                    if not date_data.empty:
                        intraday_data = []
                        for _, row in date_data.iterrows():
                            intraday_data.append({
                                'time': row['day'],
                                'price': float(row['close']),
                                'volume': float(row['volume']),
                                'amount': 0,
                            })
                        
                        yesterday_close = float(date_data.iloc[0]['open'])
                        
                        return {
                            'intraday': intraday_data,
                            'yesterday_close': yesterday_close
                        }
            
        except Exception as e:
            if 'Connection' in str(e) or 'RemoteDisconnected' in str(e):
                time.sleep(random.uniform(2, 4))
            raise e
        
        return None
    
    def _get_yesterday_close(self, stock_code: str, ak, datetime, timedelta, df) -> float:
        """获取昨日收盘价"""
        try:
            df_daily = ak.stock_zh_a_hist(
                symbol=stock_code,
                period='daily',
                start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust='qfq'
            )
            
            if df_daily is not None and len(df_daily) >= 2:
                return float(df_daily.iloc[-2]['收盘'])
            else:
                return float(df.iloc[0]['开盘'])
        except Exception:
            return float(df.iloc[0]['开盘'])
    
    def get_all_data(self, date_str: str) -> Dict:
        """
        获取所有同花顺数据
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            包含所有数据的字典
        """
        print(f"\n从同花顺获取 {date_str} 的数据...")
        
        return {
            'continuous_limit_up': self.get_continuous_limit_up(date_str),
            'limit_up_pool': self.get_limit_up_pool(date_str),
            'limit_up_type': self.get_limit_up_type(date_str),
            'block_top': self.get_block_top(date_str),
        }
