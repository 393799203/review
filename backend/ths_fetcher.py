#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺数据获取器
"""

import requests
import time
import random
import threading
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
    
    def get_limit_up_pool(self, date_str: str, page: int = 1, limit: int = 200) -> Optional[Dict]:
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
