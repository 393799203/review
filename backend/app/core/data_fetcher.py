#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取器
使用mootdx、百度股市通、同花顺API
"""

import requests
import urllib.request
import json
import time
import random
import threading
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from mootdx.quotes import Quotes
from mootdx.utils.holiday import holiday


class DataFetcher:
    """数据获取器"""
    
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
        
        self.mootdx_client = Quotes.factory(market='std')
        
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
        """初始化会话"""
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
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        print("心跳线程已停止")
    
    def is_ready(self) -> bool:
        return self._session_ready
    
    def get_continuous_limit_up(self, date_str: str) -> Optional[List[Dict]]:
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
        获取单只股票的实时行情（使用mootdx）
        """
        try:
            print(f"从mootdx获取 {stock_code} 实时行情...")
            
            quotes = self.mootdx_client.quotes(symbol=[stock_code])
            
            if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                q = quotes.iloc[0]
                price = float(q.get('price', 0) or 0)
                prev_close = float(q.get('last_close', 0) or 0)

                # 竞价时段（9:15-9:25）mootdx 的 price 字段为 0，但五档盘口有
                # 竞价挂单参考价。此时用买一价（无则卖一价）作为最新价显示；
                # 无盘口价再退昨收，避免出现 "0.00 / -100%"。
                if price <= 0:
                    bid1 = float(q.get('bid1', 0) or 0)
                    ask1 = float(q.get('ask1', 0) or 0)
                    if bid1 > 0:
                        price = bid1
                    elif ask1 > 0:
                        price = ask1
                    elif prev_close > 0:
                        price = prev_close
                
                volatility = None
                turnover = None
                total_mv = None
                
                try:
                    high = float(q.get('high', 0) or 0)
                    low = float(q.get('low', 0) or 0)
                    
                    if high > 0 and low > 0 and prev_close > 0:
                        volatility = ((high - low) / prev_close) * 100
                    
                    volume = float(q.get('vol', 0) or 0)
                    if volume > 0:
                        market = 1 if stock_code.startswith('6') else 0
                        client = Quotes.factory(market=market)
                        finance_data = client.finance(symbol=stock_code)
                        if finance_data is not None and not finance_data.empty:
                            liutongguben = float(finance_data['liutongguben'].iloc[0])
                            if liutongguben > 0:
                                vol_shares = volume * 100
                                turnover = (vol_shares / liutongguben) * 100
                            # 总市值 = 总股本(股) × 现价（元）
                            try:
                                zongguben = float(finance_data['zongguben'].iloc[0])
                                if zongguben > 0 and price > 0:
                                    total_mv = zongguben * price
                            except (KeyError, IndexError, TypeError, ValueError):
                                pass
                except Exception as e:
                    print(f"计算波动率和换手率失败: {e}")
                
                return {
                    'code': stock_code,
                    'name': '',
                    'open': float(q.get('open', 0) or 0),
                    'prev_close': prev_close,
                    'price': price,
                    'high': float(q.get('high', 0) or 0),
                    'low': float(q.get('low', 0) or 0),
                    'volume': float(q.get('vol', 0) or 0),
                    'amount': float(q.get('amount', 0) or 0),
                    'change_amount': (price - prev_close) if price and prev_close else 0,
                    'change_percent': ((price - prev_close) / prev_close * 100) if price and prev_close else 0,
                    'volatility': round(volatility, 2) if volatility else None,
                    'turnover': round(turnover, 2) if turnover else None,
                    'total_mv': round(total_mv, 2) if total_mv else None,
                    'bid1': float(q.get('bid1', 0) or 0),
                    'bid2': float(q.get('bid2', 0) or 0),
                    'bid3': float(q.get('bid3', 0) or 0),
                    'bid4': float(q.get('bid4', 0) or 0),
                    'bid5': float(q.get('bid5', 0) or 0),
                    'ask1': float(q.get('ask1', 0) or 0),
                    'ask2': float(q.get('ask2', 0) or 0),
                    'ask3': float(q.get('ask3', 0) or 0),
                    'ask4': float(q.get('ask4', 0) or 0),
                    'ask5': float(q.get('ask5', 0) or 0),
                    'bid_vol1': float(q.get('bid_vol1', 0) or 0),
                    'bid_vol2': float(q.get('bid_vol2', 0) or 0),
                    'bid_vol3': float(q.get('bid_vol3', 0) or 0),
                    'bid_vol4': float(q.get('bid_vol4', 0) or 0),
                    'bid_vol5': float(q.get('bid_vol5', 0) or 0),
                    'ask_vol1': float(q.get('ask_vol1', 0) or 0),
                    'ask_vol2': float(q.get('ask_vol2', 0) or 0),
                    'ask_vol3': float(q.get('ask_vol3', 0) or 0),
                    'ask_vol4': float(q.get('ask_vol4', 0) or 0),
                    'ask_vol5': float(q.get('ask_vol5', 0) or 0),
                }
            
            return None
            
        except Exception as e:
            print(f"✗ 获取股票 {stock_code} 实时行情失败: {e}")
            return None
    
    def get_stock_kline(self, stock_code: str, days: int = 60) -> Optional[List[Dict]]:
        """
        获取股票历史K线数据（使用mootdx）
        """
        try:
            print(f"从mootdx获取 {stock_code} K线数据...")
            
            market = 1 if stock_code.startswith('6') else 0
            client = Quotes.factory(market=market)
            
            end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y-%m-%d')
            
            df = client.get_k_data(code=stock_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                print(f"✗ mootdx未返回K线数据")
                return self._get_kline_from_tdx(stock_code, days)
            
            df = df.tail(days)
            
            xdxr_data = {}
            try:
                xdxr_df = client.xdxr(symbol=stock_code)
                if xdxr_df is not None and not xdxr_df.empty:
                    for _, row in xdxr_df.iterrows():
                        if row['category'] == 1:
                            date_str = f"{int(row['year'])}-{int(row['month']):02d}-{int(row['day']):02d}"
                            desc_parts = []
                            
                            if pd.notna(row.get('songzhuangu')) and row['songzhuangu'] > 0:
                                desc_parts.append(f"转{row['songzhuangu']:.2f}")
                            
                            if pd.notna(row.get('fenhong')) and row['fenhong'] > 0:
                                desc_parts.append(f"派{row['fenhong']:.2f}")
                            
                            if pd.notna(row.get('peigu')) and row['peigu'] > 0:
                                desc_parts.append(f"配{row['peigu']:.2f}")
                            
                            if desc_parts:
                                xdxr_data[date_str] = '10' + ''.join(desc_parts)
                            else:
                                xdxr_data[date_str] = '除权'
            except Exception as e:
                print(f"获取除权除息数据失败: {e}")
            
            liutongguben = 0
            try:
                finance_data = client.finance(symbol=stock_code)
                if finance_data is not None and not finance_data.empty:
                    liutongguben = float(finance_data['liutongguben'].iloc[0])
            except Exception as e:
                print(f"获取流通股本失败: {e}")
            
            today_pre_close = 0
            try:
                quotes = client.quotes(symbol=[stock_code])
                if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                    today_pre_close = float(quotes.iloc[0].get('last_close', 0) or 0)
            except Exception as e:
                print(f"获取实时行情失败: {e}")
            
            kline_data = []
            prev_close = None
            
            for i, (idx, row) in enumerate(df.iterrows()):
                try:
                    current_close = float(row['close']) if row['close'] else 0
                    
                    is_last = (i == len(df) - 1)
                    
                    if is_last and today_pre_close > 0:
                        pre_close = today_pre_close
                    else:
                        pre_close = prev_close if prev_close is not None else 0
                    
                    date_str = str(row['date'])[:10] if 'date' in row else idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
                    
                    is_ex_dividend = False
                    ex_dividend_ratio = None
                    ex_dividend_desc = None
                    
                    if date_str in xdxr_data:
                        is_ex_dividend = True
                        ex_dividend_desc = xdxr_data[date_str]
                        
                        if prev_close is not None and prev_close > 0:
                            ex_dividend_ratio = round(abs(current_close - prev_close) / prev_close * 100, 2)
                    
                    change_percent = 0
                    change_amount = 0
                    if pre_close > 0:
                        change_percent = ((current_close - pre_close) / pre_close) * 100
                        change_amount = current_close - pre_close
                    
                    turnover = 0
                    if liutongguben > 0 and row['vol']:
                        vol_shares = float(row['vol']) * 100
                        turnover = (vol_shares / liutongguben) * 100
                    
                    kline_data.append({
                        'date': date_str,
                        'open': float(row['open']) if row['open'] else 0,
                        'close': current_close,
                        'high': float(row['high']) if row['high'] else 0,
                        'low': float(row['low']) if row['low'] else 0,
                        'volume': float(row['vol']) if row['vol'] else 0,
                        'amount': float(row['amount']) if row['amount'] else 0,
                        'change_percent': round(change_percent, 2),
                        'change_amount': round(change_amount, 2),
                        'turnover': round(turnover, 2),
                        'pre_close': pre_close,
                        'is_ex_dividend': is_ex_dividend,
                        'ex_dividend_ratio': ex_dividend_ratio,
                        'ex_dividend_desc': ex_dividend_desc,
                    })
                    
                    prev_close = current_close
                    
                except (ValueError, TypeError) as e:
                    continue
            
            if kline_data:
                print(f"✓ 成功获取K线数据，共 {len(kline_data)} 条记录")
                return kline_data
            
            return self._get_kline_from_tdx(stock_code, days)
            
        except Exception as e:
            print(f"✗ 获取股票 {stock_code} K线数据失败: {e}")
            return self._get_kline_from_tdx(stock_code, days)

    def _get_kline_from_tdx(self, stock_code: str, days: int = 60) -> Optional[List[Dict]]:
        """
        TDX 行情库兜底：mootdx 不可用时从 quantdb（tdx.raw_stocks_daily）读日线拼 K 线。

        返回结构与 mootdx 路径一致（时间正序、含涨跌幅/前收），换手率与除权信息为空。
        """
        try:
            from app.core.tdx_db import get_tdx_engine
            from sqlalchemy import text

            engine = get_tdx_engine()
            if engine is None:
                return None

            code = str(stock_code).split('.')[0]
            if code.startswith('6'):
                symbol = f"sh{code}"
            elif code.startswith(('4', '8')):
                symbol = f"bj{code}"
            else:
                symbol = f"sz{code}"

            sql = text(
                "SELECT date, open, high, low, close, volume, amount "
                "FROM tdx.raw_stocks_daily WHERE symbol = :symbol "
                "ORDER BY date DESC LIMIT :days"
            )
            with engine.connect() as conn:
                rows = conn.execute(sql, {'symbol': symbol, 'days': int(days)}).fetchall()
            if not rows:
                return None

            kline = []
            prev_close = None
            for d, o, h, lo, c, vol, amount in reversed(rows):
                close = float(c) if c else 0
                if prev_close is None:
                    pre_close = close
                else:
                    pre_close = prev_close
                change_percent = ((close - pre_close) / pre_close * 100) if pre_close > 0 else 0
                date_str = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)[:10]
                kline.append({
                    'date': date_str,
                    'open': float(o or 0),
                    'close': close,
                    'high': float(h or 0),
                    'low': float(lo or 0),
                    'volume': float(vol or 0),
                    'amount': float(amount or 0),
                    'change_percent': round(change_percent, 2),
                    'change_amount': round(close - pre_close, 2),
                    'turnover': 0,
                    'pre_close': pre_close,
                    'is_ex_dividend': False,
                    'ex_dividend_ratio': None,
                    'ex_dividend_desc': None,
                })
                prev_close = close

            print(f"✓ TDX行情库兜底获取 {stock_code} K线，共 {len(kline)} 条")
            return kline
        except Exception as e:
            print(f"✗ TDX行情库 K线兜底失败: {e}")
            return None
    
    def get_stock_intraday(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票当日分时数据（使用mootdx）
        在交易日早上9点之前返回昨天的数据
        在非交易日返回最近交易日的数据
        """
        try:
            now = datetime.now()
            current_time = now.time()
            market_open_time = datetime.strptime('09:25', '%H:%M').time()
            
            date_str = None
            
            if holiday(date=now.strftime('%Y-%m-%d')):
                check_date = now - timedelta(days=1)
                while holiday(date=check_date.strftime('%Y-%m-%d')):
                    check_date = check_date - timedelta(days=1)
                
                date_str = check_date.strftime('%Y%m%d')
                print(f"今天是非交易日，获取 {date_str} 的分时数据...")
            elif current_time < market_open_time:
                check_date = now - timedelta(days=1)
                while holiday(date=check_date.strftime('%Y-%m-%d')):
                    check_date = check_date - timedelta(days=1)
                
                date_str = check_date.strftime('%Y%m%d')
                print(f"当前时间 {current_time} 早于开盘时间，获取 {date_str} 的分时数据...")
            
            print(f"从mootdx获取 {stock_code} 分时数据...")
            
            if date_str:
                minutes = self.mootdx_client.minutes(symbol=stock_code, date=date_str)
            else:
                minutes = self.mootdx_client.minute(symbol=stock_code)
            
            if minutes is None or (hasattr(minutes, 'empty') and minutes.empty):
                print(f"✗ mootdx未返回分时数据")
                return None
            
            intraday_data = []
            last_valid_price = 0  # 竞价/无成交点的价格占位（沿用上一有效价）
            for idx, row in minutes.iterrows():
                if idx < 120:
                    hour = 9 + (30 + idx) // 60
                    minute = (30 + idx) % 60
                else:
                    hour = 13 + (idx - 120) // 60
                    minute = (idx - 120) % 60
                
                p = float(row.get('price', 0) or 0)
                if p <= 0:
                    p = last_valid_price if last_valid_price > 0 else 0
                else:
                    last_valid_price = p

                intraday_data.append({
                    'time': f"{hour:02d}:{minute:02d}",
                    'price': p,
                    'volume': float(row.get('vol', 0) or 0),
                })
            
            if not intraday_data:
                print(f"✗ mootdx未返回分时数据")
                return None
            
            if len(intraday_data) >= 120:
                last_morning = intraday_data[119]
                intraday_data.insert(120, {
                    'time': '11:30',
                    'price': last_morning['price'],
                    'volume': 0,
                })
            
            if len(intraday_data) >= 241:
                last_afternoon = intraday_data[-1]
                intraday_data.append({
                    'time': '15:00',
                    'price': last_afternoon['price'],
                    'volume': 0,
                })
            
            quotes = self.mootdx_client.quotes(symbol=[stock_code])
            yesterday_close = 0
            if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                yesterday_close = float(quotes.iloc[0].get('last_close', 0) or 0)
            
            print(f"✓ 成功获取分时数据，共 {len(intraday_data)} 条记录")
            return {
                'intraday': intraday_data,
                'yesterday_close': yesterday_close
            }
            
        except Exception as e:
            print(f"✗ 获取股票 {stock_code} 分时数据失败: {e}")
            return None
    
    def get_all_data(self, date_str: str) -> Dict:
        print(f"\n从同花顺获取 {date_str} 的数据...")
        
        return {
            'continuous_limit_up': self.get_continuous_limit_up(date_str),
            'limit_up_pool': self.get_limit_up_pool(date_str),
            'limit_up_type': self.get_limit_up_type(date_str),
            'block_top': self.get_block_top(date_str),
        }
    
    def get_reports(self, page: int = 1, page_size: int = 50, stock_code: str = '') -> Optional[Dict]:
        """
        获取研报列表（东财研报API）
        """
        try:
            REPORT_API = "https://reportapi.eastmoney.com/report/list"
            
            params = {
                "industryCode": "*",
                "pageSize": str(page_size),
                "industry": "*",
                "rating": "*",
                "ratingChange": "*",
                "beginTime": "2000-01-01",
                "endTime": "2030-01-01",
                "pageNo": str(page),
                "fields": "",
                "qType": "0",
                "orgCode": "",
                "code": stock_code,
                "rcode": "",
                "p": str(page),
                "pageNum": str(page),
                "pageNumber": str(page),
            }
            
            # 东财 reportapi 会拦截带同花顺 Referer/Origin 的请求(返回567拦截页),
            # 不能使用 self.session(携带同花顺会话头),用干净请求头单独访问
            r = requests.get(REPORT_API, params=params, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
                'Referer': 'https://data.eastmoney.com/report/',
            })
            d = r.json()
            
            return {
                'list': d.get('data', []),
                'total': d.get('TotalPage', 0),
                'page': page
            }
            
        except Exception as e:
            print(f"✗ 获取研报列表失败: {e}")
            return None
