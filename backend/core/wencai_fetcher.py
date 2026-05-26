#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺问财数据获取器
"""

import pywencai
import threading
from typing import List, Dict, Optional
import os


class WencaiFetcher:
    """问财数据获取器"""
    
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
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        
        self.cookie = os.getenv('WENCAI_COOKIE', '')
        
    def set_cookie(self, cookie: str):
        """设置Cookie"""
        self.cookie = cookie
    
    def get_breakout_stocks(self, date_str: str, cookie: str = '') -> Optional[List[Dict]]:
        """
        获取突破120日高点的涨停股
        
        Args:
            date_str: 日期字符串（YYYYMMDD格式）
            cookie: 问财cookie（可选，匿名访问也可以）
            
        Returns:
            股票列表
        """
        date_formatted = f"{date_str[:4]}年{date_str[4:6]}月{date_str[6:8]}日"
        
        query = f'''
{date_formatted} 涨停
非ST 非科创板 非北交所
股价大于等于120日最高价的95%
'''
        
        try:
            print(f"\n问财查询: {query.strip()}")
            result = pywencai.get(
                query=query,
                cookie=cookie if cookie else None,
                loop=True,
                log=False
            )
            
            if result is not None and not result.empty:
                stocks = result.to_dict('records')
                print(f"✓ 问财查询成功，找到 {len(stocks)} 只股票")
                return stocks
            else:
                print("✗ 问财查询无结果")
                return []
                
        except Exception as e:
            print(f"✗ 问财查询失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def custom_query(self, query: str, cookie: str = '') -> Optional[List[Dict]]:
        """
        自定义问财查询
        
        Args:
            query: 查询语句
            cookie: 问财cookie（可选，匿名访问也可以）
            
        Returns:
            查询结果列表
        """
        try:
            print(f"\n问财自定义查询: {query}")
            result = pywencai.get(
                query=query,
                cookie=cookie if cookie else None,
                loop=True,
                log=False
            )
            
            if result is not None and not result.empty:
                data = result.to_dict('records')
                print(f"✓ 问财查询成功，找到 {len(data)} 条结果")
                return data
            else:
                print("✗ 问财查询无结果")
                return []
                
        except Exception as e:
            print(f"✗ 问财查询失败: {e}")
            import traceback
            traceback.print_exc()
            return None


wencai_fetcher = WencaiFetcher()
