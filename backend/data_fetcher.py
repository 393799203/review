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
from typing import Dict, List, Optional
from mootdx.quotes import Quotes


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
                    'change_amount': price - prev_close if price and prev_close else 0,
                    'change_percent': ((price - prev_close) / prev_close * 100) if prev_close else 0,
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
        获取股票历史K线数据（使用百度股市通API）
        """
        try:
            print(f"从百度股市通获取 {stock_code} K线数据...")
            
            url = "https://finance.pae.baidu.com/selfselect/getstockquotation"
            params = {
                "all": "1", "isIndex": "false", "isBk": "false", "isBlock": "false",
                "isFutures": "false", "isStock": "true", "newFormat": "1",
                "group": "quotation_kline_ab", "finClientType": "pc",
                "code": stock_code, "start_time": "", "ktype": "1",
            }
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/vnd.finance-web.v1+json",
                "Origin": "https://gushitong.baidu.com",
                "Referer": "https://gushitong.baidu.com/",
            }
            
            r = requests.get(url, params=params, headers=headers, timeout=15)
            d = r.json()
            
            result = d.get("Result", {})
            md = result.get("newMarketData", {})
            keys = md.get("keys", [])
            rows = md.get("marketData", "").split(";")
            
            if not rows or rows[0] == '':
                print(f"✗ 百度股市通未返回K线数据")
                return None
            
            key_map = {k: i for i, k in enumerate(keys)}
            
            kline_data = []
            for row in rows[-days:]:
                if not row.strip():
                    continue
                vals = row.split(',')
                
                try:
                    close = float(vals[key_map.get('close', 3)]) if vals[key_map.get('close', 3)] else 0
                    pre_close = float(vals[key_map.get('preClose', 11)]) if key_map.get('preClose', 11) < len(vals) and vals[key_map.get('preClose', 11)] else 0
                    
                    kline_data.append({
                        'date': vals[key_map.get('time', 1)],
                        'open': float(vals[key_map.get('open', 2)]) if vals[key_map.get('open', 2)] else 0,
                        'close': close,
                        'high': float(vals[key_map.get('high', 5)]) if vals[key_map.get('high', 5)] else 0,
                        'low': float(vals[key_map.get('low', 6)]) if vals[key_map.get('low', 6)] else 0,
                        'volume': float(vals[key_map.get('volume', 4)]) if vals[key_map.get('volume', 4)] else 0,
                        'amount': float(vals[key_map.get('amount', 7)]) if vals[key_map.get('amount', 7)] else 0,
                        'change_percent': float(vals[key_map.get('ratio', 9)]) if key_map.get('ratio', 9) < len(vals) and vals[key_map.get('ratio', 9)] else 0,
                        'change_amount': float(vals[key_map.get('range', 8)]) if key_map.get('range', 8) < len(vals) and vals[key_map.get('range', 8)] else 0,
                        'turnover': float(vals[key_map.get('turnoverratio', 10)]) if key_map.get('turnoverratio', 10) < len(vals) and vals[key_map.get('turnoverratio', 10)] else 0,
                        'pre_close': pre_close,
                    })
                except (ValueError, TypeError, IndexError) as e:
                    continue
            
            if kline_data:
                print(f"✓ 成功获取K线数据，共 {len(kline_data)} 条记录")
                return kline_data
            
            return None
            
        except Exception as e:
            print(f"✗ 获取股票 {stock_code} K线数据失败: {e}")
            return None
    
    def get_stock_intraday(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票当日分时数据（使用mootdx）
        """
        try:
            print(f"从mootdx获取 {stock_code} 分时数据...")
            
            minutes = self.mootdx_client.minute(symbol=stock_code)
            
            if minutes is None or (hasattr(minutes, 'empty') and minutes.empty):
                print(f"✗ mootdx未返回分时数据")
                return None
            
            intraday_data = []
            for idx, row in minutes.iterrows():
                if idx < 120:
                    hour = 9 + (30 + idx) // 60
                    minute = (30 + idx) % 60
                else:
                    hour = 13 + (idx - 120) // 60
                    minute = (idx - 120) % 60
                
                intraday_data.append({
                    'time': f"{hour:02d}:{minute:02d}",
                    'price': float(row.get('price', 0) or 0),
                    'volume': float(row.get('vol', 0) or 0),
                })
            
            if not intraday_data:
                print(f"✗ mootdx未返回分时数据")
                return None
            
            # 补充11:30数据（使用11:29的收盘价）
            if len(intraday_data) >= 120:
                last_morning = intraday_data[119]
                intraday_data.insert(120, {
                    'time': '11:30',
                    'price': last_morning['price'],
                    'volume': 0,
                })
            
            # 补充15:00数据（使用14:59的收盘价）
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
